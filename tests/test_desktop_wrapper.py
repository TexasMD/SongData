import pytest
from unittest.mock import patch, MagicMock
from apps.musicdb_desktop.backend_manager import BackendManager

@pytest.fixture
def mock_multiprocessing():
    with patch("apps.musicdb_desktop.backend_manager.multiprocessing.Process") as mock_process_cls:
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.is_alive.return_value = True
        mock_process_cls.return_value = mock_proc
        yield mock_process_cls, mock_proc

@pytest.fixture
def mock_psutil():
    with patch("apps.musicdb_desktop.backend_manager.psutil") as mock_ps:
        mock_parent = MagicMock()
        mock_child = MagicMock()
        mock_parent.children.return_value = [mock_child]
        mock_ps.Process.return_value = mock_parent
        mock_ps.wait_procs.return_value = ([], []) # (gone, alive)
        yield mock_ps, mock_parent, mock_child

def test_backend_manager_start(mock_multiprocessing):
    mock_process_cls, mock_proc = mock_multiprocessing

    manager = BackendManager(port=9999)
    assert not manager.is_running()

    result = manager.start()

    assert result is True
    assert manager.is_running()

    mock_process_cls.assert_called_once()
    mock_proc.start.assert_called_once()

    # Starting again should return False
    assert manager.start() is False

def test_backend_manager_stop(mock_multiprocessing, mock_psutil):
    mock_process_cls, mock_proc = mock_multiprocessing
    mock_ps, mock_parent, mock_child = mock_psutil

    manager = BackendManager()
    manager.start()
    assert manager.is_running()

    # We must not set is_alive to False *before* stop() because stop() checks is_running() first!
    # Let the mock maintain is_alive=True during the is_running check inside stop().
    result = manager.stop()

    # Then for subsequent checks, simulate it being dead
    mock_proc.is_alive.return_value = False

    assert result is True
    assert not manager.is_running()

    mock_ps.Process.assert_called_once_with(12345)
    mock_child.terminate.assert_called_once()
    mock_parent.terminate.assert_called_once()

    # Stopping again should return False
    assert manager.stop() is False

def test_backend_manager_poll_detects_exit(mock_multiprocessing):
    mock_process_cls, mock_proc = mock_multiprocessing

    manager = BackendManager()
    manager.start()

    # Simulate process exit
    mock_proc.is_alive.return_value = False

    assert not manager.is_running()
    assert manager.process is None
