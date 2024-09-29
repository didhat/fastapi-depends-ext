## Fastapi depends extension

![PyPI - Version](https://img.shields.io/pypi/v/fastapi-depends-extension?color=green)
[![Supported versions](https://img.shields.io/pypi/pyversions/fastapi-depends-extension.svg)](https://pypi.python.org/pypi/fastapi-depends-extension)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/didhat/fastapi-depends-ext/github-ci.yml)](https://github.com/reagento/dishka/actions)

### Purpose

This library extends capabilities of standard Depends di in FastaAPI and add Resources that creating only once and than
dependency always return created object at first time.
This is convenient when we create some kind of connection in the database or want to use a long-time object for the
entire application. The extension can also correctly handle resource closures on shutdown application in the familiar
Depends style. With this extension you don't need to create global variables and other strange things in your code.

### Quickstart

1. Install extension

```shell
pip install fastapi-depends-extension
```

2. Create FastApi application and setup di extenstion

```python
from fastapi import FastAPI, Depends
from extdepends import setup_extend_di, on_di_shutdown

app = FastAPI(lifespan=on_di_shutdown)
setup_extend_di(app)
```

or you can extend your own lifespan

```python
from extdepends import setup_extend_di, on_di_shutdown


async def app_lifespan(app):
    print("your own code")
    yield
    await on_di_shutdown(app)
    print("your close code")


app = FastApi(lifespan=app_lifespan)
```

3. After that you can define your resource and use it in routes almost just like common Depends function, resource only
   does not support callable classes. All current methods for creating resources are described below. Notice that
   function resource_with_close will always return the same resource. Also it is not possible call this function call
   outside di FastAPI, because of serious modification under the hood.

```python
@resource
async def resource_with_close():
    print("open resource logic")
    yield "resource"
    print("close resource login on shutdown application")


app.get("/test")


async def test(dep=Depends(resource_with_close)):
    return dep
```

also you can define others Depends resources or common depends function in resource and it will be work

```python

@resource
def setting():
    return {"setting": 12}


def common_depends():
    return 12


@resource
async def resource_with_close(settings=Depends(setting), common=Depends(common_depends)):
    print(f"open resource logic, with setting: {settings} and common depends {common}")
    yield "resource"
    print("close resource on shutdown resource")
```

### All methods for creating different resources:

1. Resource with closing supports asynchronous and synchronous generators:

```python

@resource
async def async_resource_with_close():
    print("open async resource")
    yield "resource"
    print("close resource on shutdown app")

@resource
def sync_resource_with_close():
   print("open sync resource")
   yield "resource"
   print("close resource on shutdown app")

```

2. Resource with closing has contextmanager support is such way:

```python
from contextlib import asynccontextmanager, contextmanager

@resource
@asynccontextmanager
async def async_context_manager():
   print("open async context manager depends")
   yield "resource"
   print("close async context manager")

@resource
@contextmanager
async def sync_context_manager():
   print("open sync context manager depends")
   yield "resource"
   print("close sync context manager depends")

```

The resource will open a context manager and return the resource that was used throughout the lifecycle of the application. Upon shutdown, the context manager will be closed.

3. Resource without close logic, it's just like singletone

```python

@resource
async def async_resource():
    await asyncio.sleep(2)
    return "resource"

@resource
def sync_resource():
   return "resource"
```


### Limitations

1. Callable classes has not support yet
2. Does not support functions with *args and **kwargs in arguments
3. Decorated functions also may not work correctly



