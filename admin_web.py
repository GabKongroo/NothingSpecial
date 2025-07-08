from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from model import SessionLocal, Beat, Bundle, BundleBeat, Order, get_database_stats as get_db_stats, get_exclusive_beats_sold
from sqlalchemy import or_
import os
import sys
import subprocess  # Needed for FFmpeg conversion
from datetime import datetime, timezone
from dotenv import load_dotenv
import boto3
from botocore.config import Config
import uuid
from werkzeug.utils import secure_filename
import logging
import re
import tempfile
import io
from pathlib import Path
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

load_dotenv()  # Carica le variabili dal file .env

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY")

# Configurazione Flash Messages
app.config['SECRET_KEY'] = os.environ.get("ADMIN_SECRET_KEY")

# Health check endpoint per Railway
@app.route("/health")
def health_check():
    """Health check per Railway deployment"""
    return {
        "status": "healthy",
        "service": "admin-web",
        "environment": os.environ.get("ENVIRONMENT", "development")
    }

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# R2 Configuration
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL")

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin_web.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Progress tracking per operazioni lunghe - versione semplificata per Railway
import time
import json

# Storage per il progresso delle operazioni
progress_storage = {}

# --- R2 MANAGER INTEGRATO ---
SERVICE_ACCOUNT_FILE = Path(__file__).parent / 'pegasus.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DRIVE_ROOT_FOLDER_ID = os.environ.get("DRIVE_ROOT_FOLDER_ID")

# Suffissi dei file per R2
SUFFIX_MAP = {
    "_full.wav": "private/beats",
    "_spoiler.wav": "public/previews", 
    "_pic.jpg": "public/images",
    "_pic.jpeg": "public/images"
}

def extract_beat_name(filename):
    """Estrai il nome pulito del beat dal nome del file"""
    patterns = [
        r'^(.*?)_spoiler\.wav$',
        r'^(.*?)_full\.wav$',
        r'^(.*?)_pic\.jpg$',
        r'^(.*?)_pic\.jpeg$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return None

def sanitize_name(name):
    """Rimuove caratteri speciali e normalizza i nomi"""
    name = re.sub(r'[^a-zA-Z0-9\s\-]', '', name).strip()
    return re.sub(r'\s+', ' ', name)

def get_drive_service():
    """Get authenticated Google Drive service"""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def get_r2_client():
    """Get Cloudflare R2 client"""
    return boto3.client(
        's3',
        endpoint_url=R2_ENDPOINT_URL,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
    )

def download_drive_file(service, file_id):
    """Scarica file da Drive e restituisce bytes"""
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read()

def upload_to_r2_direct(s3_client, data, key, content_type):
    """Carica file su Cloudflare R2 direttamente"""
    try:
        acl = 'public-read' if key.startswith('public/') else 'private'
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
            ACL=acl
        )
        return True
    except Exception as e:
        logging.error(f"Errore upload R2 per {key}: {str(e)}")
        return False

def get_content_type_from_filename(filename):
    """Determina il content type in base all'estensione"""
    if filename.endswith('.wav'): return 'audio/wav'
    if filename.endswith('.mp3'): return 'audio/mpeg'
    if filename.endswith('.jpg'): return 'image/jpeg'
    if filename.endswith('.jpeg'): return 'image/jpeg'
    return 'application/octet-stream'

def convert_wav_to_mp3_direct(wav_data):
    """Converte audio WAV in MP3 usando FFmpeg"""
    try:
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
            tmp_wav.write(wav_data)
            tmp_wav_path = tmp_wav.name
        
        tmp_mp3_path = tempfile.mktemp(suffix='.mp3')
        
        cmd = [
            'ffmpeg', '-y', '-i', tmp_wav_path,
            '-codec:a', 'libmp3lame', '-qscale:a', '2', tmp_mp3_path
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logging.error(f"Errore FFmpeg: {result.stderr}")
            return None
        
        with open(tmp_mp3_path, 'rb') as f:
            mp3_data = f.read()
        
        os.unlink(tmp_wav_path)
        os.unlink(tmp_mp3_path)
        
        return mp3_data
    except Exception as e:
        logging.error(f"Errore conversione WAV in MP3: {str(e)}")
        return None

def r2_key_exists_check(s3_client, key):
    """Controlla se una chiave esiste già su R2"""
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=key)
        return True
    except Exception:
        return False

def reset_database_integrated():
    """Reset completo del database integrato"""
    try:
        from model import engine, Base
        
        logging.info("🔄 Eliminazione di tutte le tabelle...")
        Base.metadata.drop_all(engine)
        logging.info("✅ Tabelle eliminate")
        
        logging.info("🔨 Ricreazione schema database...")
        Base.metadata.create_all(engine)
        logging.info("✅ Schema database ricreato")
        
        return True, "Database reset completato con successo"
    except Exception as e:
        error_msg = f"Errore durante il reset del database: {str(e)}"
        logging.error(f"❌ {error_msg}")
        return False, error_msg

