from bullwatch_unified import create_app


def test_create_app():
    app = create_app()
    assert app is not None


def test_dashboard_route():
    app = create_app()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Bullwatch Unified" in resp.data
