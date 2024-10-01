import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown, ResourceContainer

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)


class ClosingResource:
    def __init__(self, is_close: bool = False):
        self.value = random.randint(1, 1000)
        self.is_close = False


@resource
async def async_generator_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@resource
def sync_generator_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@app.get("/async_generator_resource")
async def get_async_generator_resource(async_gen_res: ClosingResource = Depends(async_generator_depends)):
    return {"value": async_gen_res.value, "is_close": async_gen_res.is_close}


@app.get("/sync_generator_resource")
async def get_sync_generator_resource(sync_gen_res: ClosingResource = Depends(sync_generator_depends)):
    return {"value": sync_gen_res.value, "is_close": sync_gen_res.is_close}


def test_async_generator_resource():

    with TestClient(app) as client:
        resource_1 = client.get("/async_generator_resource").json()
        resource_2 = client.get("/async_generator_resource").json()
        resource_3 = client.get("/async_generator_resource").json()

    assert resource_1 == resource_2 == resource_3

    container: ResourceContainer = app.dependency_overrides[ResourceContainer]()
    assert container._instances == {}



def test_sync_generator_resource():

    with TestClient(app) as client:
        resource_1 = client.get("/sync_generator_resource").json()
        resource_2 = client.get("/sync_generator_resource").json()
        resource_3 = client.get("/sync_generator_resource").json()

    assert resource_1 == resource_2 == resource_3

    container: ResourceContainer = app.dependency_overrides[ResourceContainer]()
    assert container._instances == {}

