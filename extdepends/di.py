from typing import Any, ContextManager, AsyncContextManager
import types
import inspect

from extdepends.merge_args import merge_args
from fastapi import FastAPI, Depends
from contextlib import AsyncExitStack, suppress, asynccontextmanager


class GeneratorExitCollector:
    def __init__(self):
        self._resources = []

    def add_generator_resource(self, gen_res):
        self._resources.append(gen_res)

    async def close_gen_depends(self):
        for gen in self._resources:
            if inspect.isgenerator(gen):
                next(gen, None)
            elif inspect.isasyncgen(gen):
                with suppress(StopAsyncIteration):
                    await gen.__anext__()


class ResourceCacher:
    def __init__(self):
        self._resources = {}

    def add_cache_depends(self, func, ready_res):
        cache_key = (func.__module__, func.__name__)
        self._resources[cache_key] = ready_res

    def get_cache_depends(self, func) -> Any:
        cache_key = (func.__module__, func.__name__)
        return self._resources.get(cache_key, None)


def _async_di_exit_stack() -> AsyncExitStack:
    raise NotImplementedError()


def _async_generator_calls() -> GeneratorExitCollector:
    raise NotImplementedError()


def _resources_cache_di():
    raise NotImplementedError()


def setup_extend_di(app: FastAPI):
    exit_stack = AsyncExitStack()
    resource_cacher = ResourceCacher()
    generator_exit_stack = GeneratorExitCollector()

    app.dependency_overrides[_async_di_exit_stack] = lambda: exit_stack
    app.dependency_overrides[_async_generator_calls] = lambda: generator_exit_stack
    app.dependency_overrides[_resources_cache_di] = lambda: resource_cacher


@asynccontextmanager
async def on_di_shutdown(app: FastAPI):
    yield
    async_generator_collector: GeneratorExitCollector = app.dependency_overrides[_async_generator_calls]()
    async_exit_stack: AsyncExitStack = app.dependency_overrides[_async_di_exit_stack]()

    await async_generator_collector.close_gen_depends()
    await async_exit_stack.aclose()


def resource(dep):
    @merge_args(dep, drop_args=["args", "kwargs", "kwds"])
    async def wrapper(*_args, _generator_finished=Depends(_async_generator_calls),
                      _resource_cacher=Depends(_resources_cache_di),
                      _async_context_exit_stak: AsyncExitStack = Depends(_async_di_exit_stack), **kwargs):
        already_exist_resource = _resource_cacher.get_cache_depends(dep)
        if already_exist_resource:
            return already_exist_resource

        if inspect.isgeneratorfunction(dep):
            resource_gen = dep(**kwargs)
            res = next(resource_gen, None)
            _generator_finished.add_generator_resource(resource_gen)
        elif inspect.isasyncgenfunction(dep):
            resource_gen = dep(**kwargs)
            res = await resource_gen.__anext__()
            _generator_finished.add_generator_resource(resource_gen)
        elif inspect.iscoroutinefunction(dep):
            res = await dep(**kwargs)
            if isinstance(res, AsyncContextManager):
                res = await _async_context_exit_stak.enter_async_context(res)
            if isinstance(res, ContextManager):
                res = _async_context_exit_stak.enter_context(res)
        elif inspect.isfunction(dep):
            res = dep(**kwargs)
            if isinstance(res, AsyncContextManager):
                res = await _async_context_exit_stak.enter_async_context(res)
            if isinstance(res, ContextManager):
                res = _async_context_exit_stak.enter_context(res)
        else:
            raise ValueError(f"can't resolve resource {dep.__name__}, resource should be generator or context manager or function")

        if res is None:
            raise ValueError(f"resource can't be None, error while init {dep.__name__} resource")

        _resource_cacher.add_cache_depends(dep, res)
        return res

    wrapper.__name__ = dep.__name__
    wrapper.__module__ = dep.__module__

    return wrapper
