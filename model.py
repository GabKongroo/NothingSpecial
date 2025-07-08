from sqlalchemy import Column, Integer, String, Float, Boolean, create_engine, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()  # Carica le variabili dal file .env

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
    
    # Campi per prenotazione temporanea beat esclusivi - AGGIORNATI per consistenza
    reserved_by_user_id = Column(BigInteger, nullable=True)  # ID utente che ha prenotato (BigInteger per Telegram IDs)
    reserved_at = Column(DateTime, nullable=True)  # Timestamp prenotazione
    reservation_expires_at = Column(DateTime, nullable=True)  # Scadenza prenotazione
    
    orders = relationship("Order", back_populates="beat")
    bundle_beats = relationship("BundleBeat", back_populates="beat")

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

class Order(Base):
    """Tabella degli ordini"""
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
    
    # Relazioni
    beat = relationship("Beat", back_populates="orders")
    bundle = relationship("Bundle", back_populates="orders")

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
    
    # Relazioni
    # bundle = relationship("Bundle", back_populates="bundle_orders")  # Disabilitato per approccio unificato

# Collegamento al database reale (non tocca nulla)
DATABASE_URL = os.environ.get("DATABASE_URL")

# RIMUOVI connect_args={"check_same_thread": False} per PostgreSQL!
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# NON chiamiamo Base.metadata.create_all() per evitare modifiche strutturali

# === FUNZIONI DI UTILITÀ PER IL DATABASE ===

def get_session():
    """Ritorna una sessione del database"""
    return SessionLocal()

def test_database_connection():
    """Testa la connessione al database"""
    try:
        session = get_session()
        # Test query semplice
        count = session.query(Beat).count()
        session.close()
        return True, count
    except Exception as e:
        return False, str(e)

def get_database_stats():
    """Ritorna statistiche del database"""
    try:
        session = get_session()
        
        # Statistiche di base
        total_beats = session.query(Beat).count()
        total_bundles = session.query(Bundle).count()
        active_bundles = session.query(Bundle).filter(Bundle.is_active == 1).count()
        total_orders = session.query(Order).count()
        
        # Beat esclusivi (totali)
        exclusive_beats = session.query(Beat).filter(Beat.is_exclusive == 1).count()
        
        # Beat esclusivi venduti (con ordini)
        exclusive_beats_sold = session.query(Order).join(Beat).filter(
            Beat.is_exclusive == 1
        ).count()
        
        # Beat per genere
        genres = session.query(Beat.genre).distinct().all()
        genre_counts = {}
        for (genre,) in genres:
            count = session.query(Beat).filter(Beat.genre == genre).count()
            genre_counts[genre] = count
        
        session.close()
        
        return {
            'total_beats': total_beats,
            'exclusive_beats': exclusive_beats,
            'total_bundles': total_bundles,
            'active_bundles': active_bundles,
            'total_orders': total_orders,
            'exclusive_beats_sold': exclusive_beats_sold,
            'genre_counts': genre_counts,
            'sold_exclusive_count': exclusive_beats_sold  # Per compatibilità con template
        }
    except Exception as e:
        return {'error': str(e)}

def get_exclusive_beats_sold():
    """Ritorna la lista dei beat esclusivi venduti"""
    try:
        session = get_session()
        
        # Query per beat esclusivi venduti con dettagli dell'ordine
        exclusive_orders = session.query(Order, Beat).join(Beat).filter(
            Beat.is_exclusive == 1
        ).order_by(Order.created_at.desc()).all()
        
        results = []
        for order, beat in exclusive_orders:
            results.append({
                'beat_title': beat.title,
                'genre': beat.genre,
                'mood': beat.mood,
                'price': order.amount,
                'payer_email': order.payer_email,
                'transaction_id': order.transaction_id,
                'created_at': order.created_at,
                'telegram_user_id': order.telegram_user_id
            })
        
        session.close()
        return results
    except Exception as e:
        return {'error': str(e)}

def create_beat_from_migration(beat_data):
    """Crea un beat nel database dai dati della migrazione"""
    try:
        session = get_session()
        
        # Controlla se il beat esiste già
        existing_beat = session.query(Beat).filter_by(
            genre=beat_data['genre'],
            mood=beat_data['mood'],
            folder=beat_data['folder'],
            title=beat_data['title']
        ).first()
        
        if existing_beat:
            session.close()
            return False, "Beat già esistente"
        
        # Crea nuovo beat
        beat = Beat(
            genre=beat_data['genre'],
            mood=beat_data['mood'],
            folder=beat_data['folder'],
            title=beat_data['title'],
            preview_key=beat_data['preview_key'],
            file_key=beat_data['file_key'],
            image_key=beat_data['image_key'],
            price=beat_data.get('price', 19.99),
            original_price=beat_data.get('original_price', None),
            is_exclusive=beat_data.get('is_exclusive', 0),
            is_discounted=beat_data.get('is_discounted', 0),
            discount_percent=beat_data.get('discount_percent', 0),
            available=beat_data.get('available', 1),
            reserved_by_user_id=beat_data.get('reserved_by_user_id', None),
            reserved_at=beat_data.get('reserved_at', None),
            reservation_expires_at=beat_data.get('reservation_expires_at', None)
        )
        
        session.add(beat)
        session.commit()
        session.close()
        
        return True, "Beat creato con successo"
    except Exception as e:
        if session:
            session.rollback()
            session.close()
        return False, str(e)
