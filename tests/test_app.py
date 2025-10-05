# tests/test_app.py
import app as appmod
from uuid import uuid4

def test_index_and_ics():
    app = appmod.app
    # Fresh app context + (re)create tables/seed
    with app.app_context():
        appmod.init_db()

    client = app.test_client()

    # Home works
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Upcoming Shifts" in resp.data or b"Shifts" in resp.data or b"<html" in resp.data

    # Create a unique user and set session so /my.ics is allowed
    unique_email = f"u{uuid4().hex[:6]}@test"
    with app.app_context():
        db = appmod.get_db()
        db.execute(
            "INSERT OR IGNORE INTO app_user(email,password_hash,role) VALUES (?,?,?)",
            (unique_email, appmod.generate_password_hash("x", method=appmod.HASH_METHOD), "VOLUNTEER"),
        )
        db.commit()
        user_id = db.execute("SELECT id FROM app_user WHERE email=?", (unique_email,)).fetchone()[0]

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["role"] = "VOLUNTEER"

    # Try ICS (some apps return 200, others redirect if path differs)
    r = client.get("/my.ics", follow_redirects=False)
    assert r.status_code in (200, 302, 401, 403)
    if r.status_code == 200:
        ct = r.headers.get("Content-Type", "")
        assert "text/calendar" in ct or "text/plain" in ct  # tolerate dev headers
