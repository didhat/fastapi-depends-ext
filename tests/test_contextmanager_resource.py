import random
from contextlib import contextmanager, asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)


class ClosingResource:
    def __init__(self, is_close: bool = False):
        self.value = random.randint(1, 1000)
        self.is_close = False


@resource
@asynccontextmanager
async def async_contextmanager_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@resource
@contextmanager
def sync_contextmanager_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@app.get("/async_contextmanager_resource")
async def get_async_contextmanager_resource(async_cm_res: ClosingResource = Depends(async_contextmanager_depends)):
    return {"value": async_cm_res.value, "is_close": async_cm_res.is_close}


@app.get("/sync_contextmanager_resource")
async def get_sync_contextmanager_resource(sync_cm_res: ClosingResource = Depends(sync_contextmanager_depends)):
    return {"value": sync_cm_res.value, "is_close": sync_cm_res.is_close}


def test_async_contextmanager_resource():
    with TestClient(app) as client:
        resource_1 = client.get("/async_contextmanager_resource").json()
        resource_2 = client.get("/async_contextmanager_resource").json()
        resource_3 = client.get("/async_contextmanager_resource").json()

    assert resource_1 == resource_2 == resource_3



def test_sync_contextmanager_resource():
    with TestClient(app) as client:
        resource_1 = client.get("/sync_contextmanager_resource").json()
        resource_2 = client.get("/sync_contextmanager_resource").json()
        resource_3 = client.get("/sync_contextmanager_resource").json()

    assert resource_1 == resource_2 == resource_3

