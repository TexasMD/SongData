import os
from unittest.mock import patch
from datetime import datetime
from src.utils import backup_file

def test_backup_file_success(tmp_path):
    # Create a dummy file to backup
    test_file = tmp_path / "test_data.txt"
    test_file.write_text("dummy content")

    # Define a fixed time for our mock
    fixed_time = datetime(2024, 1, 1, 12, 30, 45)
    expected_timestamp = fixed_time.strftime("%Y%m%d_%H%M%S")
    expected_backup_name = f"test_data_{expected_timestamp}.bak.txt"
    expected_backup_path = os.path.join(str(tmp_path), expected_backup_name)

    # Patch datetime inside src.utils so it uses our fixed time
    with patch("src.utils.datetime") as mock_datetime:
        mock_datetime.now.return_value = fixed_time

        # Call the function
        actual_backup_path = backup_file(str(test_file))

        # Verify the returned path is correct
        assert actual_backup_path == expected_backup_path

        # Verify the backup file was actually created
        assert os.path.exists(actual_backup_path)

        # Verify the content is the same
        with open(actual_backup_path, "r") as f:
            assert f.read() == "dummy content"

def test_backup_file_nonexistent(tmp_path):
    # Pass a path that does not exist
    non_existent_file = str(tmp_path / "does_not_exist.txt")

    # Call the function
    result = backup_file(non_existent_file)

    # It should return an empty string
    assert result == ""
