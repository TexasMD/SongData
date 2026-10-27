import sqlite3
from pathlib import Path

import shs_universal_page_parser as parser


def test_sanitize_year_strips_float_suffix():
    assert parser.sanitize_year("1985.0") == "1985"
    assert parser.sanitize_year("June 15, 1989") == "1989"
    assert parser.sanitize_year("") == ""


def test_short_or_numeric_title_guard():
    assert parser.is_short_or_numeric_title("19") is True
    assert parser.is_short_or_numeric_title("Try") is True
    assert parser.is_short_or_numeric_title("Wicked Game") is False


def test_categorize_and_parse_work_html(tmp_path: Path):
    html = """<!DOCTYPE html>
    <html>
    <head>
      <title>Versions of Wicked Game written by Chris Isaak | SecondHandSongs</title>
      <link rel="canonical" href="https://secondhandsongs.com/work/1051/all" />
    </head>
    <body>
      <h1><span itemprop="name">Wicked Game</span></h1>
      <article>
        <p>First release by <a href="/artist/190"><span itemprop="byArtist">Chris Isaak</span></a> (June 1989)
           <a href="/performance/1051">Wicked Game</a></p>
      </article>
      <dl>
        <dt>Written by</dt><dd><a href="/artist/190">Chris Isaak</a></dd>
        <dt>ISWC</dt><dd>T-070.205.906-0</dd>
        <dt>Language</dt><dd>English</dd>
      </dl>
      <h2>Versions</h2>
      <table>
        <thead>
          <tr><th>Title</th><th>Performer</th><th>Release date</th><th>Info</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><a href="/performance/1051">Wicked Game</a></td>
            <td><a href="/artist/190">Chris Isaak</a></td>
            <td>1989.0</td>
            <td class="field-info">First release</td>
          </tr>
          <tr>
            <td><a href="/performance/9999">Wicked Game</a></td>
            <td><a href="/artist/190">Chris Isaak</a> duet with Guest Artist</td>
            <td>1995.0</td>
            <td class="field-info"></td>
          </tr>
          <tr>
            <td><a href="/performance/2000">Wicked Game</a></td>
            <td><a href="/artist/500">HIM</a></td>
            <td>1998</td>
            <td class="field-info"></td>
          </tr>
        </tbody>
      </table>
      <h2>Adaptations</h2>
      <table>
        <thead>
          <tr><th>Title</th><th>Performer</th><th>Release date</th><th>Info</th></tr>
        </thead>
        <tbody>
          <tr>
            <td><a href="/performance/3000">Juego Malvado</a></td>
            <td><a href="/artist/600">Spanish Artist</a></td>
            <td>2001</td>
            <td class="field-info">First release</td>
          </tr>
        </tbody>
      </table>
    </body>
    </html>
    """
    html_file = tmp_path / "02_wicked_game.html"
    html_file.write_text(html, encoding="utf-8")
    out_csv = tmp_path / "out.csv"
    out_db = tmp_path / "out.sqlite"
    excl_csv = tmp_path / "excluded_adaptations.csv"

    args = parser.parse_args(
        [
            "--input-file",
            str(html_file),
            "--output-csv",
            str(out_csv),
            "--database",
            str(out_db),
            "--excluded-csv",
            str(excl_csv),
            "--workers",
            "1",
        ]
    )
    pages_cnt, rows_cnt, adapt_cnt = parser.execute_pipeline(args)
    assert pages_cnt == 1
    assert rows_cnt == 4
    assert adapt_cnt == 1

    conn = sqlite3.connect(str(out_db))
    rows = conn.execute(
        "SELECT title, performer, release_year, is_first_release, is_adaptation, classification "
        "FROM table_rows ORDER BY row_id"
    ).fetchall()
    conn.close()

    assert rows[0] == ("Wicked Game", "Chris Isaak", 1989, 1, 0, "1strel")
    assert rows[1] == (
        "Wicked Game",
        "Chris Isaak duet with Guest Artist",
        1995,
        0,
        0,
        "aarw",
    )
    assert rows[2] == ("Wicked Game", "HIM", 1998, 0, 0, "cover")
    assert rows[3] == ("Juego Malvado", "Spanish Artist", 2001, 0, 1, "adaptation")
