import asyncio
import random
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI, APIRouter, Depends
from extdepends.di import resource, setup_extend_di, on_di_shutdown
from contextlib import asynccontextmanager

router = APIRouter()


@dataclass
class CounterClass:
    counter: int
    name: str


class CounterService:
    def __init__(self, generator_counter: CounterClass, context_manager_counter: CounterClass, sync_gen_counter: CounterClass):
        self._generator = generator_counter
        self._context_manager = context_manager_counter
        self._sync_gen_counter = sync_gen_counter

    async def plus_counts(self):
        self._generator.counter += 1
        self._context_manager.counter += 1
        self._sync_gen_counter.counter += 1
        print(self._generator)
        print(self._context_manager)
        print(self._sync_gen_counter)

    def get_counts(self):
        return {
            self._generator.name: self._generator.counter,
            self._context_manager.name: self._context_manager.counter,
            self._sync_gen_counter.name: self._sync_gen_counter.counter,
        }


def a1():
    print("second level depends")


@resource
def setting(lol=Depends(a1)):
    print("setting depends")
    yield {"a1": 1, "b1": 12}
    print("close settings resource")


@resource
async def async_generator_resource(settings=Depends(setting)):
    print(f"create async generator resource, settings: {settings}")
    yield CounterClass(0, name="async generator resource")
    print("close async generator resource")


@resource
def sync_generator_resource(settings=Depends(setting)):
    print(f"create sync generator resource, settings, {settings}")
    yield CounterClass(0, name="sync generator resource")
    print("close sync generator resource")


@resource
@asynccontextmanager
async def async_context_manager_dep(settings=Depends(setting)):
    print(f"create context manager resource with settings: {settings}")
    yield CounterClass(0, name="context manager resource")
    print("close context manager resource")


@resource
def once_randomly_generated_resource(max_num: int):
    return random.randint(1, max_num)


@resource
async def once_fake_created_http_request_for_resource():
    await asyncio.sleep(3)
    current_owner = random.choice(["Max", "Dan", "John"])
    return current_owner


async def service_provider(generator_res=Depends(async_generator_resource),
                           context_manager_res=Depends(async_context_manager_dep),
                           sync_generator_res=Depends(sync_generator_resource),
                           ):
    return CounterService(
        generator_counter=generator_res,
        context_manager_counter=context_manager_res,
        sync_gen_counter=sync_generator_res,
    )


@router.post("/generator_plus")
async def plus_generator(generator_res=Depends(async_generator_resource)):
    generator_res.counter += 1
    print(generator_res)


@router.post("/context_plus")
async def plus_context(context_manager_res=Depends(async_context_manager_dep)):
    context_manager_res.counter += 1
    print(context_manager_res)


@router.post("/plus")
async def plus_all_counts(service: CounterService = Depends(service_provider)):
    await service.plus_counts()


@router.get("/info")
def get_counters(service: CounterService = Depends(service_provider)):
    return service.get_counts()


@router.get("/once_generated_random_resource")
def get_random_number(random_num=Depends(once_randomly_generated_resource)):
    return {"random": random_num}


@router.get("/service_owner")
async def get_cached_service_owner(owner=Depends(once_fake_created_http_request_for_resource)):
    return {"owner": owner}


def create_app():
    app = FastAPI(lifespan=on_di_shutdown)
    app.include_router(router)

    setup_extend_di(app)

    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), port=8087)
