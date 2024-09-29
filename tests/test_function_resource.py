import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di

app = FastAPI()
setup_extend_di(app)


@resource
async def async_func_depends():
    return random.randint(1, 100)


@resource
def sync_func_depends():
    return random.randint(1, 100)


@app.get("/sync_depends_resource")
async def get_sync_depends(sync_dep=Depends(sync_func_depends)):
    return sync_dep


@app.get("/async_depends_resource")
async def get_async_depends(async_dep=Depends(async_func_depends)):
    return async_dep


client = TestClient(app)


def test_sync_resource_depends():
    sync_resource_1 = client.get("/sync_depends_resource").json()
    sync_resource_2 = client.get("/sync_depends_resource").json()
    sync_resource_3 = client.get("/sync_depends_resource").json()
    assert sync_resource_1 == sync_resource_2 == sync_resource_3


def test_async_resource_depends():
    async_resource_1 = client.get("/async_depends_resource").json()
    async_resource_2 = client.get("/async_depends_resource").json()
    async_resource_3 = client.get("/async_depends_resource").json()

    assert async_resource_1 == async_resource_2 == async_resource_3
