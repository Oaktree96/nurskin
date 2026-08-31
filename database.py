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


class BlockedSlot(Base):
    """Dates/times the practitioner is unavailable (blocked)."""
    __tablename__ = "blocked_slots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    time = Column(String(10), nullable=True)  # HH:MM or null = full day blocked
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    _seed_services()


def _seed_services():
    db = SessionLocal()
    # Always re-seed: delete existing services so new prices apply
    db.query(Service).delete()
    db.commit()

    services = [
        # ── Facial Packages ──
        Service(name="Skin Deep", category="Facial Packages", price=100, duration_minutes=60,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, dermaplan, diamond dermabrasion, EFG mesotherapy cocktail, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="The Carboxytherapy Facial", category="Facial Packages", price=65, duration_minutes=60,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, non-invasive carboxytherapy gel and face mask, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="The Man Up Facial", category="Facial Packages", price=55, duration_minutes=60,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, dermaplan, diamond dermabrasion, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="Teen Facial", category="Facial Packages", price=40, duration_minutes=45,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, gentle blackhead extractions, painless peel, skin toner, ice globes, essence moisturiser, face mask, vitamin oils and SPF."),
        Service(name="Skin Consultation and Analysis", category="Facial Packages", price=20, duration_minutes=30,
            description="Face to face skin consultation tailored to your skin needs and goals. Discussion of the best treatment for your skin type and texture to achieve your skin goals."),
        Service(name="Skin Cleanse", category="Facial Packages", price=50, duration_minutes=45,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="Skin Fresh", category="Facial Packages", price=60, duration_minutes=45,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, dermaplan, diamond dermabrasion, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="Skin Renew", category="Facial Packages", price=75, duration_minutes=60,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, dermaplan, clinicare chemical peel, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),
        Service(name="Skin Glow", category="Facial Packages", price=85, duration_minutes=60,
            description="Pre-cleanse, double cleanse, O-Zone steam, ultrasonic wand, exfoliation, hot towels, blackhead extractions, instant painless peel, skin toner, dermaplan, diamond dermabrasion, EFG microneedling, ice globes, essence moisturiser, EFG face mask, vitamin oils and SPF."),

        # ── Add-Ons ──
        Service(name="LED Light Therapy", category="Add-Ons", price=10, duration_minutes=15,
            description="LED light therapy add-on to enhance your facial treatment."),
        Service(name="Jelly Face Mask", category="Add-Ons", price=10, duration_minutes=15,
            description="Hydrating jelly face mask add-on."),

        # ── Bio Re-Peel ──
        Service(name="Bio Re-Peel (1 treatment)", category="Bio Re-Peel", price=75, duration_minutes=45,
            description="Single Bio Re-Peel treatment."),
        Service(name="Bio Re-Peel (2 treatments)", category="Bio Re-Peel", price=105, duration_minutes=45,
            description="Course of 2 Bio Re-Peel treatments."),
        Service(name="Bio Re-Peel (4 treatments)", category="Bio Re-Peel", price=175, duration_minutes=45,
            description="Course of 4 Bio Re-Peel treatments."),
        Service(name="Bio Re-Peel (6 treatments)", category="Bio Re-Peel", price=235, duration_minutes=45,
            description="Course of 6 Bio Re-Peel treatments."),

        # ── Skin Boosters ──
        Service(name="Seventy Hyal 2000 (1 session)", category="Skin Boosters", price=100, duration_minutes=45,
            description="Single session of Seventy Hyal 2000 skin booster."),
        Service(name="Seventy Hyal 2000 (3 sessions)", category="Skin Boosters", price=250, duration_minutes=45,
            description="Course of 3 Seventy Hyal 2000 skin booster sessions."),
        Service(name="JaluPro", category="Skin Boosters", price=165, duration_minutes=45,
            description="JaluPro skin booster treatment."),
        Service(name="Profhilo (Face)", category="Skin Boosters", price=165, duration_minutes=45,
            description="Profhilo bio-remodelling treatment for the face."),
        Service(name="Profhilo (Body)", category="Skin Boosters", price=200, duration_minutes=45,
            description="Profhilo bio-remodelling treatment for the body."),

        # ── Polynucleotides ──
        Service(name="Vitaran I Under Eyes (1 session)", category="Polynucleotides", price=100, duration_minutes=30,
            description="Single session of Vitaran I polynucleotide treatment for under eyes."),
        Service(name="Vitaran I Under Eyes (2 sessions)", category="Polynucleotides", price=180, duration_minutes=30,
            description="Course of 2 Vitaran I polynucleotide treatments for under eyes."),
        Service(name="Vitaran II Face & Body (1 session)", category="Polynucleotides", price=140, duration_minutes=45,
            description="Single session of Vitaran II polynucleotide treatment for face and body."),
        Service(name="Vitaran II Face & Body (2 sessions)", category="Polynucleotides", price=220, duration_minutes=45,
            description="Course of 2 Vitaran II polynucleotide treatments for face and body."),

        # ── Lumi Eyes ──
        Service(name="Lumi Eyes (1 session)", category="Lumi Eyes", price=100, duration_minutes=30,
            description="Single Lumi Eyes treatment session."),
        Service(name="Lumi Eyes (2 sessions)", category="Lumi Eyes", price=180, duration_minutes=30,
            description="Course of 2 Lumi Eyes treatment sessions."),
        Service(name="Lumi Eyes (3 sessions)", category="Lumi Eyes", price=240, duration_minutes=30,
            description="Course of 3 Lumi Eyes treatment sessions."),

        # ── Aesthetic Treatments ──
        Service(name="Anti-Wrinkle Injections (1 area)", category="Aesthetic Treatments", price=130, duration_minutes=30,
            description="Anti-wrinkle injections for 1 area. Includes free top-up at 2 week review."),
        Service(name="Anti-Wrinkle Injections (2 areas)", category="Aesthetic Treatments", price=160, duration_minutes=30,
            description="Anti-wrinkle injections for 2 areas. Includes free top-up at 2 week review."),
        Service(name="Anti-Wrinkle Injections (3 areas)", category="Aesthetic Treatments", price=190, duration_minutes=30,
            description="Anti-wrinkle injections for 3 areas. Includes free top-up at 2 week review."),
        Service(name="B12 Injections", category="Aesthetic Treatments", price=20, duration_minutes=15,
            description="Vitamin B12 injection."),
    ]

    for s in services:
        db.add(s)
    db.commit()
    db.close()