from flask import Flask, render_template, request, redirect, url_for, session
from model import SessionLocal, Beat
from sqlalchemy import or_
import os
from dotenv import load_dotenv

load_dotenv()  # Carica le variabili dal file .env

app = Flask(__name__)
app.secret_key = os.environ.get("ADMIN_SECRET_KEY")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

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


if __name__ == "__main__":
    app.run(debug=True, port=5001)

