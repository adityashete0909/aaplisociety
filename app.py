import os
import functools
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, g, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db as create_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "society-mgmt-super-secret-key-2026")

# Ensure DB initialized on startup
with app.app_context():
    init_db()

def get_db():
    if "db" not in g:
        g.db = create_db_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        g.user = user

@app.context_processor
def inject_global_data():
    db = get_db()
    society = db.execute("SELECT * FROM society_info LIMIT 1").fetchone()
    return dict(current_user=g.user, society=society, now=datetime.now())

# Decorators
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("portal_landing"))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for("login_admin"))
        if g.user["role"] != "admin":
            flash("Access denied. Admin portal privilege required.", "danger")
            return redirect(url_for("member_dashboard"))
        return view(**kwargs)
    return wrapped_view

def member_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to your society member portal.", "warning")
            return redirect(url_for("login_member"))
        if g.user["role"] != "member":
            flash("You are logged in as Admin. Redirected to Admin Dashboard.", "info")
            return redirect(url_for("admin_dashboard"))
        if g.user["status"] != "active":
            flash("Your resident account is awaiting committee verification.", "warning")
        return view(**kwargs)
    return wrapped_view

# ----------------- LANDING PAGE -----------------
@app.route("/")
def portal_landing():
    if g.user:
        if g.user["role"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("member_dashboard"))
    
    db = get_db()
    notice_count = db.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
    member_count = db.execute("SELECT COUNT(*) FROM users WHERE role = 'member'").fetchone()[0]
    return render_template("landing.html", notice_count=notice_count, member_count=member_count)

# ----------------- AUTH ROUTES -----------------
@app.route("/login/member", methods=["GET", "POST"])
def login_member():
    if g.user:
        return redirect(url_for("member_dashboard" if g.user["role"] == "member" else "admin_dashboard"))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ? AND role = 'member'", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("member_dashboard"))
        else:
            flash("Invalid email or password for Member Portal.", "danger")

    return render_template("auth/login.html", portal_type="member", portal_title="Society Member Portal")

