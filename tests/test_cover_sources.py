from __future__ import annotations

from types import SimpleNamespace

from bs4 import BeautifulSoup

from src.cover_info_client import CoverInfoClient
from src.secondhandsongs_client import SecondHandSongsClient
from src.whosampled_client import WhoSampledClient


class FakeResponse:
    def __init__(self, status_code: int, payload, url: str):
        self.status_code = status_code
        self._payload = payload
        self.url = url

    def json(self):
        return self._payload


def test_cover_info_client_exact_search_and_details(monkeypatch):
    client = CoverInfoClient()
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append(("get", url, params))
        if url.endswith("/song/find"):
            return FakeResponse(
                200,
                [
                    {
                        "_id": "song-1",
                        "title": "Blackbird",
                        "artists": [{"artist": {"names": [{"name": "The Beatles"}]}}],
                    }
                ],
                f"{url}?input=Blackbird+The+Beatles&exact=True",
            )
        raise AssertionError(url)

    def fake_post(url, json=None, timeout=None):
        seen.append(("post", url, json))
        return FakeResponse(
            200,
            {
                "title": "Blackbird",
                "artists": [{"artist": {"names": [{"name": "The Beatles"}]}}],
                "release_date": "1968",
                "covers": [
                    {
                        "song": {
                            "title": "Blackbird",
                            "artists": [{"artist": {"names": [{"name": "Eva Cassidy"}]}}],
                            "release_date": "1998",
                        }
                    }
                ],
                "originals": [],
            },
            f"{url}",
        )

    monkeypatch.setattr(client.session, "get", fake_get)
    monkeypatch.setattr(client.session, "post", fake_post)

    rows = client.extract_covers("Blackbird", "The Beatles")
    assert rows == [
        {
            "title": "Blackbird",
            "artist": "Eva Cassidy",
            "musicbrainz_recording_id": None,
            "cover_song": "Yes",
            "original_title": "Blackbird",
            "original_artist": "The Beatles",
            "original_year": "1968",
            "source": "cover.info",
        }
    ]
    assert [entry[0] for entry in seen] == ["get", "post"]


def test_secondhandsongs_client_groups_exact_title_versions(monkeypatch):
    client = SecondHandSongsClient()
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append((url, params))
        title = params.get("title", "")
        performer = params.get("performer", "")
        if performer:
            payload = {
                "totalResults": 1,
                "resultPage": [
                    {
                        "entityType": "performance",
                        "uri": "https://secondhandsongs.com/performance/cover-1",
                        "title": title,
                        "performer": {"name": performer},
                        "isOriginal": False,
                    }
                ],
            }
        else:
            payload = {
                "totalResults": 2,
                "resultPage": [
                    {
                        "entityType": "performance",
                        "uri": "https://secondhandsongs.com/performance/original-1",
                        "title": title,
                        "performer": {"name": "Original Artist"},
                        "isOriginal": True,
                    },
                    {
                        "entityType": "performance",
                        "uri": "https://secondhandsongs.com/performance/cover-1",
                        "title": title,
                        "performer": {"name": "Cover Artist"},
                        "isOriginal": False,
                    },
                ],
            }
        return FakeResponse(200, payload, f"{url}?title={title}&performer={performer}&format=json")

    monkeypatch.setattr(client.session, "get", fake_get)

    rows = client.extract_covers("Blackbird", "Cover Artist", original_year="1968")
    assert rows == [
        {
            "title": "Blackbird",
            "artist": "Cover Artist",
            "musicbrainz_recording_id": None,
            "cover_song": "Yes",
            "original_title": "Blackbird",
            "original_artist": "Original Artist",
            "original_year": "1968",
            "source": "SecondHandSongs",
        }
    ]
    assert len(seen) >= 2


def test_whosampled_parser_handles_track_connections():
    client = WhoSampledClient()
    html = """
    <html>
      <body>
        <section class="trackItem">
          <h3 class="trackName"><a><span itemprop="name">Blackbird</span></a></h3>
          <a class="trackCover" title="The Beatles by Blackbird"></a>
          <div class="trackConnections">
            <div class="track-connection">
              <span class="sampleAction">was covered in</span>
              <li><a class="connectionName">Blackbird</a> by Eva Cassidy (1998)</li>
            </div>
          </div>
        </section>
      </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows = client.extract_covers_from_page(soup, "Blackbird", "The Beatles")
    assert rows[0]["title"] == "Blackbird"
    assert rows[0]["artist"] == "Eva Cassidy"
    assert rows[0]["original_title"] == "Blackbird"
    assert rows[0]["original_artist"] == "The Beatles"
