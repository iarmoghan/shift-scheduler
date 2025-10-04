import os, sqlite3, csv, io, uuid
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_wtf.csrf import CSRFProtect, generate_csrf

# Use PBKDF2 instead of scrypt (compatibility on some Python builds)
HASH_METHOD = "pbkdf2:sha256"

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "shifts.db"))
SECRET = os.environ.get("SECRET_KEY", "dev_secret_change_me")

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET)

# CSRF protection
csrf = CSRFProtect(app)

@app.context_processor
def inject_csrf_token():
    # lets you call {{ csrf_token() }} in templates
    return dict(csrf_token=generate_csrf)

# ----------- date helpers (NEW) -----------
def parse_iso(s: str):
    """Parse 'YYYY-MM-DDTHH:MM' (from <input type=datetime-local>) or ISO string to datetime."""
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def iso_no_seconds(dt: datetime) -> str:
    """Normalize to ISO string without seconds (or with seconds=00)."""
    return dt.replace(second=0, microsecond=0).isoformat()

def format_range(starts_at: str, ends_at: str) -> str:
    """Pretty time range for UI."""
    try:
        s = datetime.fromisoformat(starts_at)
        e = datetime.fromisoformat(ends_at)
    except Exception:
        return f"{starts_at} – {ends_at}"
    if s.date() == e.date():
        return f"{s.strftime('%b %d, %Y, %I:%M %p')} – {e.strftime('%I:%M %p')}"
    else:
        return f"{s.strftime('%b %d, %Y, %I:%M %p')} – {e.strftime('%b %d, %Y, %I:%M %p')}"

