from sqlalchemy import Column, Integer, String, Float, Boolean, create_engine, ForeignKey, BigInteger, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import QueuePool
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

print(f"Connecting to database: {DATABASE_URL}")

# Configurazione del pool di connessioni
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=300
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
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
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))  # Campo aggiunto

    beat = relationship("Beat", back_populates="orders")
    bundle = relationship("Bundle", back_populates="orders")

class Bundle(Base):
    """Tabella per i bundle di beat promozionali"""
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
    """Tabella di associazione tra bundle e beat"""
    __tablename__ = "bundle_beats"
    
    id = Column(Integer, primary_key=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=False)
    beat_id = Column(Integer, ForeignKey("beats.id"), nullable=False)
    
    # Relazioni
    bundle = relationship("Bundle", back_populates="bundle_beats")
    beat = relationship("Beat", back_populates="bundle_beats")

class BundleOrder(Base):
    """Tabella per gli ordini dei bundle"""
    __tablename__ = "bundle_orders"
    
    id = Column(Integer, primary_key=True)
    bundle_id = Column(Integer, ForeignKey("bundles.id"), nullable=False)
    user_id = Column(BigInteger, nullable=False)  # BigInteger per Telegram IDs
    total_price = Column(Float, nullable=False)
    payment_status = Column(String(50), nullable=False, default="pending")
    transaction_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=True)

def get_session():
    """Restituisce una sessione per interagire con il database"""
    return SessionLocal()

def get_database_stats():
    """Ottiene statistiche del database"""
    try:
        with SessionLocal() as session:
            total_beats = session.query(Beat).count()
            exclusive_beats = session.query(Beat).filter(Beat.is_exclusive == 1).count()
            total_bundles = session.query(Bundle).count()
            active_bundles = session.query(Bundle).filter(Bundle.is_active == 1).count()
            
            # Conteggio beat esclusivi venduti
            sold_exclusive_count = session.query(Order).filter(
                Order.order_type == "beat"
            ).join(Beat).filter(Beat.is_exclusive == 1).count()
            
            return {
                "total_beats": total_beats,
                "exclusive_beats": exclusive_beats,
                "total_bundles": total_bundles,
                "active_bundles": active_bundles,
                "sold_exclusive_count": sold_exclusive_count
            }
    except Exception as e:
        return {"error": str(e)}

def get_exclusive_beats_sold():
    """Ottiene lista dei beat esclusivi venduti"""
    try:
        with SessionLocal() as session:
            sold_beats = session.query(Order).filter(
                Order.order_type == "beat"
            ).join(Beat).filter(Beat.is_exclusive == 1).all()
            
            result = []
            for order in sold_beats:
                result.append({
                    "id": order.beat_id,
                    "title": order.beat_title,
                    "amount": order.amount,
                    "currency": order.currency,
                    "payer_email": order.payer_email,
                    "created_at": order.created_at,
                    "transaction_id": order.transaction_id
                })
            
            return result
    except Exception as e:
        return {"error": str(e)}

def create_beat_from_migration(beat_data):
    """Crea un beat dal processo di migrazione"""
    try:
        with SessionLocal() as session:
            beat = Beat(
                genre=beat_data['genre'],
                mood=beat_data['mood'],
                folder=beat_data['folder'],
                title=beat_data['title'],
                preview_key=beat_data['preview_key'],
                file_key=beat_data['file_key'],
                image_key=beat_data['image_key'],
                price=beat_data['price'],
                original_price=beat_data.get('original_price'),
                is_exclusive=beat_data.get('is_exclusive', 0),
                is_discounted=beat_data.get('is_discounted', 0),
                discount_percent=beat_data.get('discount_percent', 0),
                available=beat_data.get('available', 1),
                reserved_by_user_id=beat_data.get('reserved_by_user_id'),
                reserved_at=beat_data.get('reserved_at'),
                reservation_expires_at=beat_data.get('reservation_expires_at')
            )
            session.add(beat)
            session.commit()
            return True, "Beat creato con successo"
    except Exception as e:
        return False, str(e)

print("Model loaded successfully!")
