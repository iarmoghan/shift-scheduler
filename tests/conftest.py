# tests/conftest.py
import pathlib, sys, importlib
import pytest

# Ensure repo root on path
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

mod = importlib.import_module("app")
flask_app = getattr(mod, "app")

@pytest.fixture
def app():
    flask_app.config.update(TESTING=True)
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def admin_client(app):
    c = app.test_client()
    # Inject an admin session (adjust keys if your app uses different names)
    with c.session_transaction() as s:
        s["user_id"] = 1
        s["role"] = "ADMIN"
    return c

@pytest.fixture
def user_client(app):
    c = app.test_client()
    with c.session_transaction() as s:
        s["user_id"] = 2
        s["role"] = "VOLUNTEER"
    return c

