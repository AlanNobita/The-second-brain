import os
import sys
import tempfile
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models import youtube_db as ydb
from app.services import subscription_service as ss

_db_tmp = os.path.join(tempfile.mkdtemp(), "test.db")
ydb.DB_PATH = _db_tmp
ydb.init_youtube_db()


def test_subscribe():
    with patch("app.services.subscription_service.get_channel_videos", return_value=[]):
        sub = ss.subscribe("https://youtube.com/@testchannel")
    assert sub["channel_name"] is not None


def test_list_subscriptions():
    subs = ss.list_subscriptions()
    assert isinstance(subs, list)


def test_has_due_subscriptions():
    result = ss.has_due_subscriptions()
    assert isinstance(result, bool)


def test_unsubscribe():
    with patch("app.services.subscription_service.get_channel_videos", return_value=[]):
        sub = ss.subscribe("https://youtube.com/@unsubtest")
    result = ss.unsubscribe(sub["id"])
    assert result is True


def test_check_all_subscriptions():
    result = ss.check_all_subscriptions()
    assert "checked" in result
    assert "new_videos" in result
