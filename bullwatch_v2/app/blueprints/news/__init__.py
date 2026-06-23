# -*- coding: utf-8 -*-
"""News Blueprint — Market intelligence API endpoints.

FAZ 15 — Provides ``/api/news`` and ``/api/news/coin`` endpoints.
"""
from flask import Blueprint

news_bp = Blueprint("news", __name__)

from app.blueprints.news.routes import *  # noqa: E402, F401, F403
