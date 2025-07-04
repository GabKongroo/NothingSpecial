from sqlalchemy import Column, Integer, String, Float, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()  # Carica le variabili dal file .env

Base = declarative_base()

class Beat(Base):
    __tablename__ = "beats"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    genre = Column(String(50), nullable=True)
    mood = Column(String(50), nullable=True)
    folder = Column(String(50), nullable=True)
    preview_key = Column(String(255), nullable=True)
    file_key = Column(String(255), nullable=True)
    image_key = Column(String(255), nullable=True)
    price = Column(Float, nullable=False, default=19.99)
    original_price = Column(Float, nullable=True)  # <--- AGGIUNTO
    is_exclusive = Column(Integer, nullable=False, default=0)   # 0 = False, 1 = True
    is_discounted = Column(Integer, nullable=False, default=0)  # 0 = False, 1 = True
    discount_percent = Column(Integer, nullable=False, default=0)

# Collegamento al database reale (non tocca nulla)
DATABASE_URL = os.environ.get("DATABASE_URL")

# RIMUOVI connect_args={"check_same_thread": False} per PostgreSQL!
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# NON chiamiamo Base.metadata.create_all() per evitare modifiche strutturali
