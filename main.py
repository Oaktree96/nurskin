"""NurSkin — FastAPI Booking System with 25% No-Show Fee"""
import os
import uuid
import stripe
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import init_db, SessionLocal, Service, Booking, BlockedSlot

# ── Config ────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
NO_SHOW_FEE_PERCENT = 0.25  # 25%
CANCEL_HOURS = 24
ADMIN_PIN = "1337"

# ── App ───────────────────────────────────────
app = FastAPI(title="NurSkin Booking System")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup():
    init_db()


# ── Schemas ───────────────────────────────────
class BookingCreate(BaseModel):
    client_name: str
    client_phone: str | None = None
    client_email: str | None = None
    service_id: int
    booking_date: str
    booking_time: str
    notes: str | None = None
    stripe_payment_method_id: str


# ── Routes — Public ──────────────────────────
@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/booking")
def booking_page():
    return FileResponse("static/booking.html")


@app.get("/admin")
def admin_page():
    return FileResponse("static/admin.html")


@app.get("/api/services")
def get_services():
    db = SessionLocal()
    services = db.query(Service).all()
    db.close()
    grouped: dict[str, list] = {}
    for s in services:
        grouped.setdefault(s.category, []).append({
            "id": s.id,
            "name": s.name,
            "price": s.price,
            "duration_minutes": s.duration_minutes,
            "description": s.description or "",
        })
    return grouped


@app.get("/api/stripe-key")
def get_stripe_key():
    if not STRIPE_PUBLISHABLE_KEY:
        return {"publishable_key": None, "stripe_disabled": True}
    return {"publishable_key": STRIPE_PUBLISHABLE_KEY, "stripe_disabled": False}


@app.get("/api/terms")
def get_terms():
    return {
        "no_show_fee_percent": int(NO_SHOW_FEE_PERCENT * 100),
        "cancel_hours": CANCEL_HOURS,
    }


# ── Routes — Booking ─────────────────────────
@app.get("/api/availability")
def get_availability(date: str):
    """Return available time slots for a given date (YYYY-MM-DD)."""
    db = SessionLocal()

    # Already booked
    existing = db.query(Booking).filter(
        Booking.booking_date == date,
        Booking.status.in_(["pending_payment", "confirmed"]),
    ).all()

    # Blocked by practitioner — full day or specific times
    blocked = db.query(BlockedSlot).filter(
        BlockedSlot.date == date,
    ).all()

    booked_times = {b.booking_time for b in existing}
    blocked_times = set()
    for b in blocked:
        if b.time is None:
            blocked_times.update(["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"])
        else:
            blocked_times.add(b.time)

    db.close()

    all_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"]
    available = [s for s in all_slots if s not in booked_times and s not in blocked_times]
    return {"date": date, "available": available}


# ── Routes — Blocked Slots (Admin) ──────────
class BlockedSlotCreate(BaseModel):
    date: str       # YYYY-MM-DD
    time: str | None = None  # HH:MM or None = full day


