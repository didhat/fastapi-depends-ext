import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)


@resource
async def resource_for_override():
    return 10


@app.get("/resource")
async def get_resource(dep: int = Depends(resource_for_override)):
    return dep


def test_resource_override():
    client = TestClient(app)
    response = client.get("/resource")
    assert response.json() == 10

    app.dependency_overrides[resource_for_override] = lambda: 20

    response = client.get("/resource")
    assert response.json() == 20






