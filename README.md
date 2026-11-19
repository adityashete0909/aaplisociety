# AapliSociety - Society Management System

🌐 **Live 24/7 Public Link**: **[https://aaplisociety-one.vercel.app](https://aaplisociety-one.vercel.app)**

A full-featured Housing Society Management web application featuring **two distinct portals**:
1. **Society Member Portal**: For flat residents and owners to manage family, vehicles, submit maintenance payments, track complaints, pre-approve visitor gate passes, and book amenities.
2. **Management Admin Portal**: For managing committee members and office bearers to oversee resident directories, issue maintenance bills, review and approve payment receipts, broadcast circulars, resolve complaints, and log gate visitors.

---

## Tech Stack & Architecture

- **Backend**: Python 3 (Flask)
- **Database**: SQLite3 (Local, zero external server requirement, ACID compliant)
- **Frontend**: Responsive Tailwind CSS, FontAwesome 6, Inter/Plus Jakarta Sans typography, and custom glassmorphism styles
- **Security**: Hashed passwords (`werkzeug.security`), role-based session isolation, SQL injection prevention via parameterized queries.

---

## Quick Start Guide

### 1. Requirements
- Python 3.8+ (Tested on Python 3.13)
- `pip install flask` (already configured)

### 2. Run the Application
In your terminal, navigate to this project folder and run:

```powershell
python app.py
```
Or simply double-click `run.bat` in Windows File Explorer.

Then open your browser at:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Pre-seeded Demo Credentials

You can test both roles right out of the box with one-click credential filling:

| Portal | Login URL | Email | Password | Details |
| :--- | :--- | :--- | :--- | :--- |
| **Member Portal** | `/login/member` | `rahul@society.com` | `member123` | Flat A-402 (Has pre-saved family, vehicles & bills) |
| **Admin Portal** | `/login/admin` | `admin@society.com` | `admin123` | Managing Committee Office |

> **Admin Registration Passkey**: `SOCIETY2026` (used if registering a new admin account via `/register/admin`).

---

## Features Breakdown

### 👨‍👩‍👧 Society Member Portal (`/member/dashboard`)
Each member can put, view, and update their own personal data:
- **Profile & Flat Details**: Edit full name, contact phone, and flat number.
- **Family Members**: Add/remove residents living in the flat (Name, Relation, Age, Phone).
- **Vehicles & Parking**: Register 2-wheelers and 4-wheelers with assigned parking slots.
- **Maintenance & Dues**: View active billing cycles, submit payment proofs with UTR/transaction references, and view/print official payment receipts (`/receipt/<id>`).
- **Complaints & Helpdesk**: Submit tickets across categories (Plumbing, Electrical, Elevator, Security, Noise) with priority tags, and view responses from the committee.
- **Visitor Pre-Approvals**: Issue gate passes with expected arrival time and vehicle details.
- **Amenity Bookings**: Reserve society amenities (Clubhouse, Banquet Lawn, Tennis Court, Swimming Pool Gazebo).

### 🛡️ Management Admin Portal (`/admin/dashboard`)
Admins have full oversight and management capabilities:
- **Society Profile Configuration**: Edit society name, registration number, address, committee contacts, UPI ID for maintenance, and society bylaws.
- **Resident Directory**: View all registered flats and occupants, add new residents, activate or deactivate accounts.
- **Billing & Invoicing**: Issue new maintenance billing cycles (Quarterly/Monthly), review member-submitted payments, and approve or reject them.
- **Notice Board Publisher**: Post official circulars and announcements with urgency badges (Normal, Important, Urgent) and categories.
- **Complaints Resolution**: Update complaint tickets (Pending, In Progress, Resolved, Rejected) and write committee resolution notes.
- **Security Gate Register**: Log walk-in visitors and check-in / check-out visitor passes.
- **Amenity Management**: Approve or reject amenity booking requests.

---

## Automated Verification

To run the automated test suite verifying both portals and all CRUD operations:
```powershell
python -m unittest tests/test_system.py
```

---

## ☁️ Cloud Deployment Guide

This project is configured out-of-the-box for deployment on **Render** or **Google Cloud Run**.

### 1. Deploying to Render
1. Push this project to GitHub or GitLab.
2. Log in to [Render](https://render.com) and click **New + > Web Service**.
3. Select your repository.
4. Render will automatically detect the settings from `render.yaml` and `Procfile`:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`
5. *(Optional for Persistence)*: On free-tier instances, disk storage is ephemeral. To persist SQLite between deploys, attach a **Persistent Disk** on Render (e.g. `/var/data`) and set the environment variable:
   - `DATABASE_PATH = /var/data/society.db`
   - `FLASK_SECRET_KEY = your-production-secret-key`

### 2. Deploying to Google Cloud Run
You can deploy using Google Cloud CLI using the included `Dockerfile`:
```bash
# Build and deploy directly to Cloud Run
gcloud run deploy aaplisociety \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FLASK_SECRET_KEY="your-production-secret-key"
```
Cloud Run automatically injects `$PORT` (default `8080`) and routes incoming traffic to the container.