def update_progress(operation_id, progress, status, details=None):
    """Aggiorna il progresso di un'operazione - versione semplificata"""
    progress_storage[operation_id] = {
        'progress': progress,
        'status': status,
        'details': details,
        'timestamp': time.time()
    }

def get_progress(operation_id):
    """Ottiene il progresso di un'operazione"""
    return progress_storage.get(operation_id, {
        'progress': 0,
        'status': 'Non trovato',
        'details': None,
        'timestamp': time.time()
    })

# SSE route removed - operations are now synchronous

def run_database_migration_direct(operation_id):
    """Esegue la migrazione database direttamente senza script esterni"""
    try:
        update_progress(operation_id, 0, "Inizializzazione migrazione...")
        
        # Esegui la migrazione integrata
        success, result_message = migrate_to_r2_integrated(operation_id)
        
        if success:
            update_progress(operation_id, 100, "Migrazione completata con successo!", result_message)
            return True, result_message
        else:
            update_progress(operation_id, 100, "Errore durante la migrazione", result_message)
            return False, result_message
            
    except Exception as e:
        error_msg = f"Errore interno durante la migrazione: {str(e)}"
        update_progress(operation_id, 100, "Errore interno", error_msg)
        return False, error_msg



def upload_to_r2(file_content, file_key):
    """Upload file to Cloudflare R2"""
    try:
        # Check if all required environment variables are set
        if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME]):
            print("Error: Missing R2 environment variables")
            print(f"R2_ACCESS_KEY_ID: {'âœ…' if R2_ACCESS_KEY_ID else 'âŒ'}")
            print(f"R2_SECRET_ACCESS_KEY: {'âœ…' if R2_SECRET_ACCESS_KEY else 'âŒ'}")
            print(f"R2_ENDPOINT_URL: {'âœ…' if R2_ENDPOINT_URL else 'âŒ'}")
            print(f"R2_BUCKET_NAME: {'âœ…' if R2_BUCKET_NAME else 'âŒ'}")
            return False
        
        s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if file_key.lower().endswith(('.jpg', '.jpeg')):
            content_type = 'image/jpeg'
        elif file_key.lower().endswith('.png'):
            content_type = 'image/png'
        elif file_key.lower().endswith('.gif'):
            content_type = 'image/gif'
        elif file_key.lower().endswith('.webp'):
            content_type = 'image/webp'
        
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType=content_type
        )
        
        print(f"Successfully uploaded {file_key} to R2")
        return True
    except Exception as e:
        print(f"Error uploading to R2: {e}")
        return False

