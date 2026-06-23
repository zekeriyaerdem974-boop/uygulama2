import pytest
from flask import Flask
import sys
sys.path.append("..")
from legacy_monolith import app

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from legacy_monolith import app

# Flask test client fixture
@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# FAZ 38 UI testleri: layout, sidebar, bottom bar, legal footer, chat sayfası
# Updated for FAZ UI REBUILD: pro-layout → tl-grid, pro-sidebar → tl-sidebar

def test_base_app_ui(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data


def test_discover_ui(client):
    response = client.get("/discover")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data


def test_feed_ui(client):
    response = client.get("/feed")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data


def test_market_radar_ui(client):
    response = client.get("/market-radar")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data


def test_trade_ui(client):
    response = client.get("/trade")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data


def test_chat_ui(client):
    response = client.get("/chat")
    assert response.status_code == 200
    assert b"tl-grid" in response.data
    assert b"pro-bottombar" in response.data
    assert b"terminal.css" in response.data

# Not: client fixture pytest-flask ile sağlanır.
