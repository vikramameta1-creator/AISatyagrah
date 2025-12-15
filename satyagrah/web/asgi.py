# satyagrah/web/asgi.py
from .jobs_api import create_app

# Run with:
#   uvicorn satyagrah.web.asgi:app --host 127.0.0.1 --port 9000 --reload
app = create_app()