def delete_from_r2(file_key):
    """Delete file from Cloudflare R2"""
    try:
        # Check if all required environment variables are set
        if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME]):
            print("Error: Missing R2 environment variables for deletion")
            return False
        
        s3_client = boto3.client(
            's3',
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        # Check if file exists before attempting deletion
        try:
            s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=file_key)
            file_exists = True
        except:
            file_exists = False
        
        if file_exists:
            s3_client.delete_object(Bucket=R2_BUCKET_NAME, Key=file_key)
            print(f"Successfully deleted {file_key} from R2")
            return True
        else:
            print(f"File {file_key} not found in R2, skipping deletion")
            return True  # Consider this a success since the file doesn't exist
            
    except Exception as e:
        print(f"Error deleting from R2: {e}")
        return False

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    error_beat_id = None
    if not session.get("logged_in"):
        # Mostra errore solo se non associato a un beat specifico
        return render_template(
            "admin_web.html",
            beats=[],
            error=error if error_beat_id is None else None,
            error_beat_id=error_beat_id
        )

    with SessionLocal() as db:
        if request.method == "POST":
            print("DEBUG FORM DATA:", dict(request.form))  # <--- AGGIUNTO
            form_cache = {}
            for key in request.form:
                # Salta i campi hidden
                if key.startswith("original_price_hidden_"):
                    continue
                if key.startswith("original_price_"):
                    # Solo se la chiave NON contiene 'hidden'
                    suffix = key.replace("original_price_", "")
                    if not suffix.isdigit():
                        continue
                    beat_id = int(suffix)
                    original_price = request.form.get(f"original_price_{beat_id}", type=float)
                    discounted_price = request.form.get(f"discounted_price_{beat_id}", type=float)
                    # Cambiato qui:
                    is_exclusive_list = request.form.getlist(f"is_exclusive_{beat_id}")
                    is_exclusive = int(is_exclusive_list[-1]) if is_exclusive_list else 0

                    is_discounted_list = request.form.getlist(f"is_discounted_{beat_id}")
                    is_discounted = int(is_discounted_list[-1]) if is_discounted_list else 0

                    discount_percent = request.form.get(f"discount_percent_{beat_id}", type=int) or 0

                    beat = db.query(Beat).filter_by(id=beat_id).first()
                    if not beat:
                        continue

                    # Aggiorna il prezzo originale solo se cambia
                    if original_price is not None and (beat.original_price is None or beat.original_price != original_price):
                        beat.original_price = original_price

                    form_cache[beat_id] = {
                        "original_price": original_price,
                        "discounted_price": discounted_price,
                        "is_exclusive": is_exclusive,
                        "is_discounted": is_discounted,
                        "discount_percent": discount_percent,
                    }

                    if (discounted_price is not None and discounted_price != '' and discounted_price > 0) and not is_discounted:
                        error = f"Spunta 'Scontato' per applicare il prezzo scontato al beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if is_discounted and (discounted_price is None or discounted_price <= 0):
                        error = f"Inserisci un prezzo scontato valido (> 0) per il beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if is_discounted and original_price is not None and discounted_price is not None and discounted_price > original_price:
                        error = f"Il prezzo scontato non puÃ² essere maggiore del prezzo originale per il beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if is_discounted and discount_percent < 0:
                        error = f"La percentuale di sconto non puÃ² essere negativa per il beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if is_discounted and discount_percent == 0:
                        try:
                            calc_percent = int(round(100 - (discounted_price / original_price * 100)))
                            if calc_percent <= 0:
                                error = f"Inserisci una percentuale di sconto valida (> 0) per il beat '{beat.title}'!"
                                error_beat_id = beat.id
                                break
                            discount_percent = calc_percent
                        except Exception:
                            error = f"Errore nel calcolo dello sconto per il beat '{beat.title}'!"
                            error_beat_id = beat.id
                            break

                    if discount_percent > 0 and not is_discounted:
                        error = f"Spunta 'Scontato' per applicare lo sconto al beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if not is_discounted and beat.is_discounted:
                        beat.price = beat.original_price
                        beat.is_discounted = 0
                        beat.discount_percent = 0
                        discounted_price = ''
                    elif not is_discounted:
                        # Se non scontato, resetta il prezzo al prezzo originale
                        beat.price = beat.original_price
                        beat.is_discounted = 0
                        beat.discount_percent = 0
                    else:
                        # Se scontato, aggiorna il prezzo con il prezzo scontato
                        beat.price = discounted_price
                        beat.is_discounted = 1
                        beat.discount_percent = discount_percent

                    beat.is_exclusive = is_exclusive
            if not error:
                print("Salvataggio dati:", form_cache)  # DEBUG: mostra cosa viene salvato
                db.commit()

        # Dopo la gestione POST, filtra i beat per ricerca se serve
        query = db.query(Beat).order_by(Beat.id.asc())
        search_q = request.args.get("q", "").strip()
        if search_q:
            query = query.filter(Beat.title.ilike(f"%{search_q}%"))
        beats_db = query.all()

        beats = []
        for b in beats_db:
            if request.method == "POST" and error and b.id in form_cache:
                cached = form_cache[b.id]
                beats.append({
                    "id": b.id,
                    "title": b.title,
                    "genre": b.genre,
                    "mood": b.mood,
                    "price": b.price,
                    "is_exclusive": cached["is_exclusive"],
                    "is_discounted": cached["is_discounted"],
                    "discount_percent": cached["discount_percent"],
                    "original_price": cached["original_price"],
                    "discounted_price": cached["discounted_price"],
                })
            else:
                beats.append({
                    "id": b.id,
                    "title": b.title,
                    "genre": b.genre,
                    "mood": b.mood,
                    "price": b.price,
                    "is_exclusive": b.is_exclusive,
                    "is_discounted": b.is_discounted,
                    "discount_percent": b.discount_percent,
                    "original_price": b.original_price if b.original_price is not None else b.price,
                    "discounted_price": b.price if b.is_discounted else '',
                })

        return render_template(
            "admin_web.html",
            beats=beats,
            error=error if error_beat_id is None else None,
            error_beat_id=error_beat_id
        )


@app.route("/bundles")
def bundles():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    with SessionLocal() as db:
        bundles = db.query(Bundle).order_by(Bundle.created_at.desc()).all()
        bundle_list = []
        
        for bundle in bundles:
            # Recupera i beat del bundle con informazioni complete
            beats = db.query(Beat).join(BundleBeat).filter(
                BundleBeat.bundle_id == bundle.id
            ).all()
            
            # Crea lista beat con informazioni estese
            beats_info = []
            for beat in beats:
                beats_info.append({
                    "id": beat.id,
                    "title": beat.title,
                    "price": beat.price,
                    "original_price": beat.original_price,
                    "is_exclusive": beat.is_exclusive,
                    "is_discounted": beat.is_discounted,
                    "genre": beat.genre,
                    "mood": beat.mood
                })
            
            bundle_list.append({
                "id": bundle.id,
                "name": bundle.name,
                "description": bundle.description,
                "individual_price": bundle.individual_price,
                "bundle_price": bundle.bundle_price,
                "discount_percent": bundle.discount_percent,
                "is_active": bundle.is_active,
                "created_at": bundle.created_at,
                "image_key": bundle.image_key,
                "beats_count": len(beats),
                "beats": beats_info
            })
    
    return render_template("bundles.html", bundles=bundle_list)


