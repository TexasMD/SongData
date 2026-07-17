from pathlib import Path
from src.commands.enrich_msd_secondhand_review import run
from unittest.mock import patch, MagicMock

def test_run_dry_run(tmp_path: Path):
    review_csv = tmp_path / "review.csv"
    with open(review_csv, "w") as f:
        f.write("review_flags,left_title,left_artist\nmissing_shs_performance_url,Title,Artist\n")

    output_csv = tmp_path / "output.csv"

    run(False, review_csv, "WhoSampled", output_csv)

    assert not output_csv.exists()

@patch("src.commands.enrich_msd_secondhand_review.scrape_whosampled")
def test_run_write(mock_scrape, tmp_path: Path):
    review_csv = tmp_path / "review.csv"
    with open(review_csv, "w") as f:
        f.write("review_flags,left_title,left_artist\nmissing_shs_performance_url,Title,Artist\n")

    output_csv = tmp_path / "output.csv"

    mock_scrape.return_value = [{"title": "Cover Title", "artist": "Cover Artist"}]

    run(True, review_csv, "WhoSampled", output_csv)

    assert output_csv.exists()

    with open(output_csv) as f:
        content = f.read()
        assert "Cover Title" in content
        assert "Cover Artist" in content
        assert "Title" in content # query_title
