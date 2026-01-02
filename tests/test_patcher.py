import pytest
import os
from pathlib import Path
from tools.patcher import read_file, write_file

def test_read_file_success(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world", encoding="utf-8")
    content = read_file(str(f))
    assert content == "hello world"

def test_read_file_not_found():
    with pytest.raises(FileNotFoundError):
        read_file("non_existent_file.txt")

def test_write_file_success(tmp_path):
    f = tmp_path / "output.txt"
    write_file(str(f), "content")
    assert f.read_text(encoding="utf-8") == "content"

def test_write_file_creates_dirs(tmp_path):
    f = tmp_path / "subdir" / "nested" / "file.txt"
    write_file(str(f), "nested content")
    assert f.exists()
    assert f.read_text(encoding="utf-8") == "nested content"

def test_write_file_atomic(tmp_path):
    # This is harder to test without mocking, but we can check if it works generally
    f = tmp_path / "atomic.txt"
    write_file(str(f), "initial")
    write_file(str(f), "updated")
    assert f.read_text(encoding="utf-8") == "updated"