@app.route("/api/upload-bundle-image", methods=["POST"])
def upload_bundle_image():
    """API endpoint for uploading bundle images"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    if 'image' not in request.files:
        return jsonify({"success": False, "error": "Nessun file ricevuto"}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nessun file selezionato"}), 400
    
    if not file.content_type.startswith('image/'):
        return jsonify({"success": False, "error": "Il file deve essere un'immagine"}), 400
    
    try:
        # Check if R2 is properly configured
        if not all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME]):
            return jsonify({
                "success": False, 
                "error": "Configurazione R2 mancante. Controlla le variabili d'ambiente."
            }), 500
        
        # Check for previous image to delete (optional parameter)
        previous_image_key = request.form.get('previous_image_key', '').strip()
        if previous_image_key:
            print(f"Deleting previous image: {previous_image_key}")
            if delete_from_r2(previous_image_key):
                print(f"Successfully deleted previous image: {previous_image_key}")
            else:
                print(f"Failed to delete previous image: {previous_image_key}")
        
        # Generate unique filename
        file_extension = secure_filename(file.filename).split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        file_key = f"public/bundle_images/{unique_filename}"
        
        # Upload to R2
        file_content = file.read()
        print(f"Uploading file: {file_key}, size: {len(file_content)} bytes")
        
        if upload_to_r2(file_content, file_key):
            # Generate public URL
            public_url = f"{os.environ.get('R2_PUBLIC_BASE_URL')}/{file_key}"
            
            print(f"Upload successful! Public URL: {public_url}")
            
            return jsonify({
                "success": True,
                "image_key": file_key,
                "image_url": public_url,
                "message": "Immagine caricata con successo"
            })
        else:
            print(f"Upload failed for file: {file_key}")
            return jsonify({"success": False, "error": "Errore durante il caricamento su R2"}), 500
            
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"success": False, "error": f"Errore interno del server: {str(e)}"}), 500

@app.route("/bundles/create", methods=["GET", "POST"])
def create_bundle():
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        bundle_price = request.form.get("bundle_price", type=float)
        image_key = request.form.get("image_key", "").strip()
        beat_ids = request.form.getlist("beat_ids")
        
        if not name or not bundle_price or not beat_ids:
            flash("Nome, prezzo e almeno un beat sono obbligatori!", "error")
            return redirect(url_for("create_bundle"))
        
        try:
            beat_ids = [int(bid) for bid in beat_ids]
        except ValueError:
            flash("ID beat non validi!", "error")
            return redirect(url_for("create_bundle"))
        
        with SessionLocal() as db:
            # Calcola il prezzo individuale totale
            beats = db.query(Beat).filter(Beat.id.in_(beat_ids)).all()
            
            if len(beats) != len(beat_ids):
                flash("Alcuni beat selezionati non esistono!", "error")
                return redirect(url_for("create_bundle"))
            
            individual_price = sum(beat.price for beat in beats)
            discount_percent = int(((individual_price - bundle_price) / individual_price) * 100) if individual_price > 0 else 0
            
            # Crea il bundle
            bundle = Bundle(
                name=name,
                description=description,
                individual_price=individual_price,
                bundle_price=bundle_price,
                discount_percent=discount_percent,
                is_active=1,
                created_at=datetime.now(timezone.utc),
                image_key=image_key if image_key else None
            )
            
            db.add(bundle)
            db.flush()  # Per ottenere l'ID del bundle
            
            # Associa i beat al bundle
            for beat_id in beat_ids:
                bundle_beat = BundleBeat(bundle_id=bundle.id, beat_id=beat_id)
                db.add(bundle_beat)
            
            db.commit()
            
            flash(f"Bundle '{name}' creato con successo!", "success")
            return redirect(url_for("bundles"))
    
    # GET: mostra form di creazione con informazioni estese sui beat
    with SessionLocal() as db:
        beats = db.query(Beat).order_by(Beat.title.asc()).all()
        beats_list = []
        for b in beats:
            beats_list.append({
                "id": b.id, 
                "title": b.title, 
                "genre": b.genre, 
                "mood": b.mood, 
                "price": b.price,
                "original_price": b.original_price,
                "is_exclusive": b.is_exclusive,
                "is_discounted": b.is_discounted,
                "discount_percent": b.discount_percent
            })
    
    return render_template("create_bundle.html", beats=beats_list)


@app.route("/bundles/<int:bundle_id>/edit", methods=["GET", "POST"])
def edit_bundle(bundle_id):
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    with SessionLocal() as db:
        bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
        if not bundle:
            flash("Bundle non trovato!", "error")
            return redirect(url_for("bundles"))
        
        if request.method == "POST":
            bundle.name = request.form.get("name", "").strip()
            bundle.description = request.form.get("description", "").strip()
            bundle.bundle_price = request.form.get("bundle_price", type=float)
            bundle.image_key = request.form.get("image_key", "").strip() or None
            beat_ids = request.form.getlist("beat_ids")
            
            if not bundle.name or not bundle.bundle_price or not beat_ids:
                flash("Nome, prezzo e almeno un beat sono obbligatori!", "error")
                return redirect(url_for("edit_bundle", bundle_id=bundle_id))
            
            try:
                beat_ids = [int(bid) for bid in beat_ids]
            except ValueError:
                flash("ID beat non validi!", "error")
                return redirect(url_for("edit_bundle", bundle_id=bundle_id))
            
            # Calcola nuovo prezzo individuale
            beats = db.query(Beat).filter(Beat.id.in_(beat_ids)).all()
            individual_price = sum(beat.price for beat in beats)
            bundle.individual_price = individual_price
            bundle.discount_percent = int(((individual_price - bundle.bundle_price) / individual_price) * 100) if individual_price > 0 else 0
            
            # Rimuovi associazioni esistenti
            db.query(BundleBeat).filter(BundleBeat.bundle_id == bundle_id).delete()
            
            # Aggiungi nuove associazioni
            for beat_id in beat_ids:
                bundle_beat = BundleBeat(bundle_id=bundle_id, beat_id=beat_id)
                db.add(bundle_beat)
            
            db.commit()
            flash(f"Bundle '{bundle.name}' aggiornato con successo!", "success")
            return redirect(url_for("bundles"))
        
        # GET: mostra form di modifica
        beats = db.query(Beat).all()
        bundle_beats = db.query(BundleBeat).filter(BundleBeat.bundle_id == bundle_id).all()
        selected_beat_ids = [bb.beat_id for bb in bundle_beats]
        
        beats_list = [{"id": b.id, "title": b.title, "genre": b.genre, "mood": b.mood, "price": b.price, "selected": b.id in selected_beat_ids} for b in beats]
        
        bundle_data = {
            "id": bundle.id,
            "name": bundle.name,
            "description": bundle.description,
            "bundle_price": bundle.bundle_price,
            "image_key": bundle.image_key,
            "is_active": bundle.is_active
        }
    
    return render_template("edit_bundle.html", bundle=bundle_data, beats=beats_list)


@app.route("/bundles/<int:bundle_id>/toggle", methods=["POST"])
def toggle_bundle(bundle_id):
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    with SessionLocal() as db:
        bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
        if bundle:
            bundle.is_active = 1 - bundle.is_active  # Toggle 0/1
            db.commit()
            status = "attivato" if bundle.is_active else "disattivato"
            flash(f"Bundle '{bundle.name}' {status}!", "success")
        else:
            flash("Bundle non trovato!", "error")
    
    return redirect(url_for("bundles"))


@app.route("/bundles/<int:bundle_id>/delete", methods=["POST"])
def delete_bundle(bundle_id):
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    with SessionLocal() as db:
        bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
        if bundle:
            try:
                bundle_name = bundle.name  # Salva il nome prima di eliminare
                bundle_image_key = bundle.image_key  # Salva la chiave dell'immagine
                
                # 1. Elimina gli ordini che referenziano questo bundle
                orders_to_delete = db.query(Order).filter(Order.bundle_id == bundle_id).all()
                for order in orders_to_delete:
                    db.delete(order)
                
                # 2. Elimina le associazioni bundle-beat
                db.query(BundleBeat).filter(BundleBeat.bundle_id == bundle_id).delete()
                
                # 3. Elimina il bundle stesso
                db.delete(bundle)
                
                # 4. Commit tutte le modifiche al database
                db.commit()
                
                # 5. Elimina l'immagine da R2 (se presente)
                if bundle_image_key:
                    print(f"Attempting to delete image: {bundle_image_key}")
                    if delete_from_r2(bundle_image_key):
                        print(f"Successfully deleted image {bundle_image_key} from R2")
                    else:
                        print(f"Failed to delete image {bundle_image_key} from R2")
                        # Non falliamo l'operazione se l'immagine non puÃ² essere cancellata
                        # Il bundle Ã¨ giÃ  stato eliminato dal database
                
                flash(f"Bundle '{bundle_name}' e tutti i suoi ordini associati eliminati con successo!", "success")
                
            except Exception as e:
                db.rollback()
                print(f"Error during bundle deletion: {str(e)}")
                flash(f"Errore durante l'eliminazione del bundle: {str(e)}", "error")
        else:
            flash("Bundle non trovato!", "error")
    
    return redirect(url_for("bundles"))


@app.route("/api/save-all-beats", methods=["POST"])
def save_all_beats_api():
    """API endpoint per salvare tutti i beat modificati dal frontend"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    try:
        data = request.get_json()
        print(f"DEBUG: Dati ricevuti: {data}")  # Debug
        
        if not data or 'beats' not in data:
            return jsonify({"success": False, "error": "Dati non validi"}), 400
        
        beats_data = data['beats']
        updated_count = 0
        errors = []
        
        print(f"DEBUG: Processando {len(beats_data)} beat")  # Debug
        
        with SessionLocal() as db:
            for beat_data in beats_data:
                try:
                    beat_id = beat_data.get('id')
                    if not beat_id:
                        continue
                    
                    beat = db.query(Beat).filter(Beat.id == beat_id).first()
                    if not beat:
                        errors.append(f"Beat ID {beat_id} non trovato")
                        continue

                    # Aggiorna i valori del beat
                    original_price = beat_data.get('original_price')
                    discounted_price = beat_data.get('discounted_price')
                    is_exclusive = beat_data.get('is_exclusive', 0)
                    is_discounted = beat_data.get('is_discounted', 0)
                    discount_percent = beat_data.get('discount_percent', 0)
                    
                    # Validazione
                    if is_discounted and (not discounted_price or discounted_price <= 0):
                        errors.append(f"Prezzo scontato non valido per il beat '{beat.title}'")
                        continue
                    
                    if is_discounted and original_price and discounted_price > original_price:
                        errors.append(f"Prezzo scontato maggiore del prezzo originale per il beat '{beat.title}'")
                        continue
                    
                    # Aggiorna il beat
                    if original_price is not None:
                        beat.original_price = original_price
                    
                    beat.is_exclusive = is_exclusive
                    beat.is_discounted = is_discounted
                    beat.discount_percent = discount_percent
                    
                    if is_discounted and discounted_price:
                        beat.price = discounted_price
                    elif original_price:
                        beat.price = original_price
                    
                    updated_count += 1
                    
                except Exception as e:
                    errors.append(f"Errore nell'aggiornamento del beat ID {beat_data.get('id', 'sconosciuto')}: {str(e)}")
                    continue
            
            if errors:
                db.rollback()
                return jsonify({
                    "success": False, 
                    "error": "Errori durante l'aggiornamento", 
                    "details": errors
                }), 400
            
            db.commit()
            print(f"DEBUG: Aggiornati {updated_count} beat con successo")  # Debug
            return jsonify({
                "success": True, 
                "message": f"{updated_count} beat aggiornati con successo",
                "updated_count": updated_count
            })
            
    except Exception as e:
        print(f"DEBUG: Errore generale: {str(e)}")  # Debug
        return jsonify({"success": False, "error": f"Errore interno: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
def login():
    password = request.form.get("password")
    if password == ADMIN_PASSWORD:
        session["logged_in"] = True
        return redirect(url_for("index"))
    return render_template("admin_web.html", beats=[], error="Password errata")

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))

