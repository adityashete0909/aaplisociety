import sqlite3
import os
from werkzeug.security import generate_password_hash
from datetime import datetime

DB_FILE = os.environ.get("DATABASE_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "society.db")

def get_db():
    db_path = os.environ.get("DATABASE_PATH") or DB_FILE
    if os.environ.get("VERCEL"):
        tmp_db = "/tmp/society.db"
        if not os.path.exists(tmp_db):
            local_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "society.db")
            if os.path.exists(local_db):
                try:
                    import shutil
                    shutil.copy2(local_db, tmp_db)
                except Exception:
                    pass
        db_path = tmp_db
    parent_dir = os.path.dirname(os.path.abspath(db_path))
    if parent_dir and not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # 1. Users table (Admins and Society Members)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'member')),
        phone TEXT,
        wing TEXT,
        flat_number TEXT,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'pending', 'inactive')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Society Info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS society_info (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        registration_no TEXT,
        address TEXT,
        contact_phone TEXT,
        contact_email TEXT,
        upi_id TEXT,
        rules_text TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 3. Family Members (Added by Society Member)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS family_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        relation TEXT NOT NULL,
        age INTEGER,
        phone TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 4. Vehicles (Added by Society Member)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('2-Wheeler', '4-Wheeler', 'Other')),
        vehicle_number TEXT NOT NULL,
        parking_slot TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 5. Maintenance Bills (Issued by Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance_bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        billing_month TEXT NOT NULL,
        amount REAL NOT NULL,
        due_date DATE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 6. Payments (Submitted by Member, Verified by Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        payment_method TEXT NOT NULL,
        transaction_ref TEXT NOT NULL,
        payment_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
        admin_remarks TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (bill_id) REFERENCES maintenance_bills(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 7. Complaints (Logged by Member, Resolved by Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL DEFAULT 'Medium' CHECK(priority IN ('Low', 'Medium', 'High', 'Urgent')),
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'in_progress', 'resolved', 'rejected')),
        admin_reply TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 8. Visitors (Pre-approved by Member or Logged by Admin/Security)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS visitors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        visitor_name TEXT NOT NULL,
        visitor_phone TEXT,
        vehicle_number TEXT,
        expected_time TEXT,
        actual_entry TIMESTAMP,
        actual_exit TIMESTAMP,
        purpose TEXT,
        status TEXT NOT NULL DEFAULT 'pre_approved' CHECK(status IN ('pre_approved', 'checked_in', 'checked_out')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # 9. Notices / Announcements (Created by Admin, read by Members)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        category TEXT NOT NULL DEFAULT 'General',
        urgency TEXT NOT NULL DEFAULT 'Normal' CHECK(urgency IN ('Normal', 'Important', 'Urgent')),
        content TEXT NOT NULL,
        posted_by TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 10. Amenity Bookings (Booked by Member, Approved by Admin)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS amenity_bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amenity_name TEXT NOT NULL,
        booking_date DATE NOT NULL,
        time_slot TEXT NOT NULL,
        purpose TEXT,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    conn.commit()

    # Seed initial data if empty
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()

    # Check if society_info exists
    cursor.execute("SELECT COUNT(*) FROM society_info")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO society_info (name, registration_no, address, contact_phone, contact_email, upi_id, rules_text)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "AapliSociety Co-operative Housing Society",
            "REG/MAH/2021/88741",
            "Plot No. 42, Sector 18, Palm Beach Road, Navi Mumbai - 400705",
            "+91 98201 12345",
            "admin@aamlisociety.org",
            "aamlisociety.maintenance@okhdfcbank",
            "1. Quiet hours are from 10:30 PM to 6:30 AM.\n2. All delivery personnel must register at the main gate.\n3. Clubhouse bookings require 48 hours prior notice.\n4. Waste segregation (Dry and Wet) is mandatory.\n5. Visitor parking is strictly for 24 hours max."
        ))

    # Check if admin user exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'admin@society.com'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Society Management Committee",
            "admin@society.com",
            generate_password_hash("admin123"),
            "admin",
            "+91 98200 99999",
            "Clubhouse Office",
            "Admin-01",
            "active"
        ))

    # Check if sample member exists
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'rahul@society.com'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Rahul Sharma",
            "rahul@society.com",
            generate_password_hash("member123"),
            "member",
            "+91 98765 43210",
            "A",
            "402",
            "active"
        ))
        member_id = cursor.lastrowid

        # Seed member's family
        cursor.execute("""
        INSERT INTO family_members (user_id, name, relation, age, phone)
        VALUES 
        (?, 'Pooja Sharma', 'Spouse', 32, '+91 98765 43211'),
        (?, 'Aarav Sharma', 'Son', 7, '')
        """, (member_id, member_id))

        # Seed member's vehicles
        cursor.execute("""
        INSERT INTO vehicles (user_id, vehicle_type, vehicle_number, parking_slot)
        VALUES 
        (?, '4-Wheeler', 'MH-04-AB-1234', 'A-P42'),
        (?, '2-Wheeler', 'MH-04-XY-9876', 'A-2W-15')
        """, (member_id, member_id))

        # Seed member's visitor
        cursor.execute("""
        INSERT INTO visitors (user_id, visitor_name, visitor_phone, vehicle_number, expected_time, purpose, status)
        VALUES (?, 'Amit Verma', '+91 91234 56789', 'MH-01-CZ-3344', 'Today, 6:00 PM', 'Family Dinner', 'pre_approved')
        """, (member_id,))

    # Seed sample member 2
    cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'priya@society.com'")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO users (name, email, password_hash, role, phone, wing, flat_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            "Priya Nair",
            "priya@society.com",
            generate_password_hash("member123"),
            "member",
            "+91 97654 32109",
            "B",
            "201",
            "active"
        ))
        priya_id = cursor.lastrowid

        cursor.execute("""
        INSERT INTO vehicles (user_id, vehicle_type, vehicle_number, parking_slot)
        VALUES (?, '4-Wheeler', 'MH-43-KL-5566', 'B-P12')
        """, (priya_id,))

    # Seed notices
    cursor.execute("SELECT COUNT(*) FROM notices")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO notices (title, category, urgency, content, posted_by)
        VALUES 
        ('Annual General Body Meeting (AGM)', 'Event', 'Urgent', 'The Annual General Body Meeting will be held in the Clubhouse Hall on Sunday at 10:30 AM. Attendance by all primary flat owners is requested.', 'Secretary Office'),
        ('Elevator Maintenance - Wing A', 'Maintenance', 'Important', 'Scheduled lift servicing and safety certification for Wing A passenger elevator will take place on Friday between 1:00 PM and 4:00 PM. Please plan accordingly.', 'Estate Manager'),
        ('Monsoon Preparedness & Terrace Waterproofing', 'General', 'Normal', 'All residents are advised to ensure balcony drainpipes are free from debris. Terrace inspection completed successfully.', 'Maintenance Team')
        """)

    # Seed maintenance bills
    cursor.execute("SELECT COUNT(*) FROM maintenance_bills")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO maintenance_bills (title, billing_month, amount, due_date, description)
        VALUES 
        ('Quarterly Maintenance Q4 (Oct - Dec)', 'October 2026', 4500.0, '2026-11-25', 'Includes standard society charges, water charges, lift maintenance, security, and sinking fund contribution.'),
        ('Quarterly Maintenance Q3 (Jul - Sep)', 'July 2026', 4500.0, '2026-08-25', 'Previous quarter maintenance bill.')
        """)
        q4_bill_id = 1
        q3_bill_id = 2

        # Seed payment for rahul (approved for Q3, pending for Q4)
        cursor.execute("SELECT id FROM users WHERE email = 'rahul@society.com'")
        rahul_row = cursor.fetchone()
        if rahul_row:
            r_id = rahul_row[0]
            cursor.execute("""
            INSERT INTO payments (bill_id, user_id, amount, payment_method, transaction_ref, payment_date, status, admin_remarks)
            VALUES 
            (?, ?, 4500.0, 'UPI', 'UPI/261084920194/HDFC', '2026-08-10', 'approved', 'Payment verified and credited to society account.'),
            (?, ?, 4500.0, 'NEFT / NetBanking', 'NEFT-SBIN260199482', '2026-11-18', 'pending', 'Awaiting bank clearance confirmation.')
            """, (q3_bill_id, r_id, q4_bill_id, r_id))

    # Seed sample complaints
    cursor.execute("SELECT COUNT(*) FROM complaints")
    if cursor.fetchone()[0] == 0:
        cursor.execute("SELECT id FROM users WHERE email = 'rahul@society.com'")
        rahul_row = cursor.fetchone()
        if rahul_row:
            r_id = rahul_row[0]
            cursor.execute("""
            INSERT INTO complaints (user_id, category, priority, subject, description, status, admin_reply)
            VALUES 
            (?, 'Plumbing', 'High', 'Low water pressure on 4th floor', 'Since yesterday morning, water pressure in the master washroom is very weak during peak morning hours.', 'in_progress', 'Plumber assigned. Overhead tank pipeline valve will be checked today by 3 PM.'),
            (?, 'Parking', 'Low', 'Visitor car parked in slot A-P42', 'Unauthorized white sedan was found parked in my reserved slot yesterday evening.', 'resolved', 'Security issued a warning slip to the guest and cleared the parking slot.')
            """, (r_id, r_id))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
