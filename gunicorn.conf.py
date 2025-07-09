# Gunicorn configuration file
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = min(multiprocessing.cpu_count() * 2 + 1, 4)  # Max 4 workers
worker_class = "sync"
worker_connections = 1000
timeout = 600  # 10 minutes timeout for long operations like migration
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Memory management
worker_tmp_dir = "/tmp"
max_worker_memory = 256 * 1024 * 1024  # 256MB per worker

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "admin-web"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = "/tmp"

# SSL
keyfile = None
certfile = None

# Graceful timeout for worker restart
graceful_timeout = 60

# Preload app for better performance
preload_app = True

# Enable threading
threads = 2

# Additional settings for long-running operations
worker_timeout = 600  # 10 minutes
graceful_timeout = 60  # 1 minute for graceful shutdown
