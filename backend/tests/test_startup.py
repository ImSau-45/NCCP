from backend.app import create_app


def test_app_factory_boots_and_registers_routes():
    app = create_app()
    assert app is not None
    registered = {rule.endpoint: rule.rule for rule in app.url_map.iter_rules()}
    assert any(endpoint == 'health' for endpoint in registered)
    assert any(rule.startswith('/api/') for rule in registered.values())
