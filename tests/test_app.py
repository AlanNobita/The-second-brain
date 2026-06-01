

def test_health_endpoing(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200 
    assert "Second" in response.get_data(as_text=True)

    