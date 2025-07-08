from sqlalchemy import Column, Integer, String, Float, Boolean, create_engine, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
import os

Base = declarative_base()

class Beat(Base):
    __tablename__ = "beats"

    id = Column(Integer, primary_key=True)
    genre = Column(String(50), nullable=False)
    mood = Column(String(50), nullable=False)
    folder = Column(String(50), nullable=False)
    title = Column(String(100), nullable=False)
    preview_key = Column(String(255), nullable=False)
    file_key = Column(String(255), nullable=False)
    image_key = Column(String(255), nullable=False)
    price = Column(Float, nullable=False, default=19.99)
    original_price = Column(Float, nullable=True)
    is_exclusive = Column(Integer, nullable=False, default=0)   # 0 = False, 1 = True
    is_discounted = Column(Integer, nullable=False, default=0)  # 0 = False, 1 = True
    discount_percent = Column(Integer, nullable=False, default=0)
    available = Column(Integer, nullable=False, default=1)      # 0 = False, 1 = True
    
    # Campi per prenotazione temporanea beat esclusivi
    reserved_by_user_id = Column(BigInteger, nullable=True)  # ID utente che ha prenotato (BigInteger per Telegram IDs)
    reserved_at = Column(DateTime, nullable=True)  # Timestamp prenotazione
    reservation_expires_at = Column(DateTime, nullable=True)  # Scadenza prenotazione
    
    orders = relationship("Order", back_populates="beat")
    bundle_beats = relationship("BundleBeat", back_populates="beat")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    transaction_id = Column(String(255), unique=True, nullable=False)
    telegram_user_id = Column(BigInteger, nullable=False)  # BigInteger per Telegram IDs
    beat_title = Column(String(255), nullable=False)
    payer_email = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False)
    token = Column(String(255), nullable=True)
    beat_id = Column(Integer, ForeignKey("beats.id"), nullable=True)  # Chiave esterna opzionale
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=True)  # Supporto per bundle
    order_type = Column(String(20), nullable=False, default="beat")  # "beat" o "bundle"
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    beat = relationship("Beat", back_populates="orders")
    bundle = relationship("Bundle", back_populates="orders")

class Bundle(Base):
    __tablename__ = "bundles"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)  # Nome del bundle
    description = Column(String(500), nullable=True)  # Descrizione del bundle
    individual_price = Column(Float, nullable=False)  # Prezzo totale se comprati singolarmente
    bundle_price = Column(Float, nullable=False)  # Prezzo scontato del bundle
    discount_percent = Column(Integer, nullable=False, default=0)  # Percentuale di sconto
    is_active = Column(Integer, nullable=False, default=1)  # Bundle attivo/disattivo
    created_at = Column(DateTime, nullable=True)
    image_key = Column(String(255), nullable=True)  # Immagine promozionale del bundle
    
    # Relazioni
    bundle_beats = relationship("BundleBeat", back_populates="bundle")
    orders = relationship("Order", back_populates="bundle")

class BundleBeat(Base):
    __tablename__ = "bundle_beats"

    id = Column(Integer, primary_key=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=False)
    beat_id = Column(Integer, ForeignKey("beats.id"), nullable=False)
    
    # Relazioni
    bundle = relationship("Bundle", back_populates="bundle_beats")
    beat = relationship("Beat", back_populates="bundle_beats")

class BundleOrder(Base):
    __tablename__ = "bundle_orders"

    id = Column(Integer, primary_key=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)  # BigInteger per Telegram IDs
    total_price = Column(Float, nullable=False)
    payment_status = Column(String(50), nullable=False, default="pending")
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=True)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Non creare automaticamente l'engine per evitare errori quando DATABASE_URL è None
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
else:
    engine = None
    SessionLocal = None

# NON chiamiamo Base.metadata.create_all() per evitare modifiche strutturali