@app.route("/login/admin", methods=["GET", "POST"])
def login_admin():
    if g.user:
        return redirect(url_for("admin_dashboard" if g.user["role"] == "admin" else "member_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,)).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            flash(f"Welcome to Administration Portal, {user['name']}!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials or unauthorized admin login attempt.", "danger")

    return render_template("auth/login.html", portal_type="admin", portal_title="Management Admin Portal")

@app.route("/register/member", methods=["GET", "POST"])
def register_member():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        wing = request.form.get("wing", "").strip().upper()
        flat_number = request.form.get("flat_number", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password or not flat_number:
            flash("Please fill in all mandatory fields.", "warning")
            return render_template("auth/register.html", portal_type="member")

        if password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template("auth/register.html", portal_type="member")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email address already exists.", "danger")
            return render_template("auth/register.html", portal_type="member")

        db.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
        VALUES (?, ?, ?, 'member', ?, ?, ?, 'active')
        """, (name, email, generate_password_hash(password), phone, wing, flat_number))
        db.commit()

        flash("Member registration successful! You can now log in.", "success")
        return redirect(url_for("login_member"))

    return render_template("auth/register.html", portal_type="member")

@app.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        designation = request.form.get("designation", "").strip()
        secret_code = request.form.get("secret_code", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        # Default society master passkey for security
        if secret_code != "SOCIETY2026":
            flash("Invalid Society Admin Authorization Code. Please check with the managing committee.", "danger")
            return render_template("auth/register.html", portal_type="admin")

        if password != confirm_password:
            flash("Passwords do not match.", "warning")
            return render_template("auth/register.html", portal_type="admin")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", portal_type="admin")

        db.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
        VALUES (?, ?, ?, 'admin', ?, 'Admin Office', ?, 'active')
        """, (name, email, generate_password_hash(password), phone, designation or "Committee Member"))
        db.commit()

        flash("Admin account created successfully! Please log in.", "success")
        return redirect(url_for("login_admin"))

    return render_template("auth/register.html", portal_type="admin")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out successfully.", "info")
    return redirect(url_for("portal_landing"))

# ----------------- MEMBER PORTAL -----------------
@app.route("/member/dashboard")
@member_required
def member_dashboard():
    tab = request.args.get("tab", "overview")
    db = get_db()
    user_id = g.user["id"]

    # 1. Household Data
    family = db.execute("SELECT * FROM family_members WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()
    vehicles = db.execute("SELECT * FROM vehicles WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()

    # 2. Notices
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC LIMIT 10").fetchall()

    # 3. Bills & Payments
    bills = db.execute("SELECT * FROM maintenance_bills ORDER BY id DESC").fetchall()
    payments = db.execute("""
    SELECT p.*, b.title as bill_title, b.billing_month 
    FROM payments p 
    JOIN maintenance_bills b ON p.bill_id = b.id 
    WHERE p.user_id = ? 
    ORDER BY p.id DESC
    """, (user_id,)).fetchall()

    # Compute paid bills set
    approved_bill_ids = set(p["bill_id"] for p in payments if p["status"] == "approved")

    # 4. Complaints
    complaints = db.execute("SELECT * FROM complaints WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()

    # 5. Visitors
    visitors = db.execute("SELECT * FROM visitors WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()

    # 6. Amenity Bookings
    bookings = db.execute("SELECT * FROM amenity_bookings WHERE user_id = ? ORDER BY id DESC", (user_id,)).fetchall()

    return render_template(
        "member/dashboard.html",
        active_tab=tab,
        family=family,
        vehicles=vehicles,
        notices=notices,
        bills=bills,
        payments=payments,
        approved_bill_ids=approved_bill_ids,
        complaints=complaints,
        visitors=visitors,
        bookings=bookings
    )

@app.route("/member/profile/update", methods=["POST"])
@member_required
def member_update_profile():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    wing = request.form.get("wing", "").strip().upper()
    flat_number = request.form.get("flat_number", "").strip()

    if name and flat_number:
        db = get_db()
        db.execute("""
        UPDATE users SET name = ?, phone = ?, wing = ?, flat_number = ? WHERE id = ?
        """, (name, phone, wing, flat_number, g.user["id"]))
        db.commit()
        flash("Profile and flat details updated successfully!", "success")
    else:
        flash("Name and Flat Number are required.", "danger")

    return redirect(url_for("member_dashboard", tab="flat"))

@app.route("/member/family/add", methods=["POST"])
@member_required
def member_add_family():
    name = request.form.get("name", "").strip()
    relation = request.form.get("relation", "").strip()
    age = request.form.get("age", "").strip()
    phone = request.form.get("phone", "").strip()

    if name and relation:
        age_val = int(age) if age and age.isdigit() else None
        db = get_db()
        db.execute("""
        INSERT INTO family_members (user_id, name, relation, age, phone)
        VALUES (?, ?, ?, ?, ?)
        """, (g.user["id"], name, relation, age_val, phone))
        db.commit()
        flash(f"Family member '{name}' added successfully.", "success")
    else:
        flash("Family member name and relation are required.", "danger")

    return redirect(url_for("member_dashboard", tab="flat"))

@app.route("/member/family/delete/<int:fam_id>", methods=["POST"])
@member_required
def member_delete_family(fam_id):
    db = get_db()
    db.execute("DELETE FROM family_members WHERE id = ? AND user_id = ?", (fam_id, g.user["id"]))
    db.commit()
    flash("Family member entry removed.", "info")
    return redirect(url_for("member_dashboard", tab="flat"))

@app.route("/member/vehicles/add", methods=["POST"])
@member_required
def member_add_vehicle():
    vehicle_type = request.form.get("vehicle_type", "4-Wheeler")
    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    parking_slot = request.form.get("parking_slot", "").strip().upper()

    if vehicle_number:
        db = get_db()
        db.execute("""
        INSERT INTO vehicles (user_id, vehicle_type, vehicle_number, parking_slot)
        VALUES (?, ?, ?, ?)
        """, (g.user["id"], vehicle_type, vehicle_number, parking_slot))
        db.commit()
        flash(f"Vehicle '{vehicle_number}' registered successfully.", "success")
    else:
        flash("Vehicle registration number is required.", "danger")

    return redirect(url_for("member_dashboard", tab="flat"))

@app.route("/member/vehicles/delete/<int:veh_id>", methods=["POST"])
@member_required
def member_delete_vehicle(veh_id):
    db = get_db()
    db.execute("DELETE FROM vehicles WHERE id = ? AND user_id = ?", (veh_id, g.user["id"]))
    db.commit()
    flash("Vehicle registration removed.", "info")
    return redirect(url_for("member_dashboard", tab="flat"))

@app.route("/member/payments/submit", methods=["POST"])
@member_required
def member_submit_payment():
    bill_id = request.form.get("bill_id")
    amount = request.form.get("amount")
    payment_method = request.form.get("payment_method", "UPI")
    transaction_ref = request.form.get("transaction_ref", "").strip()
    payment_date = request.form.get("payment_date", datetime.today().strftime('%Y-%m-%d'))

    if bill_id and amount and transaction_ref:
        db = get_db()
        db.execute("""
        INSERT INTO payments (bill_id, user_id, amount, payment_method, transaction_ref, payment_date, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (bill_id, g.user["id"], float(amount), payment_method, transaction_ref, payment_date))
        db.commit()
        flash("Payment proof submitted! The administration will verify and mark as approved.", "success")
    else:
        flash("All payment details and transaction reference are required.", "danger")

    return redirect(url_for("member_dashboard", tab="maintenance"))

@app.route("/member/complaints/add", methods=["POST"])
@member_required
def member_add_complaint():
    category = request.form.get("category", "General")
    priority = request.form.get("priority", "Medium")
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()

    if subject and description:
        db = get_db()
        db.execute("""
        INSERT INTO complaints (user_id, category, priority, subject, description, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """, (g.user["id"], category, priority, subject, description))
        db.commit()
        flash("Complaint ticket submitted. Management committee has been notified.", "success")
    else:
        flash("Subject and description are required.", "danger")

    return redirect(url_for("member_dashboard", tab="complaints"))

@app.route("/member/visitors/add", methods=["POST"])
@member_required
def member_add_visitor():
    visitor_name = request.form.get("visitor_name", "").strip()
    visitor_phone = request.form.get("visitor_phone", "").strip()
    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    expected_time = request.form.get("expected_time", "").strip()
    purpose = request.form.get("purpose", "").strip()

    if visitor_name:
        db = get_db()
        db.execute("""
        INSERT INTO visitors (user_id, visitor_name, visitor_phone, vehicle_number, expected_time, purpose, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pre_approved')
        """, (g.user["id"], visitor_name, visitor_phone, vehicle_number, expected_time, purpose))
        db.commit()
        flash(f"Pre-approved visitor pass generated for '{visitor_name}'.", "success")
    else:
        flash("Visitor name is required.", "danger")

    return redirect(url_for("member_dashboard", tab="visitors"))

@app.route("/member/amenities/book", methods=["POST"])
@member_required
def member_book_amenity():
    amenity_name = request.form.get("amenity_name", "").strip()
    booking_date = request.form.get("booking_date", "").strip()
    time_slot = request.form.get("time_slot", "").strip()
    purpose = request.form.get("purpose", "").strip()

    if amenity_name and booking_date and time_slot:
        db = get_db()
        db.execute("""
        INSERT INTO amenity_bookings (user_id, amenity_name, booking_date, time_slot, purpose, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
        """, (g.user["id"], amenity_name, booking_date, time_slot, purpose))
        db.commit()
        flash("Amenity reservation request submitted for admin approval.", "success")
    else:
        flash("Please complete all reservation fields.", "danger")

    return redirect(url_for("member_dashboard", tab="amenities"))

# Printable Payment Receipt
@app.route("/receipt/<int:payment_id>")
@login_required
def view_receipt(payment_id):
    db = get_db()
    payment = db.execute("""
    SELECT p.*, b.title as bill_title, b.billing_month, u.name as member_name, u.wing, u.flat_number, u.phone as member_phone
    FROM payments p
    JOIN maintenance_bills b ON p.bill_id = b.id
    JOIN users u ON p.user_id = u.id
    WHERE p.id = ?
    """, (payment_id,)).fetchone()

    if not payment:
        abort(404)

    # Permission check: must be admin or the payer
    if g.user["role"] != "admin" and payment["user_id"] != g.user["id"]:
        flash("Unauthorized receipt access.", "danger")
        return redirect(url_for("portal_landing"))

    return render_template("receipt.html", payment=payment)

# ----------------- ADMIN PORTAL -----------------
@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    tab = request.args.get("tab", "overview")
    db = get_db()

    # Overview Metrics
    stats = {}
    stats["total_members"] = db.execute("SELECT COUNT(*) FROM users WHERE role = 'member'").fetchone()[0]
    stats["pending_members"] = db.execute("SELECT COUNT(*) FROM users WHERE role = 'member' AND status = 'pending'").fetchone()[0]
    stats["open_complaints"] = db.execute("SELECT COUNT(*) FROM complaints WHERE status IN ('pending', 'in_progress')").fetchone()[0]
    stats["total_payments"] = db.execute("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'approved'").fetchone()[0]
    stats["pending_payments"] = db.execute("SELECT COUNT(*) FROM payments WHERE status = 'pending'").fetchone()[0]
    stats["active_visitors"] = db.execute("SELECT COUNT(*) FROM visitors WHERE status IN ('pre_approved', 'checked_in')").fetchone()[0]

    # Members list
    members = db.execute("""
    SELECT u.*, 
      (SELECT COUNT(*) FROM family_members WHERE user_id = u.id) as family_count,
      (SELECT COUNT(*) FROM vehicles WHERE user_id = u.id) as vehicle_count
    FROM users u 
    WHERE u.role = 'member' 
    ORDER BY u.wing ASC, u.flat_number ASC
    """).fetchall()

    # Bills & Payments
    bills = db.execute("SELECT * FROM maintenance_bills ORDER BY id DESC").fetchall()
    payments = db.execute("""
    SELECT p.*, b.title as bill_title, b.billing_month, u.name as member_name, u.wing, u.flat_number 
    FROM payments p 
    JOIN maintenance_bills b ON p.bill_id = b.id 
    JOIN users u ON p.user_id = u.id 
    ORDER BY p.id DESC
    """).fetchall()

    # Notices
    notices = db.execute("SELECT * FROM notices ORDER BY id DESC").fetchall()

    # Complaints
    complaints = db.execute("""
    SELECT c.*, u.name as member_name, u.wing, u.flat_number, u.phone as member_phone 
    FROM complaints c 
    JOIN users u ON c.user_id = u.id 
    ORDER BY CASE c.status WHEN 'pending' THEN 1 WHEN 'in_progress' THEN 2 ELSE 3 END, c.id DESC
    """).fetchall()

    # Visitors
    visitors = db.execute("""
    SELECT v.*, u.name as member_name, u.wing, u.flat_number 
    FROM visitors v 
    JOIN users u ON v.user_id = u.id 
    ORDER BY v.id DESC
    """).fetchall()

    # Amenity Bookings
    bookings = db.execute("""
    SELECT a.*, u.name as member_name, u.wing, u.flat_number 
    FROM amenity_bookings a 
    JOIN users u ON a.user_id = u.id 
    ORDER BY a.id DESC
    """).fetchall()

    return render_template(
        "admin/dashboard.html",
        active_tab=tab,
        stats=stats,
        members=members,
        bills=bills,
        payments=payments,
        notices=notices,
        complaints=complaints,
        visitors=visitors,
        bookings=bookings
    )

@app.route("/admin/society/update", methods=["POST"])
@admin_required
def admin_update_society():
    name = request.form.get("name", "").strip()
    registration_no = request.form.get("registration_no", "").strip()
    address = request.form.get("address", "").strip()
    contact_phone = request.form.get("contact_phone", "").strip()
    contact_email = request.form.get("contact_email", "").strip()
    upi_id = request.form.get("upi_id", "").strip()
    rules_text = request.form.get("rules_text", "").strip()

    db = get_db()
    db.execute("""
    UPDATE society_info 
    SET name = ?, registration_no = ?, address = ?, contact_phone = ?, contact_email = ?, upi_id = ?, rules_text = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = 1
    """, (name, registration_no, address, contact_phone, contact_email, upi_id, rules_text))
    db.commit()
    flash("Society profile and configuration saved successfully!", "success")
    return redirect(url_for("admin_dashboard", tab="settings"))

@app.route("/admin/members/status/<int:user_id>", methods=["POST"])
@admin_required
def admin_member_status(user_id):
    status = request.form.get("status", "active")
    db = get_db()
    db.execute("UPDATE users SET status = ? WHERE id = ? AND role = 'member'", (status, user_id))
    db.commit()
    flash(f"Member status changed to '{status}'.", "info")
    return redirect(url_for("admin_dashboard", tab="members"))

@app.route("/admin/members/add", methods=["POST"])
@admin_required
def admin_add_member():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    wing = request.form.get("wing", "").strip().upper()
    flat_number = request.form.get("flat_number", "").strip()
    password = request.form.get("password", "member123")

    if name and email and flat_number:
        db = get_db()
        try:
            db.execute("""
            INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
            VALUES (?, ?, ?, 'member', ?, ?, ?, 'active')
            """, (name, email, generate_password_hash(password), phone, wing, flat_number))
            db.commit()
            flash(f"Resident '{name}' added successfully (Flat: {wing}-{flat_number}).", "success")
        except Exception as e:
            flash(f"Error adding member: {e}", "danger")
    else:
        flash("Name, Email, and Flat Number are mandatory.", "danger")

    return redirect(url_for("admin_dashboard", tab="members"))

@app.route("/admin/bills/create", methods=["POST"])
@admin_required
def admin_create_bill():
    title = request.form.get("title", "").strip()
    billing_month = request.form.get("billing_month", "").strip()
    amount = request.form.get("amount", "0")
    due_date = request.form.get("due_date", "").strip()
    description = request.form.get("description", "").strip()

    if title and billing_month and amount and due_date:
        db = get_db()
        db.execute("""
        INSERT INTO maintenance_bills (title, billing_month, amount, due_date, description)
        VALUES (?, ?, ?, ?, ?)
        """, (title, billing_month, float(amount), due_date, description))
        db.commit()
        flash(f"New maintenance billing cycle '{title}' created for all residents.", "success")
    else:
        flash("Please fill in all bill details.", "danger")

    return redirect(url_for("admin_dashboard", tab="billing"))

@app.route("/admin/payments/review/<int:payment_id>", methods=["POST"])
@admin_required
def admin_review_payment(payment_id):
    status = request.form.get("status", "approved")
    admin_remarks = request.form.get("admin_remarks", "").strip()

    db = get_db()
    db.execute("""
    UPDATE payments SET status = ?, admin_remarks = ? WHERE id = ?
    """, (status, admin_remarks, payment_id))
    db.commit()
    flash(f"Payment reference #{payment_id} marked as '{status}'.", "success")
    return redirect(url_for("admin_dashboard", tab="billing"))

@app.route("/admin/notices/create", methods=["POST"])
@admin_required
def admin_create_notice():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "General")
    urgency = request.form.get("urgency", "Normal")
    content = request.form.get("content", "").strip()
    posted_by = request.form.get("posted_by", g.user["name"]).strip()

    if title and content:
        db = get_db()
        db.execute("""
        INSERT INTO notices (title, category, urgency, content, posted_by)
        VALUES (?, ?, ?, ?, ?)
        """, (title, category, urgency, content, posted_by))
        db.commit()
        flash("Announcement published to society notice board.", "success")
    else:
        flash("Notice title and content are required.", "danger")

    return redirect(url_for("admin_dashboard", tab="notices"))

@app.route("/admin/notices/delete/<int:notice_id>", methods=["POST"])
@admin_required
def admin_delete_notice(notice_id):
    db = get_db()
    db.execute("DELETE FROM notices WHERE id = ?", (notice_id,))
    db.commit()
    flash("Notice removed from notice board.", "info")
    return redirect(url_for("admin_dashboard", tab="notices"))

@app.route("/admin/complaints/update/<int:comp_id>", methods=["POST"])
@admin_required
def admin_update_complaint(comp_id):
    status = request.form.get("status", "in_progress")
    admin_reply = request.form.get("admin_reply", "").strip()

    db = get_db()
    db.execute("""
    UPDATE complaints 
    SET status = ?, admin_reply = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE id = ?
    """, (status, admin_reply, comp_id))
    db.commit()
    flash(f"Complaint #{comp_id} status updated to '{status}'.", "success")
    return redirect(url_for("admin_dashboard", tab="complaints"))

@app.route("/admin/visitors/status/<int:vis_id>", methods=["POST"])
@admin_required
def admin_visitor_status(vis_id):
    new_status = request.form.get("status", "checked_in")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db = get_db()
    if new_status == "checked_in":
        db.execute("UPDATE visitors SET status = ?, actual_entry = ? WHERE id = ?", (new_status, now_str, vis_id))
    elif new_status == "checked_out":
        db.execute("UPDATE visitors SET status = ?, actual_exit = ? WHERE id = ?", (new_status, now_str, vis_id))
    db.commit()
    flash(f"Visitor status updated to '{new_status}'.", "info")
    return redirect(url_for("admin_dashboard", tab="visitors"))

@app.route("/admin/visitors/add", methods=["POST"])
@admin_required
def admin_add_visitor():
    user_id = request.form.get("user_id")
    visitor_name = request.form.get("visitor_name", "").strip()
    visitor_phone = request.form.get("visitor_phone", "").strip()
    vehicle_number = request.form.get("vehicle_number", "").strip().upper()
    purpose = request.form.get("purpose", "").strip()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if user_id and visitor_name:
        db = get_db()
        db.execute("""
        INSERT INTO visitors (user_id, visitor_name, visitor_phone, vehicle_number, expected_time, actual_entry, purpose, status)
        VALUES (?, ?, ?, ?, 'Walk-in', ?, ?, 'checked_in')
        """, (user_id, visitor_name, visitor_phone, vehicle_number, now_str, purpose))
        db.commit()
        flash(f"Gate entry recorded for '{visitor_name}'.", "success")
    else:
        flash("Host flat resident and visitor name are required.", "danger")

    return redirect(url_for("admin_dashboard", tab="visitors"))

@app.route("/admin/amenities/review/<int:booking_id>", methods=["POST"])
@admin_required
def admin_review_amenity(booking_id):
    status = request.form.get("status", "approved")
    db = get_db()
    db.execute("UPDATE amenity_bookings SET status = ? WHERE id = ?", (status, booking_id))
    db.commit()
    flash(f"Amenity booking #{booking_id} marked as '{status}'.", "info")
    return redirect(url_for("admin_dashboard", tab="amenities"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.run(host="0.0.0.0", port=port, debug=debug)
