

# Volunteer Shift Scheduler

I built a lightweight volunteer shift scheduler to make sign-ups easy. Admins create shifts with titles, times, locations, and capacity. Volunteers can browse and search upcoming shifts, sign up, cancel, and if a shift is full—join a waitlist that auto-promotes when someone drops out. The app includes a clean Bootstrap UI, secure auth (PBKDF2 + CSRF), and exports: volunteers can download their shifts as an .ics calendar file and admins can export signups as CSV.

[**Project Site (GitHub Pages)**](https://iarmoghan.github.io/shift-scheduler/)

---

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
````

Then I open **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

**Default admin for local dev:** `admin@example.com` / `admin123`
*(I change this in production.)*

---

## Tech stack

* Flask + Jinja templates, SQLite
* Bootstrap 5 (CDN) for the UI
* Password hashing (PBKDF2) and sessions
* CSRF protection (Flask-WTF)
* pytest + GitHub Actions CI
* GitHub Pages for the docs site

---

## Features (by version)

### v3.0 (current)

* Waitlist with **auto-promotion** when someone cancels on a full shift
* **Admin**: list, **edit**, **delete** shifts
* **Exports**: `/my.ics` (calendar), `/admin/signups.csv` (CSV)
* Card-style Home UI + nicer date formatting
* Validation: **End time must be after Start time**

### v2.0

* Bootstrap 5 UI refresh
* Search/Filter on Home (by title/location)
* CSRF protection

### v1.0

* MVP: list upcoming shifts with spots left
* Register / Login / Logout
* Sign up (capacity guard) and Cancel (from **/my**)
* Admin: create shift
* Smoke test + CI + Pages set up

---



## Screenshots I use in my report

Images live in `docs/screenshots/`:

* ![Pages site](docs/screenshots/pages-1)
* ![Pages site](docs/screenshots/pages-2)
* ![Pages site](docs/screenshots/pages-3)

---

## Links

* Repo: [https://github.com/iarmoghan/shift-scheduler](https://github.com/iarmoghan/shift-scheduler)
* Pages: [https://iarmoghan.github.io/shift-scheduler/](https://iarmoghan.github.io/shift-scheduler/)
* Issues: [https://github.com/iarmoghan/shift-scheduler/issues](https://github.com/iarmoghan/shift-scheduler/issues)
* Actions: [https://github.com/iarmoghan/shift-scheduler/actions](https://github.com/iarmoghan/shift-scheduler/actions)
* Releases: [https://github.com/iarmoghan/shift-scheduler/releases](https://github.com/iarmoghan/shift-scheduler/releases)

````

---

### `docs/index.md`
```md
# Volunteer Shift Scheduler

This is my small web app to create volunteer shifts and let volunteers claim or cancel spots.

---

## Quickstart

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
````

Then I open **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

**Admin for local dev:** `admin@example.com` / `admin123`

---

## What’s in v3.0

* Waitlist with **auto-promotion** when a spot frees
* **Admin**: list, edit, delete shifts
* **Exports**: `/my.ics` (calendar), `/admin/signups.csv` (CSV)
* Card-style Home UI + nicer dates
* Validation: End time must be after Start time

*(Previous versions: v2.0 added Bootstrap UI, search/filter, CSRF; v1.0 shipped the MVP + CI + Pages.)*

---

## Links

* Repo: [https://github.com/iarmoghan/shift-scheduler](https://github.com/iarmoghan/shift-scheduler)
* Pages: [https://iarmoghan.github.io/shift-scheduler/](https://iarmoghan.github.io/shift-scheduler/)
* Issues: [https://github.com/iarmoghan/shift-scheduler/issues](https://github.com/iarmoghan/shift-scheduler/issues)
* Actions: [https://github.com/iarmoghan/shift-scheduler/actions](https://github.com/iarmoghan/shift-scheduler/actions)
* Releases: [https://github.com/iarmoghan/shift-scheduler/releases](https://github.com/iarmoghan/shift-scheduler/releases)


