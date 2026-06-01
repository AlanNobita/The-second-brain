import pytest
import tempfile
import os
from app.services.note_service import debloat_and_structure, save_note_file

SAMPLE_TRANSCRIPT = """
hey guys welcome back to the channel today we're talking about python
before we start don't forget to like and subscribe
python is a dynamically typed language which means you don't need to declare types
it was created by guido van rossum in 1991
one key feature is that indentation matters for block structure
another important thing is that python has automatic memory management
thanks to our sponsor raid shadow legends for making this video possible
check them out at the link below
so to summarize python is great for beginners and experts alike
make sure to hit that bell icon for more content
"""

def test_debloat_removes_greetings():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert "hey guys" not in result.lower()
    assert "like and subscribe" not in result.lower()
    assert "sponsor" not in result.lower()

def test_debloat_preserves_substance():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert "dynamically typed" in result
    assert "guido van rossum" in result.lower() or "Guido van Rossum" in result
    assert "1991" in result
    assert "indentation" in result
    assert "memory management" in result

def test_debloat_returns_markdown():
    result = debloat_and_structure(SAMPLE_TRANSCRIPT, "Python Basics", "TestChannel")
    assert "##" in result or result.startswith("#")

def test_save_note_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = save_note_file("# Test\n\nContent", "Test Video Title", "2026-06-01", output_dir=tmpdir)
        assert os.path.exists(path)
        with open(path, "r") as f:
            content = f.read()
        assert "Test Video Title" in content or "# Test" in content
