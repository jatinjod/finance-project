import os

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

workers = 2
worker_class = "sync"
worker_connections = 1000

timeout = 120
keepalive = 2

accesslog = "-"
errorlog = "-"
loglevel = "info"

daemon = False
reload = False
preload_app = True