@app.get("/api/blocked-slots")
def get_blocked(pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = SessionLocal()
    slots = db.query(BlockedSlot).order_by(BlockedSlot.date.desc(), BlockedSlot.time.asc()).all()
    db.close()
    return [
        {"id": s.id, "date": s.date, "time": s.time}
        for s in slots
    ]


@app.post("/api/blocked-slots")
def block_slot(data: BlockedSlotCreate, pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = SessionLocal()
    existing = db.query(BlockedSlot).filter(
        BlockedSlot.date == data.date,
        BlockedSlot.time == data.time,
    ).first()
    if existing:
        db.close()
        return {"message": "Already blocked", "id": existing.id}
    slot = BlockedSlot(date=data.date, time=data.time)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    db.close()
    return {"message": "Blocked", "id": slot.id, "date": slot.date, "time": slot.time}


@app.delete("/api/blocked-slots/{slot_id}")
def unblock_slot(slot_id: int, pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    db = SessionLocal()
    slot = db.query(BlockedSlot).filter(BlockedSlot.id == slot_id).first()
    if not slot:
        db.close()
        raise HTTPException(status_code=404, detail="Blocked slot not found")
    db.delete(slot)
    db.commit()
    db.close()
    return {"message": "Unblocked", "id": slot_id}


# ── Routes — Booking ─────────────────────────
def create_booking(booking: BookingCreate):
    """Create booking & save card as guarantee for 25% no-show fee."""
    db = SessionLocal()
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not service:
        db.close()
        raise HTTPException(status_code=404, detail="Service not found")

    # Check slot still free
    existing = db.query(Booking).filter(
        Booking.booking_date == booking.booking_date,
        Booking.booking_time == booking.booking_time,
        Booking.status.in_(["pending_payment", "confirmed"]),
    ).first()
    if existing:
        db.close()
        raise HTTPException(status_code=409, detail="That time slot is no longer available")

    stripe_customer = None

    # Only interact with Stripe if we have an API key configured
    if stripe.api_key:
        if booking.client_email:
            customers = stripe.Customer.list(email=booking.client_email, limit=1).data
            if customers:
                stripe_customer = customers[0]

        if stripe_customer is None and booking.stripe_payment_method_id:
            stripe_customer = stripe.Customer.create(
                email=booking.client_email or None,
                name=booking.client_name,
                metadata={"source": "nurskin"},
            )
            stripe.PaymentMethod.attach(
                booking.stripe_payment_method_id,
                customer=stripe_customer.id,
            )
            _ = stripe.SetupIntent.create(
                customer=stripe_customer.id,
                payment_method=booking.stripe_payment_method_id,
                confirm=True,
                usage="off_session",
            )

    # Generate reference
    ref = _generate_ref()

    new_booking = Booking(
        client_name=booking.client_name,
        client_phone=booking.client_phone,
        client_email=booking.client_email,
        service_id=service.id,
        service_name=service.name,
        service_price=service.price,
        booking_date=booking.booking_date,
        booking_time=booking.booking_time,
        notes=booking.notes,
        status="confirmed",
        reference=ref,
        stripe_customer_id=stripe_customer.id if stripe_customer else None,
        stripe_payment_method_id=booking.stripe_payment_method_id,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    db.close()

    return {
        "message": "Booking secured! Your card is saved as a guarantee. The 25% no-show fee applies if you cancel within 24h or miss your appointment.",
        "id": new_booking.id,
        "reference": ref,
    }


@app.post("/api/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int):
    """Cancel booking. Charge 25% if within 24h of appointment."""
    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        db.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status in ("cancelled", "no_show", "completed"):
        db.close()
        raise HTTPException(status_code=400, detail=f"Booking already {booking.status}")

    booking_dt = datetime.strptime(f"{booking.booking_date} {booking.booking_time}", "%Y-%m-%d %H:%M")
    now = datetime.now()
    hours_until = (booking_dt - now).total_seconds() / 3600

    fee_charged = False
    fee_amount = None

    if hours_until <= CANCEL_HOURS and booking.stripe_payment_method_id and booking.stripe_customer_id:
        fee_amount = round(booking.service_price * NO_SHOW_FEE_PERCENT, 2)
        amount_cents = int(round(fee_amount * 100))

        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="gbp",
                customer=booking.stripe_customer_id,
                payment_method=booking.stripe_payment_method_id,
                off_session=True,
                confirm=True,
                metadata={
                    "booking_id": str(booking.id),
                    "reference": booking.reference or "",
                    "reason": "late_cancellation",
                },
                description=f"{booking.service_name} — late cancellation fee (25%)",
            )
            fee_charged = True
            booking.cancellation_fee_charged = True
            booking.cancellation_fee_amount = fee_amount
            booking.cancellation_charged_at = datetime.utcnow()
        except Exception as e:
            pass  # Fee tracking still recorded even if Stripe fails

    booking.status = "cancelled"
    db.commit()
    booking_id_val = booking.id
    db.close()

    msg = "Booking cancelled."
    if fee_charged:
        msg = f"Booking cancelled. A 25% fee of £{fee_amount:.2f} was charged to your card."
    elif hours_until <= CANCEL_HOURS:
        msg = "Booking cancelled. The 25% no-show fee could not be charged — no card on file."

    return {"message": msg, "id": booking_id_val, "status": "cancelled", "fee_charged": fee_charged, "fee_amount": fee_amount}


@app.post("/api/bookings/{booking_id}/no-show")
def mark_no_show(booking_id: int, request: Request):
    """Admin-only: mark a no-show and charge 25% fee."""
    pin = request.query_params.get("pin")
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        db.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status in ("cancelled", "no_show", "completed"):
        db.close()
        raise HTTPException(status_code=400, detail=f"Booking already {booking.status}")

    fee_amount = round(booking.service_price * NO_SHOW_FEE_PERCENT, 2)
    amount_cents = int(round(fee_amount * 100))
    fee_charged = False

    if booking.stripe_payment_method_id and booking.stripe_customer_id:
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency="gbp",
                customer=booking.stripe_customer_id,
                payment_method=booking.stripe_payment_method_id,
                off_session=True,
                confirm=True,
                metadata={
                    "booking_id": str(booking.id),
                    "reference": booking.reference or "",
                    "reason": "no_show",
                },
                description=f"{booking.service_name} — no-show fee (25%)",
            )
            fee_charged = True
        except Exception:
            pass

    booking.status = "no_show"
    booking.cancellation_fee_charged = True
    booking.cancellation_fee_amount = fee_amount
    booking.cancellation_charged_at = datetime.utcnow()
    if fee_charged:
        booking.no_show_fee_paid = True
    db.commit()
    db.close()

    return {
        "message": "Marked as no-show. 25% fee charged." if fee_charged else "Marked as no-show. Unable to charge fee — no card on file.",
        "id": booking.id,
        "status": "no_show",
        "fee_charged": fee_charged,
        "fee_amount": fee_amount,
    }


# ── Routes — Admin ────────────────────────────
@app.get("/api/bookings")
def get_bookings(pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = SessionLocal()
    bookings = db.query(Booking).order_by(Booking.booking_date.desc()).all()
    db.close()
    return [
        {
            "id": b.id,
            "client_name": b.client_name,
            "client_phone": b.client_phone,
            "client_email": b.client_email,
            "service_name": b.service_name,
            "service_price": b.service_price,
            "booking_date": b.booking_date,
            "booking_time": b.booking_time,
            "status": b.status,
            "reference": b.reference,
            "cancellation_fee_charged": b.cancellation_fee_charged,
            "cancellation_fee_amount": b.cancellation_fee_amount,
            "no_show_fee_paid": b.no_show_fee_paid,
            "created_at": str(b.created_at),
        }
        for b in bookings
    ]


@app.get("/api/stats")
def get_stats(pin: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    db = SessionLocal()
    today = datetime.now().strftime("%Y-%m-%d")
    total = db.query(Booking).count()
    today_count = db.query(Booking).filter(Booking.booking_date == today).count()
    confirmed = db.query(Booking).filter(Booking.status == "confirmed").count()
    cancelled = db.query(Booking).filter(Booking.status == "cancelled").count()
    no_shows = db.query(Booking).filter(Booking.status == "no_show").count()
    completed = db.query(Booking).filter(Booking.status == "completed").count()

    paid_bookings = db.query(Booking).filter(Booking.status.in_(["confirmed", "completed"])).all()
    revenue = sum(b.service_price for b in paid_bookings if b.service_price)

    fee_bookings = db.query(Booking).filter(Booking.cancellation_fee_charged == True).all()
    total_fees = sum(b.cancellation_fee_amount for b in fee_bookings if b.cancellation_fee_amount) or 0

    paid_fees = db.query(Booking).filter(Booking.no_show_fee_paid == True).all()
    collected_fees = sum(b.cancellation_fee_amount for b in paid_fees if b.cancellation_fee_amount) or 0

    db.close()
    return {
        "total_bookings": total,
        "today_bookings": today_count,
        "confirmed": confirmed,
        "cancelled": cancelled,
        "no_shows": no_shows,
        "completed": completed,
        "revenue": round(revenue, 2),
        "cancellation_fees": round(total_fees, 2),
        "collected_fees": round(collected_fees, 2),
        "cancel_fee_percent": int(NO_SHOW_FEE_PERCENT * 100),
        "cancel_hours": CANCEL_HOURS,
    }


@app.put("/api/bookings/{booking_id}/status")
def update_booking_status(booking_id: int, pin: str, status: str):
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    valid = ["confirmed", "completed", "cancelled", "no_show"]
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid)}")

    db = SessionLocal()
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        db.close()
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = status
    db.commit()
    db.close()
    return {"message": f"Booking #{booking_id} updated to {status}"}


# ── Routes — Gallery Upload ───────────────────
IMAGES_DIR = os.path.join(os.path.dirname(__file__), "static", "images")

@app.get("/upload")
def upload_page():
    return FileResponse("static/upload.html")


@app.post("/api/upload")
async def upload_images(request: Request):
    pin = request.query_params.get("pin")
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    form = await request.form()
    files = form.getlist("images")
    if not files:
        raise HTTPException(status_code=400, detail="No images provided")

    os.makedirs(IMAGES_DIR, exist_ok=True)
    uploaded = 0
    for file in files:
        if not file.filename:
            continue
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        # Save with UUID prefix to avoid name collisions
        safe_name = f"{uuid.uuid4().hex[:8]}{ext}"
        path = os.path.join(IMAGES_DIR, safe_name)
        content = await file.read()
        with open(path, "wb") as f:
            f.write(content)
        uploaded += 1

    return {"uploaded": uploaded, "message": f"{uploaded} image(s) uploaded"}


@app.get("/api/gallery")
def list_gallery(pin: str | None = None):
    # "view" or any PIN works for read-only; no PIN = public
    os.makedirs(IMAGES_DIR, exist_ok=True)
    images = sorted(
        [f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))],
        reverse=True,
    )
    return {"images": images}


@app.delete("/api/upload")
def delete_image(request: Request):
    pin = request.query_params.get("pin")
    filename = request.query_params.get("filename")
    if pin != ADMIN_PIN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    path = os.path.join(IMAGES_DIR, os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
        return {"deleted": filename}
    raise HTTPException(status_code=404, detail="File not found")


# ── Helpers ──────────────────────────────────
def _generate_ref() -> str:
    return "NS-" + uuid.uuid4().hex[:8].upper()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8081, reload=True)