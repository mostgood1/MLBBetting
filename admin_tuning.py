"""
Stub admin_tuning module for local development and static analysis.
In production, admin features may be disabled; this stub prevents import errors.
"""
from flask import Blueprint

# Minimal blueprint to satisfy references; routes can be added if needed.
admin_bp = Blueprint("admin", __name__)
