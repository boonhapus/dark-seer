import asyncio

from ward import fixture


@fixture(scope='global')
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()
