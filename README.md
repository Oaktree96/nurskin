# NurSkin — Booking Site

Advanced skin specialist booking system. FastAPI + SQLite + Stripe card guarantee.

## Stack
- FastAPI + Uvicorn
- SQLAlchemy + SQLite
- Stripe (SetupIntent card guarantee → 25% cancellation/no-show fee via PaymentIntent)
- Single-file static frontend (booking, admin with PIN `1337`, gallery upload)

## Run locally
```
uvicorn main:app --port 8081
```
`.env` (not committed): `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` (both live).

## Deploy on Render
Blueprint deploy: New → Blueprint → connect this repo. `render.yaml` defines:
- Web service, `pip install -r requirements.txt` → `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Persistent disk mounted at `/var/data` — `DATABASE_URL` and `IMAGES_DIR` point there
  so bookings and photo uploads survive redeploys
- Stripe keys: set in the Render dashboard env vars (marked `sync: false` in render.yaml)

Custom domain: after the service is live, add it in Render Settings → Custom Domain,
then point the DNS (CNAME) at the `onrender.com` URL.
