import os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

fd, path = tempfile.mkstemp()
os.close(fd)
os.environ["DB_PATH"] = path

import app as appmod  

def test_index_works():
    app = appmod.app
    with app.app_context():
        appmod.init_db()
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Upcoming Shifts" in resp.data
