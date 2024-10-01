import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)


async def original_provider():
    return random.randint(1, 10000)


cached_provider = resource(original_provider)


@app.get("/test1")
async def get_cached_res(res=Depends(cached_provider)):
    return res


@app.get("/test2")
async def get_common_res(res=Depends(original_provider)):
    return res


def test_res():
    with TestClient(app) as client:
        res1 = client.get("/test1").json()
        res12 = client.get("/test1").json()
        res2 = client.get("/test2").json()

        assert res1 == res12
        assert res2 != res1
