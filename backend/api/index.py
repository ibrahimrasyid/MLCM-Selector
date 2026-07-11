"""
Vercel Python serverless entry point.

Vercel's @vercel/python runtime detects the WSGI `app` object exported here and
serves it. We reuse the Flask app defined in ../app.py (single source of truth),
so local `python app.py` and the Vercel deployment run identical logic.
"""
import os
import sys

# Make the parent folder (backend/) importable so we can load app.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app  # noqa: E402  (WSGI application detected by Vercel)