@app.route("/api/r2-status", methods=["GET"])
def r2_status():
    """Check R2 configuration status"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    all_configured = all([R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT_URL, R2_BUCKET_NAME, R2_PUBLIC_BASE_URL])
    
    return jsonify({
        "all_configured": all_configured,
        "variables": {
            "R2_ACCESS_KEY_ID": bool(R2_ACCESS_KEY_ID),
            "R2_SECRET_ACCESS_KEY": bool(R2_SECRET_ACCESS_KEY),
            "R2_ENDPOINT_URL": bool(R2_ENDPOINT_URL),
            "R2_BUCKET_NAME": bool(R2_BUCKET_NAME),
            "R2_PUBLIC_BASE_URL": bool(R2_PUBLIC_BASE_URL)
        }
    })

@app.route("/admin/database", methods=["GET"])
def database_admin():
    """Pagina di amministrazione database"""
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    try:
        # Ottieni statistiche usando le funzioni integrate
        stats = get_db_stats()
        
        # Ottieni i beat esclusivi venduti
        sold_exclusive_beats = get_exclusive_beats_sold()
        
        # Se c'è un errore nelle statistiche, usa valori di default
        if 'error' in stats:
            logging.error(f"Errore nel recupero delle statistiche: {stats['error']}")
            stats = {
                "total_beats": 0,
                "exclusive_beats": 0,
                "total_bundles": 0,
                "active_bundles": 0,
                "sold_exclusive_count": 0
            }
        
        if 'error' in sold_exclusive_beats:
            logging.error(f"Errore nel recupero dei beat venduti: {sold_exclusive_beats['error']}")
            sold_exclusive_beats = []
        
        return render_template("database_admin.html", stats=stats, sold_beats=sold_exclusive_beats)
    except Exception as e:
        logging.error(f"Errore nella dashboard database: {str(e)}")
        flash(f"Errore nel caricamento della dashboard: {str(e)}", "error")
        return redirect(url_for("index"))

@app.route("/admin/database-stats", methods=["GET"])
def get_database_stats():
    """Endpoint per ottenere le statistiche del database in tempo reale"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    try:
        # Ottieni statistiche aggiornate
        stats = get_db_stats()
        
        if 'error' in stats:
            return jsonify({
                "total_beats": 0,
                "exclusive_beats": 0,
                "total_bundles": 0,
                "active_bundles": 0,
                "sold_exclusive_count": 0
            })
        
        return jsonify(stats)
    except Exception as e:
        logging.error(f"Errore nel recupero delle statistiche: {str(e)}")
        return jsonify({
            "total_beats": 0,
            "exclusive_beats": 0,
            "total_bundles": 0,
            "active_bundles": 0,
            "sold_exclusive_count": 0
        })

