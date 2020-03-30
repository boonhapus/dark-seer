from ward import test, fixture, each, skip

from darkseer.informants import StratzClient
from darkseer.schema import GameVersion, Hero, Item, Tournament, Match


@fixture
async def client():
    stratz_client = StratzClient()
    yield stratz_client
    await stratz_client.aclose()


@test('StratzClient.{method} returns List[{result.__schema_name__}]', tags=['stratz', 'integration'])
async def _(
    client=client,
    method=each('patches', 'tournaments'),
    result=each(GameVersion, Tournament)
):
    r = await getattr(client, method)()
    assert isinstance(r, list)
    assert isinstance(r[0], result)


@test('StratzClient.matches returns List[Match]', tags=['stratz', 'integration'])
async def _(client=client):
    r = await client.matches(4985891168, 4986133311, 4986260666, 4986362254, 4986461644)
    assert isinstance(r, list)
    assert isinstance(r[0], Match)


@skip('not implemented yet')
@test('StratzClient.heroes returns List[Hero]', tags=['stratz', 'integration'])
async def _(client=client):
    r = await client.heroes()
    assert isinstance(r, list)
    assert isinstance(r[0], Hero)


@skip('not implemented yet')
@test('StratzClient.items returns List[Item]', tags=['stratz', 'integration'])
async def _(client=client):
    r = await client.items()
    assert isinstance(r, list)
    assert isinstance(r[0], Item)
