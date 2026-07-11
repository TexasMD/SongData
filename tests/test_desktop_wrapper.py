import pytest
from unittest.mock import patch, MagicMock
from apps.musicdb_desktop.backend_manager import BackendManager

@pytest.fixture
def mock_subprocess():
    with patch("apps.musicdb_desktop.backend_manager.subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.poll.return_value = None # Running
        mock_popen.return_value = mock_proc
        yield mock_popen, mock_proc

@pytest.fixture
def mock_psutil():
    with patch("apps.musicdb_desktop.backend_manager.psutil") as mock_ps:
        mock_parent = MagicMock()
        mock_child = MagicMock()
        mock_parent.children.return_value = [mock_child]
        mock_ps.Process.return_value = mock_parent
        mock_ps.wait_procs.return_value = ([], []) # (gone, alive)
        yield mock_ps, mock_parent, mock_child

def test_backend_manager_start(mock_subprocess):
    mock_popen, mock_proc = mock_subprocess

    manager = BackendManager(port=9999)
    assert not manager.is_running()

    result = manager.start()

    assert result is True
    assert manager.is_running()

    # Check that it called Popen with the right port
    mock_popen.assert_called_once()
    args = mock_popen.call_args[0][0]
    assert "9999" in args
    assert "uvicorn" in args

    # Starting again should return False
    assert manager.start() is False

def test_backend_manager_stop(mock_subprocess, mock_psutil):
    mock_popen, mock_proc = mock_subprocess
    mock_ps, mock_parent, mock_child = mock_psutil

    manager = BackendManager()
    manager.start()
    assert manager.is_running()

    result = manager.stop()

    assert result is True
    assert not manager.is_running()

    # Verify the tree was terminated
    mock_ps.Process.assert_called_once_with(12345)
    mock_child.terminate.assert_called_once()
    mock_parent.terminate.assert_called_once()

    # Stopping again should return False
    assert manager.stop() is False

def test_backend_manager_poll_detects_exit(mock_subprocess):
    mock_popen, mock_proc = mock_subprocess

    manager = BackendManager()
    manager.start()

    # Simulate process exit
    mock_proc.poll.return_value = 0

    assert not manager.is_running()
    assert manager.process is None
