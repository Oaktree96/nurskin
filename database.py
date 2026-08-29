"""NurSkin Booking System — Database Models"""
import uuid
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///nurskin.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    price = Column(Float, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20), nullable=True)
    client_email = Column(String(100), nullable=True)
    service_id = Column(Integer, nullable=False)
    service_name = Column(String(100), nullable=False)
    service_price = Column(Float, nullable=False, default=0.0)
    booking_date = Column(String(20), nullable=False)
    booking_time = Column(String(10), nullable=False)
    status = Column(String(20), default="pending_payment")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reference = Column(String(12), unique=True, nullable=True)

    # Stripe
    stripe_customer_id = Column(String(100), nullable=True)
    stripe_payment_method_id = Column(String(100), nullable=True)
    stripe_setup_intent_id = Column(String(100), nullable=True)

    # 25% No-show fee tracking
    cancellation_fee_charged = Column(Boolean, default=False)
    cancellation_fee_amount = Column(Float, nullable=True)
    cancellation_charged_at = Column(DateTime, nullable=True)
    no_show_fee_paid = Column(Boolean, default=False)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_services()


def _seed_services():
    db = SessionLocal()
    count = db.query(Service).count()
    if count > 0:
        db.close()
        return

    services = [
        # Facials
        Service(name="Luxury Facial", category="Facials", price=85, duration_minutes=60, description="Deep cleansing, exfoliation, mask, and massage for radiant skin."),
        Service(name="LED Light Therapy Facial", category="Facials", price=95, duration_minutes=60, description="LED light therapy combined with a bespoke facial treatment."),
        Service(name="Chemical Peel", category="Facials", price=110, duration_minutes=45, description="Medical-grade chemical peel for skin resurfacing and renewal."),
        Service(name="Dermaplaning Facial", category="Facials", price=75, duration_minutes=45, description="Gentle exfoliation and peach fuzz removal for smooth, glowing skin."),
        Service(name="Microneedling Facial", category="Facials", price=150, duration_minutes=60, description="Collagen induction therapy for fine lines, scars, and texture."),

        # Injectables
        Service(name="Anti-Wrinkle Treatment", category="Injectables", price=200, duration_minutes=30, description="Botox / anti-wrinkle injections for frown lines, forehead, and crow's feet."),
        Service(name="Lip Filler", category="Injectables", price=180, duration_minutes=45, description="Lip enhancement with hyaluronic acid filler."),
        Service(name="Dermal Fillers (per area)", category="Injectables", price=250, duration_minutes=45, description="Volume restoration for cheeks, nasolabial folds, or jawline."),

        # Skincare
        Service(name="Skin Consultation", category="Skincare", price=40, duration_minutes=45, description="Full skin analysis and personalised treatment plan."),
        Service(name="HydraFacial", category="Facials", price=120, duration_minutes=45, description="Advanced hydradermabrasion facial for instant results."),
    ]

    for s in services:
        db.add(s)
    db.commit()
    db.close()