import random

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from extdepends.di import resource, setup_extend_di, on_di_shutdown, _resources_cache_di, ResourceCacher

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)


class ClosingResource:
    def __init__(self, is_close: bool = False):
        self.value = random.randint(1, 1000)
        self.is_close = False


class Service:
    def __init__(self, sync_resource: ClosingResource, async_resource: ClosingResource):
        self.sync_resource = sync_resource
        self.async_resource = async_resource

    async def get_resources(self):
        return {"sync": self.sync_resource.value, "async": self.async_resource.value}


@resource
async def async_generator_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@resource
async def sync_generator_depends():
    res = ClosingResource()
    yield res
    res.is_close = True


@resource
async def resource_with_depends_on_other_resources(sync_res: ClosingResource = Depends(sync_generator_depends)):
    res = ClosingResource()
    res.value = sync_res.value
    yield res
    res.is_close = True


def common_depends():
    return 10


@resource
async def resource_with_common_depends(common: int = Depends(common_depends)):
    res = ClosingResource()
    res.value = common
    yield res
    res.is_close = True


async def service_factory(sync_res: ClosingResource = Depends(sync_generator_depends),
                          async_res: ClosingResource = Depends(async_generator_depends)):
    return Service(sync_res, async_res)


@app.get("/common_depends")
async def get_common_depends(common: ClosingResource = Depends(resource_with_common_depends)):
    return {"value": common.value, "is_close": common.is_close}


@app.get("/depended_resource")
async def get_resource_depends_on_other_resources(resource: ClosingResource = Depends(resource_with_depends_on_other_resources)):
    return {"value": resource.value, "is_close": resource.is_close}


@app.get("/service")
async def get_service(service: Service = Depends(service_factory)):
    return await service.get_resources()


def test_get_resource_in_depends():
    with TestClient(app) as client:
        response_1 = client.get("/service").json()
        response_2 = client.get("/service").json()
        response_3 = client.get("/service").json()

    assert response_1 == response_2 == response_3
    resource_cacher: ResourceCacher = app.dependency_overrides[_resources_cache_di]()
    async_generator_resource = resource_cacher.get_cache_depends(async_generator_depends)
    sync_generator_resource = resource_cacher.get_cache_depends(sync_generator_depends)

    assert async_generator_resource.is_close is True
    assert sync_generator_resource.is_close is True


def test_resource_depends_on_other_resources():
    with TestClient(app) as client:
        response_1 = client.get("/depended_resource").json()
        response_2 = client.get("/depended_resource").json()
        response_3 = client.get("/depended_resource").json()

    assert response_1 == response_2 == response_3
    resource_cacher: ResourceCacher = app.dependency_overrides[_resources_cache_di]()
    sync_resource = resource_cacher.get_cache_depends(sync_generator_depends)
    depends_on_resource = resource_cacher.get_cache_depends(resource_with_depends_on_other_resources)

    assert sync_resource.value == depends_on_resource.value
    assert sync_resource.is_close is True
    assert depends_on_resource.is_close is True


def test_common_depends():
    with TestClient(app) as client:
        response_1 = client.get("/common_depends").json()
        response_2 = client.get("/common_depends").json()
        response_3 = client.get("/common_depends").json()

    assert response_1 == response_2 == response_3 == {"value": 10, "is_close": False}
    resource_cacher: ResourceCacher = app.dependency_overrides[_resources_cache_di]()
    common_resource = resource_cacher.get_cache_depends(resource_with_common_depends)

    assert common_resource.is_close is True
