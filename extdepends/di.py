import inspect
from contextlib import AsyncExitStack, asynccontextmanager, contextmanager
from typing import ContextManager, AsyncContextManager, List, Union
from functools import wraps

from fastapi import FastAPI, Depends


class ResourceContainer:

    def __init__(self):

        self._exit_stack = AsyncExitStack()
        self._instances = {}

    @staticmethod
    def _provider_key(provider):
        return provider.__module__, provider.__name__

    @staticmethod
    def _manager_from(provider, deps):
        if inspect.isgeneratorfunction(provider):
            manager = contextmanager(provider)(**deps)
        elif inspect.isasyncgenfunction(provider):
            manager = asynccontextmanager(provider)(**deps)
        else:
            manager = provider(**deps)
        return manager

    async def _instance_from(self, provider, deps):

        manager = self._manager_from(provider, deps)

        if isinstance(manager, AsyncContextManager):
            instance = await self._exit_stack.enter_async_context(manager)
        elif isinstance(manager, ContextManager):
            instance = self._exit_stack.enter_context(manager)
        elif inspect.isawaitable(manager):
            instance = await manager
        else:
            instance = manager

        return instance

    async def __call__(self, provider, deps):
        key = self._provider_key(provider)
        instance = self._instances.get(key)
        if instance:
            return instance

        instance = await self._instance_from(provider, deps)
        self._instances[key] = instance

        return instance

    async def aclose(self):
        self._instances.clear()
        await self._exit_stack.aclose()


def setup_extend_di(app: Union[FastAPI, List[FastAPI]]):
    resource_container = ResourceContainer()

    if isinstance(app, list):
        for a in app:
            a.dependency_overrides[ResourceContainer] = lambda: resource_container
    else:
        app.dependency_overrides[ResourceContainer] = lambda: resource_container


@asynccontextmanager
async def on_di_shutdown(app: FastAPI):
    yield
    container: ResourceContainer = app.dependency_overrides[ResourceContainer]()

    await container.aclose()


def resource(provider):
    def add_arg(func, name, default):
        sig = inspect.signature(func)
        params = list(sig.parameters.values())
        param = inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=default)
        params.append(param)
        func.__signature__ = sig.replace(parameters=params)

    @wraps(provider)
    async def wrapper(_container, **deps):
        return await _container(provider, deps)

    add_arg(wrapper, '_container', Depends(ResourceContainer))

    return wrapper
