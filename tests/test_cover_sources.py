from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
import csv
import json
import sys

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
    assert client.session.trust_env is False

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


def test_coverdata_batch_writer_logs_progress_and_heartbeat(tmp_path):
    script_path = Path(__file__).resolve().parents[1] / "basket" / "coverdata_shs_ci.py"
    spec = spec_from_file_location("coverdata_shs_ci", script_path)
    module = module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    output = tmp_path / "covers.csv"
    log = tmp_path / "covers.log"
    heartbeat = tmp_path / "covers.status.json"
    rows = [
        {
            "performing_artist": "Cover Artist",
            "title": "Song A",
            "year": "",
            "album": "",
            "genre": "",
            "original_artist": "Original Artist",
            "original_song_title": "Song A",
            "original_album": "",
            "original_year": "",
            "secondhandsongs_artist_id": "",
            "secondhandsongs_title_id": "",
            "secondhandsongs_performance_id": "",
            "secondhandsongs_album_id": "",
            "source": "test",
            "queried_at_utc": "",
            "source_url": "https://example.test/song-a",
        }
    ]

    module.write_in_batches(rows, output, batch_size=1, log_path=log, heartbeat_path=heartbeat, source_count=1)

    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert written[0]["performing_artist"] == "Cover Artist"
    assert "Progress appended=1" in log.read_text(encoding="utf-8")
    payload = json.loads(heartbeat.read_text(encoding="utf-8"))
    assert payload["state"] == "running"
    assert payload["appended"] == 1


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


def test_secondhandsongs_client_uses_api_key(monkeypatch):
    monkeypatch.setenv("SECONDHANDSONGS_API_KEY", "test-shs-key")

    client = SecondHandSongsClient()

    assert client.session.headers["X-API-Key"] == "test-shs-key"


def test_secondhandsongs_client_paginates_until_total_results(monkeypatch):
    client = SecondHandSongsClient()
    pages_seen = []

    def fake_get(url, params=None, timeout=None):
        page = params.get("page", 0)
        pages_seen.append(page)
        rows = [
            {
                "entityType": "performance",
                "uri": f"https://secondhandsongs.com/performance/{page}-{index}",
                "title": params["title"],
                "performer": {"name": f"Artist {page}-{index}"},
                "isOriginal": False,
            }
            for index in range(2)
        ]
        if page == 2:
            rows = rows[:1]
        return FakeResponse(
            200,
            {
                "totalResults": 5,
                "resultPage": rows,
                "skippedResults": page * 2,
            },
            f"{url}?page={page}",
        )

    monkeypatch.setattr(client.session, "get", fake_get)

    rows = client.search_performances("Blackbird", page_size=2, max_pages=10)

    assert len(rows) == 5
    assert pages_seen == [0, 1, 2]


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
