import pytest
import json

def test_yt_search(client):
    response = client.get("/yt/search?q=python+tutorial")
    assert response.status_code in (200, 400)  # 400 if no results, 200 with results

def test_yt_search_no_query(client):
    response = client.get("/yt/search")
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data

def test_yt_subscribe(client):
    response = client.post("/yt/subscribe", json={"channel_url": "https://youtube.com/@test"})
    assert response.status_code == 200
    data = response.get_json()
    assert "id" in data
    assert "channel_name" in data

def test_yt_subscriptions(client):
    response = client.get("/yt/subscriptions")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
