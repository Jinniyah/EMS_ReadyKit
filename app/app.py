# app.py
# Top-level entry point for Azure App Service / Oryx framework detection.
# Oryx needs to find app.py at the repo root to detect this as a Python
# web application and install dependencies from requirements.txt.
# Without this file, Oryx falls back to the default placeholder site.
#
# The actual startup command (antenv/bin/gunicorn ... ems_readykit.main:app)
# is set in Terraform app_command_line and takes precedence over this file.

from ems_readykit.main import app  # noqa: F401

application = app  # WSGI/ASGI compatibility alias