@app.context_processor
def inject_formatters():
    return dict(format_range=format_range)

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
    # schema (includes waitlist for v3)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS app_user (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      email TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL CHECK (role IN ('ADMIN','VOLUNTEER'))
    );

    CREATE TABLE IF NOT EXISTS shift (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      location TEXT,
      starts_at TEXT NOT NULL,
      ends_at   TEXT NOT NULL,
      capacity  INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS signup (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      shift_id INTEGER NOT NULL REFERENCES shift(id) ON DELETE CASCADE,
      user_id  INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE (shift_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS waitlist (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      shift_id INTEGER NOT NULL REFERENCES shift(id) ON DELETE CASCADE,
      user_id  INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE (shift_id, user_id)
    );
    """)
    # seed admin + example shift
    if db.execute("SELECT COUNT(*) c FROM app_user").fetchone()["c"] == 0:
        db.execute(
            "INSERT INTO app_user(email,password_hash,role) VALUES (?,?,?)",
            ("admin@example.com", generate_password_hash("admin123", method=HASH_METHOD), "ADMIN"),
        )
    if db.execute("SELECT COUNT(*) c FROM shift").fetchone()["c"] == 0:
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

def admin_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get("role") != "ADMIN":
            flash("Admin only")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

# ---------- routes: auth ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if not email or not pw:
            flash("Email and password are required")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute(
                "INSERT INTO app_user(email,password_hash,role) VALUES (?,?,?)",
                (email, generate_password_hash(pw, method=HASH_METHOD), "VOLUNTEER"),
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

# ---------- routes: core ----------
@app.get("/")
def index():
    q = request.args.get("q", "").strip()
    sql = """
      SELECT s.*,
             COALESCE((SELECT COUNT(*) FROM signup x WHERE x.shift_id=s.id),0) AS taken,
             COALESCE((SELECT COUNT(*) FROM waitlist w WHERE w.shift_id=s.id),0) AS wait_ct
      FROM shift s
      WHERE datetime(s.ends_at) > datetime('now')
    """
    params = []
    if q:
        sql += " AND (LOWER(s.title) LIKE ? OR LOWER(s.location) LIKE ?)"
        pattern = f"%{q.lower()}%"
        params.extend([pattern, pattern])
    sql += " ORDER BY s.starts_at ASC"
    rows = get_db().execute(sql, params).fetchall()
    return render_template("index.html", shifts=rows, me=current_user(), q=q)

@app.get("/my")
@login_required
def my_shifts():
    items = get_db().execute(
        """
        SELECT s.id as shift_id, s.title, s.starts_at, s.ends_at, su.id AS signup_id
        FROM signup su JOIN shift s ON s.id=su.shift_id
        WHERE su.user_id=?
        ORDER BY s.starts_at ASC
        """,
        (current_user()["id"],),
    ).fetchall()
    return render_template("my.html", items=items)

# ---------- routes: sign up / waitlist / cancel ----------
@app.post("/shifts/<int:shift_id>/signups")
@login_required
def sign_up(shift_id):
    db = get_db()
    me = current_user()
    shift = db.execute("SELECT * FROM shift WHERE id=?", (shift_id,)).fetchone()
    if not shift:
        flash("Shift not found")
        return redirect(url_for("index"))

    taken = db.execute("SELECT COUNT(*) c FROM signup WHERE shift_id=?", (shift_id,)).fetchone()["c"]
    if taken >= shift["capacity"]:
        flash("Shift is full. You can join the waitlist.")
        return redirect(url_for("index"))

    try:
        db.execute("INSERT INTO signup(shift_id,user_id) VALUES (?,?)", (shift_id, me["id"]))
        db.commit()
        flash("Signed up")
    except sqlite3.IntegrityError:
        flash("You are already signed up for this shift (or in waitlist).")
    return redirect(url_for("my_shifts"))

@app.post("/shifts/<int:shift_id>/waitlist")
@login_required
def join_waitlist(shift_id):
    db = get_db()
    me = current_user()
    # already signed up?
    if db.execute("SELECT 1 FROM signup WHERE shift_id=? AND user_id=?", (shift_id, me["id"])).fetchone():
        flash("You are already signed up for this shift.")
        return redirect(url_for("index"))
    try:
        db.execute("INSERT INTO waitlist(shift_id,user_id) VALUES (?,?)", (shift_id, me["id"]))
        db.commit()
        flash("Added to waitlist")
    except sqlite3.IntegrityError:
        flash("You are already on the waitlist.")
    return redirect(url_for("index"))

@app.post("/signups/<int:signup_id>/cancel")
@login_required
def cancel(signup_id):
    db = get_db()
    # find the signup first (need shift_id before delete)
    row = db.execute("SELECT * FROM signup WHERE id=?", (signup_id,)).fetchone()
    if not row:
        flash("Signup not found")
        return redirect(url_for("my_shifts"))
    shift_id = row["shift_id"]
    db.execute("DELETE FROM signup WHERE id=?", (signup_id,))
    db.commit()
    flash("Cancelled")

    # auto-promote first waitlisted user if a spot is free
    shift = db.execute("SELECT * FROM shift WHERE id=?", (shift_id,)).fetchone()
    taken = db.execute("SELECT COUNT(*) c FROM signup WHERE shift_id=?", (shift_id,)).fetchone()["c"]
    if taken < shift["capacity"]:
        w = db.execute(
            "SELECT * FROM waitlist WHERE shift_id=? ORDER BY datetime(created_at) ASC LIMIT 1",
            (shift_id,)
        ).fetchone()
        if w:
            try:
                db.execute("INSERT INTO signup(shift_id,user_id) VALUES (?,?)", (shift_id, w["user_id"]))
                db.execute("DELETE FROM waitlist WHERE id=?", (w["id"],))
                db.commit()
            except sqlite3.IntegrityError:
                pass
    return redirect(url_for("my_shifts"))

# ---------- routes: admin (list/edit/delete/create) ----------
@app.get("/admin/shifts")
@admin_required
def admin_list_shifts():
    rows = get_db().execute(
        """
        SELECT s.*,
               COALESCE((SELECT COUNT(*) FROM signup x WHERE x.shift_id=s.id),0) AS taken,
               COALESCE((SELECT COUNT(*) FROM waitlist w WHERE w.shift_id=s.id),0) AS wait_ct
        FROM shift s
        ORDER BY s.starts_at DESC
        """
    ).fetchall()
    return render_template("admin_shifts.html", shifts=rows)

@app.get("/admin/shifts/new")
@admin_required
def admin_new_shift():
    return render_template("admin_new_shift.html")

@app.post("/admin/shifts")
@admin_required
def admin_create_shift():
    title = request.form["title"].strip()
    location = request.form.get("location", "").strip()
    starts_raw = request.form["starts_at"]
    ends_raw = request.form["ends_at"]
    capacity = max(1, int(request.form.get("capacity", 1)))

    # ---- NEW: validate dates ----
    sdt = parse_iso(starts_raw)
    edt = parse_iso(ends_raw)
    if not title or not sdt or not edt:
        flash("Title, starts and ends are required (invalid date/time).")
        return redirect(url_for("admin_new_shift"))
    if edt <= sdt:
        flash("End time must be AFTER the start time.")
        return redirect(url_for("admin_new_shift"))

    db = get_db()
    db.execute(
        "INSERT INTO shift(title,location,starts_at,ends_at,capacity) VALUES (?,?,?,?,?)",
        (title, location, iso_no_seconds(sdt), iso_no_seconds(edt), capacity),
    )
    db.commit()
    flash("Shift created")
    return redirect(url_for("admin_list_shifts"))

@app.get("/admin/shifts/<int:shift_id>/edit")
@admin_required
def admin_edit_shift(shift_id):
    s = get_db().execute("SELECT * FROM shift WHERE id=?", (shift_id,)).fetchone()
    if not s:
        flash("Shift not found")
        return redirect(url_for("admin_list_shifts"))
    return render_template("admin_edit_shift.html", s=s)

@app.post("/admin/shifts/<int:shift_id>/update")
@admin_required
def admin_update_shift(shift_id):
    title = request.form["title"].strip()
    location = request.form.get("location", "").strip()
    starts_raw = request.form["starts_at"]
    ends_raw = request.form["ends_at"]
    capacity = max(1, int(request.form.get("capacity", 1)))

    # ---- NEW: validate dates ----
    sdt = parse_iso(starts_raw)
    edt = parse_iso(ends_raw)
    if not title or not sdt or not edt:
        flash("Title, starts and ends are required (invalid date/time).")
        return redirect(url_for("admin_edit_shift", shift_id=shift_id))
    if edt <= sdt:
        flash("End time must be AFTER the start time.")
        return redirect(url_for("admin_edit_shift", shift_id=shift_id))

    db = get_db()
    db.execute(
        "UPDATE shift SET title=?, location=?, starts_at=?, ends_at=?, capacity=? WHERE id=?",
        (title, location, iso_no_seconds(sdt), iso_no_seconds(edt), capacity, shift_id),
    )
    db.commit()
    flash("Shift updated")
    return redirect(url_for("admin_list_shifts"))

@app.post("/admin/shifts/<int:shift_id>/delete")
@admin_required
def admin_delete_shift(shift_id):
    db = get_db()
    db.execute("DELETE FROM shift WHERE id=?", (shift_id,))
    db.commit()
    flash("Shift deleted")
    return redirect(url_for("admin_list_shifts"))

# ---------- exports ----------
@app.get("/my.ics")
@login_required
def my_ics():
    """Generate a simple ICS calendar for the user's signups."""
    rows = get_db().execute(
        """
        SELECT s.* FROM signup su
        JOIN shift s ON s.id=su.shift_id
        WHERE su.user_id=?
        ORDER BY s.starts_at ASC
        """,
        (current_user()["id"],),
    ).fetchall()

    def dtfmt(s):
        # ICS requires UTC or local "floating" times; we'll use local "floating"
        try:
            return datetime.fromisoformat(s).strftime("%Y%m%dT%H%M%S")
        except Exception:
            return s

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Shift Scheduler//v3.0//EN"
    ]
    for r in rows:
        uid = f"{uuid.uuid4()}@shifts"
        # Precompute escaped fields (avoid backslashes inside f-string expressions)
        raw_loc = (r["location"] or "")
        loc = raw_loc.replace(",", r"\\,")
        summary = (r["title"] or "").replace(",", r"\\,")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"SUMMARY:{summary}",
            f"DTSTART:{dtfmt(r['starts_at'])}",
            f"DTEND:{dtfmt(r['ends_at'])}",
            f"LOCATION:{loc}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    ics = "\r\n".join(lines) + "\r\n"
    return Response(
        ics,
        mimetype="text/calendar; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=my-shifts.ics"},
    )

@app.get("/admin/signups.csv")
@admin_required
def export_signups_csv():
    db = get_db()
    rows = db.execute(
        """
        SELECT s.title, s.starts_at, s.ends_at, u.email
        FROM signup su
        JOIN shift s ON s.id=su.shift_id
        JOIN app_user u ON u.id=su.user_id
        ORDER BY s.starts_at ASC, u.email ASC
        """
    ).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["shift_title","starts_at","ends_at","user_email"])
    for r in rows:
        writer.writerow([r["title"], r["starts_at"], r["ends_at"], r["email"]])
    data = buf.getvalue()
    return Response(
        data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=signups.csv"},
    )

# ---------- entrypoint ----------
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        open(DB_PATH, "a").close()
    with app.app_context():
        init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
