from ward import test, fixture

from darkseer.informants import OpenDotaClient


@fixture
async def client():
    opendota_client = OpenDotaClient()
    yield opendota_client
    await opendota_client.aclose()


@test('OpenDota.explorer returns JSON results', tags=['opendota', 'integration'])
async def _(client=client):
    q = """
        SELECT match_id
          FROM player_matches
         GROUP BY match_id
         ORDER BY match_id
         LIMIT 50
    """
    r = await client.explorer(q)
    assert isinstance(r, list)
    assert isinstance(r[0], dict)
