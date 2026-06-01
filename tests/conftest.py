from unittest.mock import MagicMock

import pytest

# Pre-mock to avoid heavy / unavailable deps in tests
_mock_st = MagicMock()
_mock_st.SentenceTransformer = MagicMock
import sys as _sys
_sys.modules["sentence_transformers"] = _mock_st
_sys.modules["chromadb"] = MagicMock()
_sys.modules["chromadb.PersistentClient"] = MagicMock
_sys.modules["apscheduler"] = MagicMock()
_sys.modules["apscheduler.schedulers"] = MagicMock()
_sys.modules["apscheduler.schedulers.background"] = MagicMock()
_sys.modules["apscheduler.schedulers.background"].BackgroundScheduler = MagicMock

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client