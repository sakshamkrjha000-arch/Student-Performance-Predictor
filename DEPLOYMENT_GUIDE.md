# Deployment Guide — Student Prediction System

This guide walks you through publishing this Flask app to **Render.com** with a
**managed MySQL database**, the fastest path for a production Flask deployment.

---

## Prerequisites

1. A **GitHub** account.
2. A **Render.com** account (free tier is fine for this app).
3. This project committed and pushed to a GitHub repository.

---

## Step 1 — Push the code to GitHub

```bash
cd student_prediction_system
git init
git add -A
git commit -m "Prepare for deployment (Render + managed MySQL)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/student_prediction_system.git
git push -u origin main
```

*(Replace `YOUR_USERNAME` with your GitHub handle.)*

---

## Step 2 — Create the web service on Render

1. Log in to Render.com → **New +** → **Web Service**.
2. Connect your GitHub repo.
3. Set these options:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1`
   - **Runtime**: `Python 3`
   - **Region**: `Oregon` (or closest to your users)
   - **Instance type**: `Free` (enough for a low-traffic student tool)
4. Add the MySQL database (see Step 3).
5. Click **Create Web Service**.

> **Important**: Your repo must contain `requirements.txt`, `app.py`, and
> `Procfile`. All files from this project are already in place.

---

## Step 3 — Create the managed MySQL database

While the web service is deploying (or after it's created):

1. In your Render dashboard, click **New +** → **Database** → **MySQL**.
2. Pick the same region as your web service.
3. **Name**: `student_prediction_db` (so the app's default DB name matches).
4. Choose **Free** tier if your traffic is low.
5. Click **Create Database**.

Render will show you a password. **Copy it** — you won't see it again.

---

## Step 4 — Add the environment variables

In your web service settings → **Environment** → **Add Environment Variable**:

| Key | Value |
|-----|-------|
| `DB_HOST` | `<your-db-host>.up.railway.app` (or Render's MySQL host) |
| `DB_PORT` | `3306` |
| `DB_USER` | `root` (Render MySQL default) |
| `DB_PASSWORD` | `<the password you copied>` |
| `DB_NAME` | `student_prediction_db` |
| `SECRET_KEY` | A long random string (generate one at <https://generate-secret.key>) |

> Render automatically sets the `PORT` environment variable and injects it into
> the `Procfile` (`--bind 0.0.0.0:$PORT`), so you don't need to set it manually.

---

## Step 5 — Run the database schema

The app needs the MySQL tables before it can log in. In the **Dashboard** for
your MySQL database:

1. Click **Shell** (or open the **Connect** tab).
2. Run:

```sql
SOURCE /path/to/database.sql;
```

*(Upload `database.sql` to Render's file picker, or run the equivalent `CREATE
TABLE ...` statements against the shell manually.)*

You can also seed the default accounts:

```sql
INSERT INTO users (full_name, email, password_hash) VALUES
('Rahul Sharma', 'rahul@student.com', '<use the hash from database.sql>');
-- plus the matching students row
INSERT INTO admins (username, email, password_hash) VALUES
('admin', 'admin@college.edu', '<use the hash from database.sql>');
```

The `database.sql` file in this project already contains these seed hashes.

---

## Step 6 — First login

1. Open your web service URL (e.g. `https://student-prediction-system.onrender.com`).
2. Register a student account, or log in with the seeded accounts:
   - Student — `rahul@student.com` / `student123`
   - Admin — `admin` / `admin123`
3. Submit a prediction to confirm the ML pipeline works.

> **Security note**: Change the admin password immediately after your first
> login. The seed credentials are only for the initial launch.

---

## Step 7 — Remember to set `SECRET_KEY`

Flask uses `SECRET_KEY` to sign session cookies. If you don't set it, the app
falls back to `dev-secret-change-me`, which is fine for a single deploy but
means **all users share the same session signing key**. Generate a random one:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the output as `SECRET_KEY` in Render's environment variables.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'flask'` | Click **Force Run** in Render or check the `requirements.txt` is committed and the Build Command installed all packages. |
| `mysql.connector.Error: 2003 (HY000): Can't connect` | Verify `DB_HOST` and `DB_PASSWORD` are correct. The MySQL database must be in the same region for the free tier to reach it. |
| Empty login form after `SOURCE database.sql` | Make sure the DB name in `DB_NAME` matches the database you connected to. |
| Predictions fail with `model not found` | The `.pkl` files live in `saved_models/`. They're tracked in Git, but if a deployment incorrectly ignores them, run `python ml/train_performance.py` and `python ml/train_placement.py` in the shell. |
| `SECRET_KEY` warning | Generate a new key and add it as `SECRET_KEY` in Render env vars. |

---

## Cost

- **Web service**: Free tier is sufficient for a low-traffic student tool, but Render
  puts it to sleep after inactivity. You'll need a ` starter`/Basic instance for
  always-on.
- **MySQL database**: Free tier allows a few GB of data and low connection counts.
  Fine for a class project.

---

## What was changed to make this work

| File | Change |
|------|--------|
| `requirements.txt` | Added `gunicorn==23.0.0` (production WSGI server) |
| `Procfile` | `web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1` (Render's entry point) |
| `runtime.txt` | `python-3.14` (matches the environment) |
| `app.py` | Runs on `0.0.0.0` with `debug=False`; imports config from `config.py` |
| `.env.example` | Fixed invalid `[TEMPLATE]` section header |
