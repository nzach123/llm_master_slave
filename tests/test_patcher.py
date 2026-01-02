import pytest
import os
from pathlib import Path
from tools.patcher import read_file, write_file, apply_patch

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

def test_apply_patch_success(tmp_path):
    f = tmp_path / "patch_me.py"
    f.write_text("old_content", encoding="utf-8")
    result = apply_patch(str(f), "old_content", "new_content")
    assert result is True
    assert f.read_text(encoding="utf-8") == "new_content"

def test_apply_patch_not_found(tmp_path):
    f = tmp_path / "missing.py"
    f.write_text("actual_content", encoding="utf-8")
    result = apply_patch(str(f), "not_there", "replacement")
    assert result is False
    assert f.read_text(encoding="utf-8") == "actual_content"

def test_apply_patch_idempotent(tmp_path):
    f = tmp_path / "idempotent.py"
    f.write_text("already_patched", encoding="utf-8")
    # If search block is missing but replace block is present, return True
    result = apply_patch(str(f), "original", "already_patched")
    assert result is True
    assert f.read_text(encoding="utf-8") == "already_patched"

def test_apply_patch_first_occurrence_only(tmp_path):
    f = tmp_path / "multiple.py"
    f.write_text("match match", encoding="utf-8")
    result = apply_patch(str(f), "match", "found")
    assert result is True
    assert f.read_text(encoding="utf-8") == "found match"
