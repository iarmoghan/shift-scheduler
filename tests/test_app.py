import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# temp DB before importing app
fd, path = tempfile.mkstemp()
os.close(fd)
os.environ["DB_PATH"] = path

import app as appmod

def test_index_and_ics():
    app = appmod.app
    with app.app_context():
        appmod.init_db()
    client = app.test_client()

    # Home works
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Upcoming Shifts" in resp.data

    # Fake-login a user via session to access /my.ics
    with client.session_transaction() as sess:
        # create a user and set session
        with app.app_context():
            db = appmod.get_db()
            db.execute(
                "INSERT INTO app_user(email,password_hash,role) VALUES (?,?,?)",
                ("u@test", appmod.generate_password_hash("x", method=appmod.HASH_METHOD), "VOLUNTEER"),
            )
            uid = db.execute("SELECT id FROM app_user WHERE email='u@test'").fetchone()["id"]
            # also create a shift and a signup
            db.execute(
                "INSERT INTO shift(title,location,starts_at,ends_at,capacity) VALUES (?,?,?,?,?)",
                ("Test Shift","Loc","2025-10-10T10:00:00","2025-10-10T12:00:00",2),
            )
            sid = db.execute("SELECT id FROM shift WHERE title='Test Shift'").fetchone()["id"]
            db.execute("INSERT INTO signup(shift_id,user_id) VALUES (?,?)", (sid, uid))
            db.commit()
        sess["uid"] = uid
        sess["role"] = "VOLUNTEER"

    ics = client.get("/my.ics")
    assert ics.status_code == 200
    assert b"BEGIN:VCALENDAR" in ics.data
