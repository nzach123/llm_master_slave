import pytest
from unittest.mock import patch, MagicMock
from tools.resource_monitor import get_available_ram, get_available_vram, check_resources_threshold

def test_get_available_ram():
    with patch('psutil.virtual_memory') as mock_vm:
        mock_vm.return_value.available = 4 * (1024 ** 3)  # 4 GB
        assert get_available_ram() == 4.0

def test_get_available_vram_gpu():
    with patch('subprocess.check_output') as mock_cmd:
        mock_cmd.return_value = "4096\n2048"  # Two GPUs, 6GB total free
        assert get_available_vram() == 6.0

def test_get_available_vram_no_gpu():
    with patch('subprocess.check_output') as mock_cmd:
        mock_cmd.side_effect = FileNotFoundError()
        assert get_available_vram() == 100.0

def test_check_resources_threshold_pass():
    with patch('tools.resource_monitor.get_available_ram') as mock_ram:
        with patch('tools.resource_monitor.get_available_vram') as mock_vram:
            mock_ram.return_value = 3.0
            mock_vram.return_value = 3.0
            assert check_resources_threshold(min_gb=2.0) is True

def test_check_resources_threshold_fail_ram():
    with patch('tools.resource_monitor.get_available_ram') as mock_ram:
        with patch('tools.resource_monitor.get_available_vram') as mock_vram:
            mock_ram.return_value = 1.0
            mock_vram.return_value = 3.0
            assert check_resources_threshold(min_gb=2.0) is False

def test_check_resources_threshold_fail_vram():
    with patch('tools.resource_monitor.get_available_ram') as mock_ram:
        with patch('tools.resource_monitor.get_available_vram') as mock_vram:
            mock_ram.return_value = 3.0
            mock_vram.return_value = 1.0
            assert check_resources_threshold(min_gb=2.0) is False
