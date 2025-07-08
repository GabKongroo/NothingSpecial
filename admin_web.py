from flask import Flask, render_template, request, redirect, url_for, session
from model import SessionLocal, Beat, Bundle, BundleBeat, Bundle
from sqlalchemy import or_
import os
import json
from pathlib import Path

# Google Drive imports (if needed)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️ Google API libraries not available")

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# Google Drive Configuration
DRIVE_ROOT_FOLDER_ID = os.environ.get("DRIVE_ROOT_FOLDER_ID")
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_google_credentials():
    """
    Ottiene le credenziali Google Drive da variabile di ambiente o file locale.
    """
    if not GOOGLE_AVAILABLE:
        print("❌ Google API libraries not available")
        return None
    
    # Prova prima la variabile di ambiente
    service_account_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if service_account_json and service_account_json.strip():
        try:
            credentials_info = json.loads(service_account_json)
            print("✅ Credenziali Google caricate da variabile di ambiente")
            return service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES
            )
        except json.JSONDecodeError as e:
            print(f"❌ Errore parsing GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
    
    # Fallback al file locale (solo sviluppo)
    service_account_file = Path(__file__).parent / 'pegasus.json'
    if service_account_file.exists():
        print("✅ Credenziali Google caricate da file locale")
        return service_account.Credentials.from_service_account_file(
            service_account_file, scopes=SCOPES
        )
    
    print("❌ Nessuna credenziale Google trovata")
    return None

def get_drive_service():
    """Get authenticated Google Drive service"""
    if not GOOGLE_AVAILABLE:
        return None
    
    credentials = get_google_credentials()
    if credentials:
        return build('drive', 'v3', credentials=credentials)
    return None

# Health check endpoint per Railway
@app.route("/health")
def health_check():
    """Endpoint per verificare lo stato dell'applicazione"""
    try:
        # Test connessione database
        with SessionLocal() as db:
            db.execute("SELECT 1")
        
        return {"status": "healthy", "service": "admin-web", "database": "ok"}, 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return {"status": "unhealthy", "service": "admin-web", "error": str(e)}, 503

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
                    # Cambia qui:
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
                        error = f"Il prezzo scontato non può essere maggiore del prezzo originale per il beat '{beat.title}'!"
                        error_beat_id = beat.id
                        break

                    if is_discounted and discount_percent < 0:
                        error = f"La percentuale di sconto non può essere negativa per il beat '{beat.title}'!"
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


@app.route("/login", methods=["POST"])
def login():
    password = request.form.get("password", "")
    if password == ADMIN_PASSWORD:
        session["logged_in"] = True
        return redirect(url_for("index"))
    return render_template("admin_web.html", beats=[], error="Password errata!", error_beat_id=None)


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/bundles")
def bundles():
    """Gestione bundles"""
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    try:
        with SessionLocal() as db:
            bundles = db.query(Bundle).all()
            return render_template("bundles.html", bundles=bundles)
    except Exception as e:
        print(f"❌ Error loading bundles: {e}")
        return render_template("bundles.html", bundles=[], error=str(e))

@app.route("/database_admin")
def database_admin():
    """Amministrazione database"""
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    try:
        with SessionLocal() as db:
            # Statistiche database
            beats_count = db.query(Beat).count()
            bundles_count = db.query(Bundle).count()
            
            stats = {
                "beats_count": beats_count,
                "bundles_count": bundles_count
            }
            
            return render_template("database_admin.html", stats=stats)
    except Exception as e:
        print(f"❌ Error loading database admin: {e}")
        return render_template("database_admin.html", stats={}, error=str(e))

@app.route("/create_bundle", methods=["GET", "POST"])
def create_bundle():
    """Creazione bundle"""
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    if request.method == "POST":
        try:
            with SessionLocal() as db:
                # Logica per creare bundle
                bundle_name = request.form.get("bundle_name")
                selected_beats = request.form.getlist("selected_beats")
                
                # Crea bundle nel database
                new_bundle = Bundle(
                    name=bundle_name,
                    price=float(request.form.get("bundle_price", 0))
                )
                db.add(new_bundle)
                db.commit()
                
                return redirect(url_for("bundles"))
        except Exception as e:
            print(f"❌ Error creating bundle: {e}")
            return render_template("create_bundle.html", error=str(e))
    
    try:
        with SessionLocal() as db:
            beats = db.query(Beat).all()
            return render_template("create_bundle.html", beats=beats)
    except Exception as e:
        return render_template("create_bundle.html", beats=[], error=str(e))

@app.route("/edit_bundle/<int:bundle_id>", methods=["GET", "POST"])
def edit_bundle(bundle_id):
    """Modifica bundle"""
    if not session.get("logged_in"):
        return redirect(url_for("index"))
    
    if request.method == "POST":
        try:
            with SessionLocal() as db:
                bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
                if bundle:
                    bundle.name = request.form.get("bundle_name")
                    bundle.price = float(request.form.get("bundle_price", 0))
                    db.commit()
                    return redirect(url_for("bundles"))
        except Exception as e:
            print(f"❌ Error editing bundle: {e}")
    
    try:
        with SessionLocal() as db:
            bundle = db.query(Bundle).filter(Bundle.id == bundle_id).first()
            beats = db.query(Beat).all()
            return render_template("edit_bundle.html", bundle=bundle, beats=beats)
    except Exception as e:
        return render_template("edit_bundle.html", bundle=None, beats=[], error=str(e))

if __name__ == "__main__":
    # Supporto per porta di produzione (Railway)
    port = int(os.environ.get("PORT", 8000))
    debug_mode = os.environ.get("FLASK_ENV", "development") == "development"
    
    print(f"🚀 Starting Admin Web on port {port}")
    print(f"🔧 Debug mode: {debug_mode}")
    print(f"🔑 Google Drive available: {GOOGLE_AVAILABLE}")
    
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
