import unittest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
import database

class TestSocietyManagementSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_society.db")
        database.DB_FILE = cls.test_db_path
        if os.path.exists(cls.test_db_path):
            os.remove(cls.test_db_path)
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_db_path):
            try:
                os.remove(cls.test_db_path)
            except Exception:
                pass

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_landing_page(self):
        """Test landing page renders with portal options."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Society Member Portal", response.data)
        self.assertIn(b"Management Admin Portal", response.data)

    def test_02_member_auth_and_dashboard(self):
        """Test member login and dashboard access."""
        # Valid member login
        res = self.client.post("/login/member", data={
            "email": "rahul@society.com",
            "password": "member123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome, Rahul Sharma", res.data)

        # Access member dashboard
        res_dash = self.client.get("/member/dashboard?tab=flat")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"My Profile & Flat Details", res_dash.data)

    def test_03_member_puts_own_data(self):
        """Test member adding personal family, vehicle, complaint, payment, and visitor."""
        # 1. Login
        self.client.post("/login/member", data={
            "email": "rahul@society.com",
            "password": "member123"
        }, follow_redirects=True)

        # 2. Add Family Member
        res_fam = self.client.post("/member/family/add", data={
            "name": "Kavita Sharma",
            "relation": "Mother",
            "age": "60",
            "phone": "+91 98111 22334"
        }, follow_redirects=True)
        self.assertEqual(res_fam.status_code, 200)
        self.assertIn(b"Kavita Sharma", res_fam.data)

        # 3. Add Vehicle
        res_veh = self.client.post("/member/vehicles/add", data={
            "vehicle_type": "2-Wheeler",
            "vehicle_number": "MH-04-ZZ-5555",
            "parking_slot": "A-2W-99"
        }, follow_redirects=True)
        self.assertEqual(res_veh.status_code, 200)
        self.assertIn(b"MH-04-ZZ-5555", res_veh.data)

        # 4. File Complaint
        res_cmp = self.client.post("/member/complaints/add", data={
            "category": "Electrical",
            "priority": "High",
            "subject": "Corridor light flickering outside flat 402",
            "description": "The hallway ceiling bulb has been buzzing and flickering constantly."
        }, follow_redirects=True)
        self.assertEqual(res_cmp.status_code, 200)
        self.assertIn(b"Corridor light flickering", res_cmp.data)

        # 5. Submit Payment Proof
        res_pay = self.client.post("/member/payments/submit", data={
            "bill_id": "1",
            "amount": "4500.0",
            "payment_method": "UPI",
            "transaction_ref": "UPI-TEST-123456",
            "payment_date": "2026-11-19"
        }, follow_redirects=True)
        self.assertEqual(res_pay.status_code, 200)
        self.assertIn(b"UPI-TEST-123456", res_pay.data)

        # 6. Pre-approve Visitor
        res_vis = self.client.post("/member/visitors/add", data={
            "visitor_name": "Vikram Malhotra",
            "visitor_phone": "+91 98989 12121",
            "vehicle_number": "MH-02-AB-9999",
            "expected_time": "Tomorrow 5 PM",
            "purpose": "Friend visit"
        }, follow_redirects=True)
        self.assertEqual(res_vis.status_code, 200)
        self.assertIn(b"Vikram Malhotra", res_vis.data)

    def test_04_admin_auth_and_puts_society_data(self):
        """Test admin login and creating notices, bills, resolving complaints, reviewing payments."""
        # 1. Login as Admin
        res = self.client.post("/login/admin", data={
            "email": "admin@society.com",
            "password": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Society Admin Console", res.data)

        # 2. Admin creates a Notice
        res_not = self.client.post("/admin/notices/create", data={
            "title": "Swimming Pool Deep Cleaning",
            "category": "Maintenance",
            "urgency": "Important",
            "content": "Swimming pool will remain closed on Tuesday for chemical treatment and filtration maintenance.",
            "posted_by": "Estate Manager"
        }, follow_redirects=True)
        self.assertEqual(res_not.status_code, 200)
        self.assertIn(b"Swimming Pool Deep Cleaning", res_not.data)

        # 3. Admin creates a Billing Cycle
        res_bill = self.client.post("/admin/bills/create", data={
            "title": "Q1 Maintenance (Jan - Mar 2027)",
            "billing_month": "January 2027",
            "amount": "4800.00",
            "due_date": "2027-01-20",
            "description": "Revised quarterly charges including festival fund."
        }, follow_redirects=True)
        self.assertEqual(res_bill.status_code, 200)
        self.assertIn(b"Q1 Maintenance (Jan - Mar 2027)", res_bill.data)

        # 4. Admin updates Society Info
        res_soc = self.client.post("/admin/society/update", data={
            "name": "Green Meadows CHS Ltd.",
            "registration_no": "REG/MAH/2021/88741-REV",
            "address": "Plot 42, Sector 18, Navi Mumbai",
            "contact_phone": "+91 98201 99999",
            "contact_email": "helpdesk@greenmeadows.org",
            "upi_id": "society.pay@icici",
            "rules_text": "Updated society bylaws 2026."
        }, follow_redirects=True)
        self.assertEqual(res_soc.status_code, 200)
        self.assertIn(b"Society profile and configuration saved successfully", res_soc.data)

    def test_05_role_security_enforcement(self):
        """Test that regular member cannot access admin routes."""
        # Login as member
        self.client.post("/login/member", data={
            "email": "rahul@society.com",
            "password": "member123"
        }, follow_redirects=True)

        # Try to access admin dashboard
        res = self.client.get("/admin/dashboard", follow_redirects=True)
        self.assertIn(b"Access denied. Admin portal privilege required", res.data)

    def test_06_member_registration(self):
        """Test new resident registration."""
        res = self.client.post("/register/member", data={
            "name": "Ananya Roy",
            "email": "ananya@society.com",
            "phone": "+91 99999 88888",
            "wing": "C",
            "flat_number": "1001",
            "password": "password123",
            "confirm_password": "password123"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Member registration successful", res.data)

    def test_07_admin_registration_with_passkey(self):
        """Test admin registration requires correct secret passkey."""
        # Bad passkey
        res_bad = self.client.post("/register/admin", data={
            "name": "Fake Admin",
            "email": "fake@society.com",
            "phone": "+91 91111 22222",
            "designation": "Staff",
            "secret_code": "WRONG_KEY",
            "password": "adminpassword",
            "confirm_password": "adminpassword"
        }, follow_redirects=True)
        self.assertIn(b"Invalid Society Admin Authorization Code", res_bad.data)

        # Good passkey
        res_good = self.client.post("/register/admin", data={
            "name": "Joint Secretary",
            "email": "jointsec@society.com",
            "phone": "+91 91111 22222",
            "designation": "Joint Secretary",
            "secret_code": "SOCIETY2026",
            "password": "adminpassword",
            "confirm_password": "adminpassword"
        }, follow_redirects=True)
        self.assertEqual(res_good.status_code, 200)
        self.assertIn(b"Admin account created successfully", res_good.data)

    def test_08_amenity_booking_and_receipt(self):
        """Test booking an amenity by member and printable receipt generation."""
        # Login as member
        self.client.post("/login/member", data={
            "email": "rahul@society.com",
            "password": "member123"
        }, follow_redirects=True)

        # Book Clubhouse
        res_book = self.client.post("/member/amenities/book", data={
            "amenity_name": "Clubhouse Community Hall",
            "booking_date": "2026-12-25",
            "time_slot": "Evening (5:00 PM - 10:00 PM)",
            "purpose": "Christmas Community Dinner"
        }, follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)
        self.assertIn(b"Clubhouse Community Hall", res_book.data)

        # View Receipt for Payment #1
        res_rcpt = self.client.get("/receipt/1")
        self.assertEqual(res_rcpt.status_code, 200)
        self.assertIn(b"OFFICIAL RECEIPT", res_rcpt.data.upper())
        self.assertIn(b"Rahul Sharma", res_rcpt.data)

    def test_09_visitor_gate_checkin(self):
        """Test gate visitor check-in by admin."""
        # Login as Admin
        self.client.post("/login/admin", data={
            "email": "admin@society.com",
            "password": "admin123"
        }, follow_redirects=True)

        # Change visitor status
        res = self.client.post("/admin/visitors/status/1", data={
            "status": "checked_in"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Visitor status updated", res.data)

if __name__ == "__main__":
    unittest.main()