@app.route("/admin/update-database", methods=["POST"])
def update_database():
    """Avvia l'aggiornamento database da Google Drive - versione sincrona per Railway"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    try:
        # Genera un ID unico per questa operazione
        import uuid
        operation_id = str(uuid.uuid4())
        
        # Esegui la migrazione direttamente (sincrona)
        success, result_message = run_database_migration_direct(operation_id)
        
        if success:
            return jsonify({
                "success": True,
                "operation_id": operation_id,
                "message": "Aggiornamento completato con successo!",
                "details": result_message
            })
        else:
            return jsonify({
                "success": False,
                "operation_id": operation_id,
                "error": "Errore durante l'aggiornamento",
                "details": result_message
            }), 500
            
    except Exception as e:
        error_msg = f"Errore interno: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

@app.route("/admin/reset-database", methods=["POST"])
def reset_database():
    """Reset database integrato - senza script esterni"""
    if not session.get("logged_in"):
        return jsonify({"success": False, "error": "Non autorizzato"}), 401
    
    try:
        # Esegui il reset direttamente
        success, message = reset_database_integrated()
        
        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({
                "success": False,
                "error": message
            }), 500
            
    except Exception as e:
        error_msg = f"Errore interno: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500

def migrate_to_r2_integrated(operation_id):
    """Migrazione completa da Google Drive a R2 e popolamento DB integrata"""
    try:
        update_progress(operation_id, 5, "Inizializzazione servizi...")
        
        # Test connessione database
        from model import get_session, create_beat_from_migration
        session = get_session()
        
        # Inizializza servizi
        update_progress(operation_id, 10, "Connessione a Google Drive...")
        drive_service = get_drive_service()
        
        update_progress(operation_id, 15, "Connessione a Cloudflare R2...")
        r2_client = get_r2_client()
        
        # Test connessione R2
        try:
            r2_client.head_bucket(Bucket=R2_BUCKET_NAME)
            logging.info("✅ Connessione a Cloudflare R2 riuscita")
        except Exception as e:
            raise Exception(f"Errore connessione Cloudflare R2: {str(e)}")
        
        processed_count = 0
        skipped_count = 0
        
        update_progress(operation_id, 20, "Scansione generi musicali...")
        
        # Elenca tutti i generi
        genres = drive_service.files().list(
            q=f"'{DRIVE_ROOT_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)",
            pageSize=1000
        ).execute().get('files', [])
        
        total_genres = len(genres)
        logging.info(f"📊 Trovati {total_genres} generi")
        
        for genre_idx, genre in enumerate(genres):
            genre_name = genre['name']
            sanitized_genre = sanitize_name(genre_name).lower().replace(' ', '_')
            
            progress_base = 20 + (genre_idx / total_genres) * 60  # 20-80% per i generi
            update_progress(operation_id, int(progress_base), f"Elaborazione genere: {genre_name}")
            logging.info(f"🎵 Elaborazione genere: {genre_name}")
            
            # Elenca mood per questo genere
            moods = drive_service.files().list(
                q=f"'{genre['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)",
                pageSize=1000
            ).execute().get('files', [])
            
            for mood in moods:
                mood_name = mood['name']
                sanitized_mood = sanitize_name(mood_name).lower().replace(' ', '_')
                
                # Elenca beat folders per questo mood
                beat_folders = drive_service.files().list(
                    q=f"'{mood['id']}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    fields="files(id, name)",
                    pageSize=1000
                ).execute().get('files', [])
                
                beat_folders = sorted(beat_folders, key=lambda x: x['name'].strip().lower())
                
                for beat_folder in beat_folders:
                    beat_folder_name = beat_folder['name']
                    sanitized_folder = sanitize_name(beat_folder_name).lower().replace(' ', '_')
                    
                    # Elenca file nella cartella beat
                    files = drive_service.files().list(
                        q=f"'{beat_folder['id']}' in parents and trashed=false",
                        fields="files(id, name)",
                        pageSize=10
                    ).execute().get('files', [])
                    
                    # Trova nome beat
                    beat_name = None
                    for file in files:
                        potential_name = extract_beat_name(file['name'])
                        if potential_name:
                            beat_name = sanitize_name(potential_name)
                            break

                    if not beat_name:
                        logging.warning(f"⚠️ Nessun nome beat valido trovato in {beat_folder_name}")
                        skipped_count += 1
                        continue

                    # Controlla se il beat esiste già
                    existing_beat = session.query(Beat).filter_by(
                        genre=genre_name,
                        mood=mood_name,
                        folder=beat_folder_name,
                        title=beat_name
                    ).first()
                    if existing_beat:
                        logging.info(f"⏭️ Beat già presente nel database: {beat_name}")
                        skipped_count += 1
                        continue

                    # ID unico per il beat
                    beat_id = f"{sanitized_genre}_{sanitized_mood}_{sanitized_folder}"
                    readable_beat_name = beat_name.lower().replace(' ', '_').replace("'", "")
                    beat_id = f"{beat_id}_{readable_beat_name}"
                    
                    logging.info(f"🎵 Processando beat: {beat_name} (ID: {beat_id})")
                    
                    # Inizializza chiavi R2
                    preview_key = None
                    file_key = None
                    image_key = None
                    valid_beat = True
                    
                    # Processa tutti i file del beat
                    for file in files:
                        file_name = file['name']
                        
                        # Trova suffisso corrispondente
                        matched_suffix = None
                        for suffix in SUFFIX_MAP:
                            if file_name.lower().endswith(suffix.lower()):
                                matched_suffix = suffix
                                break
                        
                        if not matched_suffix:
                            continue
                        
                        # Verifica corrispondenza nome
                        if not re.match(f"^{re.escape(beat_name)}{matched_suffix}$", file_name, re.IGNORECASE):
                            logging.warning(f"⚠️ Nome file non corrisponde: {file_name}")
                            valid_beat = False
                            continue
                        
                        # Genera chiave R2
                        target_dir = SUFFIX_MAP[matched_suffix]
                        r2_key = f"{target_dir}/{beat_name}{matched_suffix}"

                        # Controlla se esiste già su R2
                        if r2_key_exists_check(r2_client, r2_key):
                            logging.info(f"⏭️ File già presente su R2: {r2_key}")
                            # Salva chiave anche se già presente
                            if matched_suffix == "_full.wav":
                                file_key = f"{target_dir}/{beat_name}_full.wav"
                            elif matched_suffix == "_spoiler.wav":
                                preview_key = f"{target_dir}/{beat_name}_spoiler.mp3"
                            elif matched_suffix in ["_pic.jpg", "_pic.jpeg"]:
                                image_key = f"{target_dir}/{beat_name}{matched_suffix}"
                            continue
                        
                        # Download file
                        try:
                            file_data = download_drive_file(drive_service, file['id'])
                            content_type = get_content_type_from_filename(file_name)
                            
                            # Conversione MP3 per preview
                            if matched_suffix == "_spoiler.wav":
                                mp3_data = convert_wav_to_mp3_direct(file_data)
                                if mp3_data:
                                    r2_key = f"{target_dir}/{beat_name}_spoiler.mp3"
                                    content_type = 'audio/mpeg'
                                    file_data = mp3_data
                                    logging.info("🎵 Convertita preview in MP3")
                                else:
                                    logging.error("❌ Conversione preview fallita")
                            
                            # Upload su R2
                            if upload_to_r2_direct(r2_client, file_data, r2_key, content_type):
                                logging.info(f"✅ Upload completato: {r2_key}")
                                
                                # Salva chiavi per database
                                if matched_suffix == "_full.wav":
                                    file_key = f"{target_dir}/{beat_name}_full.wav"
                                elif matched_suffix == "_spoiler.wav":
                                    preview_key = f"{target_dir}/{beat_name}_spoiler.mp3"
                                elif matched_suffix in ["_pic.jpg", "_pic.jpeg"]:
                                    image_key = f"{target_dir}/{beat_name}{matched_suffix}"
                            else:
                                valid_beat = False
                        except Exception as e:
                            logging.error(f"❌ Errore processando {file_name}: {str(e)}")
                            valid_beat = False
                    
                    # Verifica completezza del beat
                    if not file_key or not preview_key or not image_key:
                        logging.warning(f"⚠️ Beat incompleto: {beat_name}")
                        valid_beat = False
                    
                    if not valid_beat:
                        skipped_count += 1
                    else:
                        # Inserisci nel database
                        beat_data = {
                            'genre': genre_name,
                            'mood': mood_name,
                            'folder': beat_folder_name,
                            'title': beat_name,
                            'preview_key': preview_key,
                            'file_key': file_key,
                            'image_key': image_key,
                            'price': 19.99,
                            'original_price': None,
                            'is_exclusive': 0,
                            'is_discounted': 0,
                            'discount_percent': 0,
                            'available': 1,
                            'reserved_by_user_id': None,
                            'reserved_at': None,
                            'reservation_expires_at': None
                        }
                        
                        success, message = create_beat_from_migration(beat_data)
                        if success:
                            processed_count += 1
                            logging.info(f"✅ Beat inserito nel database: {beat_name}")
                        else:
                            logging.error(f"❌ Errore inserimento database: {beat_name} - {message}")
                            skipped_count += 1
        
        session.close()
        
        # Risultati finali
        update_progress(operation_id, 90, "Finalizzazione...")
        total_beats = processed_count + skipped_count
        
        if total_beats == 0:
            update_progress(operation_id, 100, "Errore: Nessun beat trovato", "")
            return False, "Nessun beat trovato nella struttura Google Drive"
        
        success_rate = (processed_count/total_beats)*100 if total_beats > 0 else 0
        result_message = f"Beat processati: {processed_count}, saltati: {skipped_count}, successo: {success_rate:.1f}%"
        
        update_progress(operation_id, 100, "Migrazione completata!", result_message)
        logging.info("="*60)
        logging.info("🎉 MIGRAZIONE COMPLETATA")
        logging.info(f"📊 {result_message}")
        logging.info("="*60)
        
        return True, result_message
        
    except Exception as e:
        error_msg = f"Errore durante la migrazione: {str(e)}"
        logging.error(f"❌ {error_msg}")
        update_progress(operation_id, 100, "Errore migrazione", error_msg)
        return False, error_msg

if __name__ == "__main__":
    # Configurazione per Railway deployment
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
