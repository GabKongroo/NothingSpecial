# Dockerfile per Admin Web - Interfaccia di amministrazione Flask
FROM python:3.13-slim

# Imposta la directory di lavoro
WORKDIR /app

# Installa dipendenze di sistema per ffmpeg (necessario per conversione audio)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copia i file dei requisiti
COPY requirements.txt .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'applicazione
COPY . .

# Espone la porta 8000
EXPOSE 8000

# Comando per avviare l'applicazione
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "admin_web:app"]
