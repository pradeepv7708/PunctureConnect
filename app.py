import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-key")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "punctureconnect")
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    # Create the database if it does not already exist.
    base = mysql.connector.connect(
        host=DB_CONFIG["host"], user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )
    cur = base.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
    cur.close()
    base.close()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            email VARCHAR(120) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('customer','provider') NOT NULL DEFAULT 'customer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS shops (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            address VARCHAR(255) NOT NULL,
            latitude DECIMAL(10,7) NOT NULL,
            longitude DECIMAL(10,7) NOT NULL,
            price DECIMAL(8,2) NOT NULL,
            rating DECIMAL(2,1) DEFAULT 4.5,
            phone VARCHAR(20) NOT NULL,
            available TINYINT(1) DEFAULT 1,
            description VARCHAR(255)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT NOT NULL,
            shop_id INT NOT NULL,
            customer_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            vehicle_type VARCHAR(40) NOT NULL,
            issue VARCHAR(255),
            latitude DECIMAL(10,7),
            longitude DECIMAL(10,7),
            status ENUM('Pending','Accepted','Rejected','Completed') DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id),
            FOREIGN KEY (shop_id) REFERENCES shops(id)
        )
    """)
    cur.execute("SELECT COUNT(*) FROM shops")
    if cur.fetchone()[0] == 0:
        sample_shops = [
            ("Green Wheel Puncture Works", "Perundurai Road, Erode", 11.3410, 77.7172, 100, 4.8, "9876501001", 1, "Fast bike and scooter puncture repairs"),
            ("City Tyre Care", "Brough Road, Erode", 11.3402, 77.7275, 120, 4.6, "9876501002", 1, "Tube and tubeless tyre support"),
            ("Roadside Moto Help", "Thindal, Erode", 11.2960, 77.6810, 150, 4.5, "9876501003", 1, "Two-wheeler roadside assistance"),
            ("SpeedFix Tyres", "Solar, Erode", 11.3050, 77.7480, 90, 4.3, "9876501004", 0, "Affordable tyre repair service")
        ]
        cur.executemany("""
            INSERT INTO shops (name,address,latitude,longitude,price,rating,phone,available,description)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, sample_shops)
    conn.commit()
    cur.close()
    conn.close()

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please sign in before booking a service.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/shops")
def api_shops():
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id,name,address,latitude,longitude,price,rating,phone,available,description FROM shops ORDER BY rating DESC")
        shops = cur.fetchall()
        cur.close(); conn.close()
        return jsonify(shops)
    except Error:
        # Useful visual fallback while MySQL is being configured.
        return jsonify([
            {"id":1,"name":"Green Wheel Puncture Works","address":"Perundurai Road, Erode","latitude":11.3410,"longitude":77.7172,"price":100,"rating":4.8,"phone":"9876501001","available":1,"description":"Fast bike and scooter puncture repairs"},
            {"id":2,"name":"City Tyre Care","address":"Brough Road, Erode","latitude":11.3402,"longitude":77.7275,"price":120,"rating":4.6,"phone":"9876501002","available":1,"description":"Tube and tubeless tyre support"},
            {"id":3,"name":"Roadside Moto Help","address":"Thindal, Erode","latitude":11.2960,"longitude":77.6810,"price":150,"rating":4.5,"phone":"9876501003","available":1,"description":"Two-wheeler roadside assistance"},
            {"id":4,"name":"SpeedFix Tyres","address":"Solar, Erode","latitude":11.3050,"longitude":77.7480,"price":90,"rating":4.3,"phone":"9876501004","available":0,"description":"Affordable tyre repair service"}
        ])

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        phone = request.form.get("phone","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        role = request.form.get("role","customer")
        if not all([name, phone, email, password]) or len(password) < 6:
            flash("Complete all fields. Password must contain at least 6 characters.", "error")
            return render_template("auth.html", mode="register")
        try:
            conn = get_db(); cur = conn.cursor()
            cur.execute("INSERT INTO users (name,phone,email,password_hash,role) VALUES (%s,%s,%s,%s,%s)",
                        (name,phone,email,generate_password_hash(password),role))
            conn.commit()
            session["user_id"] = cur.lastrowid
            session["user_name"] = name
            session["role"] = role
            cur.close(); conn.close()
            flash("Your account is ready. Find a nearby service!", "success")
            return redirect(url_for("index"))
        except Error as e:
            flash("Could not create account. This email may already be registered, or MySQL is not configured.", "error")
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        try:
            conn = get_db(); cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM users WHERE email=%s", (email,))
            user = cur.fetchone()
            cur.close(); conn.close()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["role"] = user["role"]
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for("index"))
            flash("Email or password is incorrect.", "error")
        except Error:
            flash("MySQL connection failed. Check your database settings.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("index"))

@app.route("/book/<int:shop_id>", methods=["POST"])
@login_required
def book(shop_id):
    customer_name = request.form.get("customer_name", session.get("user_name","")).strip()
    phone = request.form.get("phone","").strip()
    vehicle_type = request.form.get("vehicle_type","Bike")
    issue = request.form.get("issue","").strip()
    lat = request.form.get("latitude") or None
    lng = request.form.get("longitude") or None
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("""
            INSERT INTO bookings (customer_id,shop_id,customer_name,phone,vehicle_type,issue,latitude,longitude)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (session["user_id"],shop_id,customer_name,phone,vehicle_type,issue,lat,lng))
        conn.commit()
        cur.close(); conn.close()
        flash("Booking request sent! The shop can contact you shortly.", "success")
    except Error:
        flash("Booking could not be saved. Please check your MySQL connection and try again.", "error")
    return redirect(url_for("index") + "#find")

@app.route("/my-bookings")
@login_required
def my_bookings():
    try:
        conn = get_db(); cur = conn.cursor(dictionary=True)
        cur.execute("""
            SELECT b.*, s.name AS shop_name, s.address AS shop_address
            FROM bookings b JOIN shops s ON s.id=b.shop_id
            WHERE b.customer_id=%s ORDER BY b.created_at DESC
        """, (session["user_id"],))
        bookings = cur.fetchall()
        cur.close(); conn.close()
    except Error:
        bookings = []
        flash("Could not load bookings. Check MySQL configuration.", "warning")
    return render_template("bookings.html", bookings=bookings)

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name"), "user_role": session.get("role")}

if __name__ == "__main__":
    try:
        init_db()
        print("PunctureConnect database is ready.")
    except Error as e:
        print("MySQL is not ready:", e)
        print("The homepage can still open, but registration and bookings need MySQL.")
    app.run(debug=True)
