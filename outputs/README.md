# Kabadiwala Connect

**SIH26229 — Clean & Green Technology Challenge**  
Bringing the informal collector into the formal recycling chain.

This repository contains a React + Vite frontend and a FastAPI REST service backed by SQLite by default. The app includes real password authentication, role-specific views, persistent pickup and material records, collector verification, in-app notifications, image uploads, price calculation from database rates, and a recycler batch workflow.

## Run locally

Requirements: Node.js 20+, Python 3.11+.

1. Copy `.env.example` to `.env` and change `JWT_SECRET` and the local admin password. The API command below loads `.env`.
2. Start the API in one terminal:

   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   uvicorn main:app --reload --env-file ..\.env
   ```

3. Start the web app in another terminal:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Open http://localhost:5173. API reference is available at http://localhost:8000/docs. SQLite creates `backend/kabadiwala.db` automatically and initializes the waste catalogue plus the local admin from environment variables on first start.

## Local accounts and optional sample data

The admin account is created from `ADMIN_EMAIL` and `ADMIN_PASSWORD` in `.env` (defaults in `.env.example` are for local development only). Public signup supports customer, collector and recycler roles. Collector/recycler accounts need admin verification before accepting pickups or recycler batches.

To add explicitly labeled development demo records, set `DEMO_PASSWORD` to a password of at least 12 characters and run this after starting the API once:

```powershell
cd backend
$env:DEMO_PASSWORD = 'choose-a-local-demo-password'
python seed_demo.py
```

Demo identities: `customer.demo@example.com`, `collector.demo@example.com`, `recycler.demo@example.com`, and `admin.demo@example.com`. All share the `DEMO_PASSWORD` you set. Seed data is never inserted automatically into a production database.

## Main workflow

- Customer: create account → schedule a pickup → optionally add photos and location → follow collector status and value.
- Collector: create account → admin verifies → accept pickup → mark route/arrival → submit actual weight. Final value is the actual weight multiplied by the current database rate, and a traceable batch is created.
- Recycler: create account → admin verifies → accept a listed batch → mark it processing → mark it recycled.
- Admin: sign in with environment credentials → verify collectors/recyclers, review accounts, and change category rates.

In-app notifications are persisted. Payment is recorded as a material valuation; no cash/UPI payment processor or SMS/email delivery is integrated.

## Location and image handling

The browser asks for geolocation permission only after a signed-in customer presses **Use My Current Location**. A successful one-time reading is reverse-geocoded through OpenStreetMap Nominatim; the customer can edit and confirm the resulting address. If access is denied, the address remains manually editable. Latitude/longitude are stored with the pickup and used for approximate Haversine distances when collector coordinates exist. No background or continuous location tracking is performed. Browser geolocation requires localhost or HTTPS. Reverse geocoding requires internet access and follows Nominatim availability and usage terms.

Images are optional. The API accepts up to five JPEG, PNG or WebP images (each at most 5 MB) and stores them under `backend/uploads` for local development. The development server currently serves those uploads through a static route, so anyone with a file URL can access it. Production should use private object storage, signed URLs, malware scanning, retention rules, HTTPS, and a configured CORS allowlist.

## API outline

Authentication: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/users/me`, `PUT /api/users/me`.

Operations: `GET /api/waste-categories`, `POST /api/pickup-requests`, `GET /api/pickup-requests`, `POST /api/pickup-requests/{id}/accept`, `PUT /api/pickup-requests/{id}/status`, `POST /api/pickup-requests/{id}/collection`, `GET /api/materials`, `POST /api/materials/{id}/accept`, `PUT /api/materials/{id}/status`, `GET /api/notifications`, `POST /api/uploads`.

Administration: `GET /api/admin/dashboard`, `GET /api/admin/users`, `PUT /api/admin/users/{id}/verification`, `PUT /api/admin/categories/{id}/price`, and `GET /api/admin/complaints`.

All API paths are role-guarded where appropriate and use bearer JWTs. SQLite is convenient for development; use PostgreSQL for deployment by setting `DATABASE_URL` to a SQLAlchemy PostgreSQL URL. Set a strong secret, restrict CORS, configure TLS, backups, secure media storage, and production secrets before deployment. No hosted production deployment has been performed.

## Current scope

This is a working end-to-end MVP. Payments, email/SMS, map tiles/turn-by-turn directions, account recovery, KYC document capture, collector/recycler detailed business profiles, complaint resolution actions, audit logs, and production-grade media serving are not integrated. They should not be represented as operational until implemented.
