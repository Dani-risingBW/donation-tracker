"""Production entry point for gunicorn. Refuses to start with missing or development secrets."""
import os

DEVELOPMENT_DEFAULTS = {"SECRET_KEY": "dev-secret-key", "ADMIN_PASSWORD": "admin123"}

for name, development_value in DEVELOPMENT_DEFAULTS.items():
    value = os.environ.get(name, "")
    if not value or value == development_value:
        raise RuntimeError(f"Set {name} to a real secret before starting in production.")

from .app import app  # noqa: E402
