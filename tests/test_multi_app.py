import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown


@resource
async def get_resource():
    return random.randint(1, 1000)


main_app = FastAPI(lifespan=on_di_shutdown)

app_1 = FastAPI()
app_2 = FastAPI()

setup_extend_di([main_app, app_1, app_2])


@app_1.get("/app_1")
async def return_common_app_resource(res=Depends(get_resource)):
    return res


@app_2.get("/app_2")
async def return_common_app_2_resource(res=Depends(get_resource)):
    return res


main_app.mount("/test1", app_1)
main_app.mount("/test2", app_2)


def test_get_common_resource_from_multi_app():
    with TestClient(main_app) as client:
        res11 = client.get("/test1/app_1").json()
        res12 = client.get("/test1/app_1").json()
        res21 = client.get("test2/app_2").json()
        res22 = client.get("test2/app_2").json()

    assert res11 == res12 == res21 == res22
