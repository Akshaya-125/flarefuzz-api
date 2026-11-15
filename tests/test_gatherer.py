import asyncio

from flarefuzz_api.gatherer import _links
from flarefuzz_api import gatherer


def test_link_extraction_follows_json_objects_but_rejects_non_nasa_hosts():
    record = {
        "Project": {"links": [{"rel": "resource", "href": "/geode-py/ws/repo/resource/1"}]},
        "Experiment Hardware": {"Link": "https://www1.grc.nasa.gov/some/general-page"},
        "external": {"url": "https://example.com/data.csv"},
    }
    assert _links(record, "https://psi.nasa.gov/geode-py/ws/repo/search") == [
        "https://psi.nasa.gov/geode-py/ws/repo/resource/1"
    ]


def test_link_extraction_handles_multiple_space_separated_urls():
    record = {
        "Resources": {
            "Link": "https://psi.nasa.gov/data/a.csv https://psi.nasa.gov/data/b.csv"
        }
    }
    assert _links(record, "https://psi.nasa.gov") == [
        "https://psi.nasa.gov/data/a.csv",
        "https://psi.nasa.gov/data/b.csv",
    ]


def test_gatherer_follows_project_resource_links_and_inventories_csv(monkeypatch):
    class Response:
        def __init__(self, *, payload=None, content=b"", headers=None, url=""):
            self._payload = payload
            self.content = content
            self.headers = headers or {}
            self.url = url

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def get(self, url, params=None):
            if url == gatherer.SEARCH_URL:
                return Response(
                    payload={
                        "hits": {
                            "hits": [
                                {
                                    "_source": {
                                        "Accession": "PSI-TEST",
                                        "Title": "Test project",
                                    }
                                }
                            ]
                        }
                    },
                    url=url,
                )
            if url == f"{gatherer.INVESTIGATION_DATA_URL}/PSI-TEST":
                return Response(
                    payload={"Resources": [{"href": "/resource/test.csv"}]},
                    headers={"content-type": "application/json"},
                    url=url,
                )
            if url == "https://psi.nasa.gov/resource/test.csv":
                return Response(
                    content=b"Flame diameter (mm)\n12\n",
                    headers={"content-type": "text/csv"},
                    url=url,
                )
            raise AssertionError(f"Unexpected URL: {url}")

    monkeypatch.setattr(gatherer.httpx, "AsyncClient", Client)
    results = asyncio.run(gatherer.gather_csv_inventories(term="test"))
    assert len(results) == 1
    result = results[0]
    assert result.project_id == "PSI-TEST"
    assert result.inventory.parameters[0].canonical_name == "flame_diameter"
    assert result.inventory.parameters[0].conversion_factor == 0.001
