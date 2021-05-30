import httpx

from darkseer.util import RateLimitedHTTPClient
from .schema import GameVersion


class Stratz(RateLimitedHTTPClient):
    """
    Wrapper around the STRATZ REST API.

    Documentation:
        https://docs.stratz.com/

    [ANON] Rate limit is 300/hour, 150/minute @ 20 requests per second.
    [AUTH] Rate limit is 500/hour, 150/minute @ 20 requests per second.

    Attributes
    ----------
    bearer_token : str, default None
        token in the format "Bearer XXXXXX..."
        if supplied, elevates the per-hour rate limit
    """
    def __init__(self, bearer_token: str=None):
        super().__init__(tokens=300, seconds=3600, base_url='https://api.stratz.com')

        if bearer_token is not None:
            self.tokens = 500
            self.headers.update({'authorization': f'Bearer {bearer_token}'})

    async def query(self, q: str, **variables) -> httpx.Request:
        """
        """
        r = await self.post('/graphql', data={'query': q}, params=variables)
        r.raise_for_status()
        return r

    async def patches(self):
        """
        Return a list of game versions.
        """
        q = """
        query Patches {
          constants {
            game_version: gameVersions {
              patch_id: id
              patch: name
              release_dt: asOfDateTime
            }
          }
        }
        """
        resp = await self.query(q)
        data = resp.json()['data']['constants']
        return [GameVersion(**v) for v in data['game_version']]

    def __repr__(self) -> str:
        return f'<StratzClient {self.rate}r/s>'
