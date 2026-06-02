"""Tests for the source-aware RAG classification in app.services.ai_service."""
from app.services.ai_service import (
    _classify_source,
    _extract_yt_title,
    _YT_TITLE_RE,
)


def test_classify_source_youtube_by_session_prefix():
    assert _classify_source("yt_abc123def456", "anything") == "youtube"


def test_classify_source_youtube_by_content_prefix():
    assert _classify_source("any_session", "[YouTube] Some Video (1/3)") == "youtube"


def test_classify_source_chat_by_default():
    assert _classify_source("normal-uuid-session", "Just a chat message") == "chat"


def test_classify_source_youtube_takes_precedence_when_both_match():
    # yt_ prefix wins regardless of content
    assert _classify_source("yt_abc", "[YouTube] Some Video (1/3)") == "youtube"


def test_extract_yt_title_standard_format():
    content = "[YouTube] How to Train a Robot (1/5)\n\nFirst chunk text here."
    assert _extract_yt_title(content) == "How to Train a Robot"


def test_extract_yt_title_handles_no_slash_pattern():
    # No (N/M) suffix — should not match
    content = "[YouTube] Some Video\n\nBody"
    assert _extract_yt_title(content) is None


def test_extract_yt_title_handles_no_prefix():
    content = "Just a normal message"
    assert _extract_yt_title(content) is None


def test_extract_yt_title_handles_multiline_content():
    content = "[YouTube] Multi Line Title (10/12)\nLine 2\nLine 3"
    assert _extract_yt_title(content) == "Multi Line Title"


def test_extract_yt_title_handles_special_chars():
    content = "[YouTube] C++ vs Rust: A Deep Dive (1/1)\n\nBody"
    assert _extract_yt_title(content) == "C++ vs Rust: A Deep Dive"


def test_yt_title_regex_compiles():
    # Sanity check that the regex is at module level
    assert _YT_TITLE_RE.pattern.startswith(r"^\[YouTube\]")
