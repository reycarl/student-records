import os
from contextlib import closing

import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret")
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    with closing(get_conn()) as conn, conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
                student_no VARCHAR(20) UNIQUE NOT NULL,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                course VARCHAR(100) NOT NULL,
                year_level INTEGER NOT NULL,
                email VARCHAR(100)
            )
        """)
        conn.commit()


def query(sql, params=(), fetch=True):
    with closing(get_conn()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall() if fetch else None
        conn.commit()
        return rows


def form_data():
    f = request.form
    return (f["student_no"].strip(), f["first_name"].strip(),
            f["last_name"].strip(), f["course"].strip(),
            int(f["year_level"]), f["email"].strip())


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        students = query(
            "SELECT * FROM students WHERE student_no ILIKE %s OR first_name ILIKE %s "
            "OR last_name ILIKE %s OR course ILIKE %s ORDER BY last_name",
            (like, like, like, like))
    else:
        students = query("SELECT * FROM students ORDER BY last_name")
    return render_template("index.html", students=students, q=q)


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        try:
            query("INSERT INTO students (student_no, first_name, last_name, course, "
                  "year_level, email) VALUES (%s,%s,%s,%s,%s,%s)",
                  form_data(), fetch=False)
            flash("Student added.")
            return redirect(url_for("index"))
        except psycopg2.errors.UniqueViolation:
            flash("Student number already exists.")
    return render_template("form.html", student=None)


@app.route("/edit/<int:sid>", methods=["GET", "POST"])
def edit(sid):
    if request.method == "POST":
        query("UPDATE students SET student_no=%s, first_name=%s, last_name=%s, "
              "course=%s, year_level=%s, email=%s WHERE id=%s",
              form_data() + (sid,), fetch=False)
        flash("Student updated.")
        return redirect(url_for("index"))
    rows = query("SELECT * FROM students WHERE id=%s", (sid,))
    if not rows:
        return redirect(url_for("index"))
    return render_template("form.html", student=rows[0])


@app.route("/delete/<int:sid>", methods=["POST"])
def delete(sid):
    query("DELETE FROM students WHERE id=%s", (sid,), fetch=False)
    flash("Student deleted.")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True)
