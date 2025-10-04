import os, sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "shifts.db"))
SECRET = os.environ.get("SECRET_KEY", "dev_secret_change_me")

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET)

# ---------- DB helpers ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    # run schema
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r") as f:
        db.executescript(f.read())
    # seed admin + one sample shift if empty
    count = db.execute("SELECT COUNT(*) AS c FROM app_user").fetchone()["c"]
    if count == 0:
        db.execute(
            "INSERT INTO app_user(email,password_hash,role) VALUES (?,?,?)",
            ("admin@example.com", generate_password_hash("admin123"), "ADMIN"),
        )
    if db.execute("SELECT COUNT(*) AS c FROM shift").fetchone()["c"] == 0:
        starts = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        ends = starts + timedelta(hours=3)
        db.execute(
            "INSERT INTO shift(title,location,starts_at,ends_at,capacity) VALUES (?,?,?,?,?)",
            ("Food Bank Morning Shift", "Community Center", starts.isoformat(), ends.isoformat(), 3),
        )
    db.commit()

# ---------- auth utils ----------
def current_user():
    uid = session.get("uid")
    if not uid: return None
    return get_db().execute("SELECT * FROM app_user WHERE id=?", (uid,)).fetchone()

def login_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

# ---------- routes: auth ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        db = get_db()
        try:
            db.execute(
                "INSERT INTO app_user(email,password_hash,role) VALUES (?,?,?)",
                (email, generate_password_hash(pw), "VOLUNTEER"),
            )
            db.commit()
            flash("Registration successful. Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        user = get_db().execute("SELECT * FROM app_user WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], pw):
            session["uid"] = user["id"]
            session["role"] = user["role"]
            return redirect(url_for("index"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------- routes: core pages ----------
@app.get("/")
def index():
    # list future shifts with spots left
    rows = get_db().execute(
        """
        SELECT s.*,
               COALESCE((SELECT COUNT(*) FROM signup x WHERE x.shift_id=s.id),0) AS taken
        FROM shift s
        WHERE datetime(s.ends_at) > datetime('now')
        ORDER BY s.starts_at ASC
        """
    ).fetchall()
    return render_template("index.html", shifts=rows, me=current_user())

@app.get("/my")
@login_required
def my_shifts():
    # will be populated in the next step when we add signups
    items = get_db().execute(
        """
        SELECT s.title, s.starts_at, s.ends_at, su.id AS signup_id
        FROM signup su JOIN shift s ON s.id=su.shift_id
        WHERE su.user_id=?
        ORDER BY su.created_at DESC
        """,
        (current_user()["id"],),
    ).fetchall()
    return render_template("my.html", items=items)

# ---------- entrypoint ----------
if __name__ == "__main__":
    # ensure DB file exists and is initialized
    if not os.path.exists(DB_PATH):
        open(DB_PATH, "a").close()
    with app.app_context():
        init_db()
    app.run(debug=True)
