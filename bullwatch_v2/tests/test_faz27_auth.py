# -*- coding: utf-8 -*-
"""FAZ 27 — User Accounts / Auth / Cloud Sync Tests.

Tests:
  1. User engine: register, authenticate, get_user, save/load user_data
  2. Auth API: register, login, me, logout, protected routes
  3. Journal user_id linking
  4. Strategy user_id linking
  5. Simulator user_id linking
  6. Cloud data save/load
"""
import json
import os
import sys
import tempfile
import uuid

import pytest

# Ensure project root is in path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Route all DBs to temp directory so tests don't pollute real data."""
    db_dir = str(tmp_path / "data")
    os.makedirs(db_dir, exist_ok=True)

    # Patch db_manager (centralized)
    monkeypatch.setattr("app.core.db_manager._DB_DIR", db_dir)

    # Patch user_engine
    monkeypatch.setattr("app.core.user_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.user_engine._DB_PATH", os.path.join(db_dir, "users.db"))

    # Patch journal_engine
    monkeypatch.setattr("app.core.journal_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.journal_engine._DB_PATH", os.path.join(db_dir, "journal.db"))

    # Patch paper_trading_engine
    monkeypatch.setattr("app.core.paper_trading_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.paper_trading_engine._DB_PATH", os.path.join(db_dir, "paper_trading.db"))

    # Re-init paper_trading tables in temp DB (since _init_db ran at import time on real DB)
    from app.core.paper_trading_engine import _init_db
    _init_db()


@pytest.fixture
def app():
    """Create Flask test app via the proper factory."""
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# ══════════════════════════════════════════════════════════════════════
# 1. USER ENGINE UNIT TESTS
# ══════════════════════════════════════════════════════════════════════

class TestUserEngine:
    """Test user_engine.py core functions."""

    def test_register_user(self):
        from app.core.user_engine import register_user
        user = register_user("test@example.com", "testuser", "password123")
        assert user["email"] == "test@example.com"
        assert user["username"] == "testuser"
        assert "password_hash" not in user
        assert "id" in user

    def test_register_duplicate_email(self):
        from app.core.user_engine import register_user
        register_user("dup@example.com", "user1", "password123")
        with pytest.raises(ValueError, match="zaten kayıtlı|already"):
            register_user("dup@example.com", "user2", "password456")

    def test_register_invalid_email(self):
        from app.core.user_engine import register_user
        with pytest.raises(ValueError):
            register_user("not-an-email", "user", "password123")

    def test_register_short_password(self):
        from app.core.user_engine import register_user
        with pytest.raises(ValueError):
            register_user("short@example.com", "user", "123")

    def test_authenticate_success(self):
        from app.core.user_engine import register_user, authenticate
        register_user("auth@example.com", "authuser", "mypassword")
        user = authenticate("auth@example.com", "mypassword")
        assert user is not None
        assert user["email"] == "auth@example.com"

    def test_authenticate_wrong_password(self):
        from app.core.user_engine import register_user, authenticate
        register_user("wrong@example.com", "wronguser", "correct")
        user = authenticate("wrong@example.com", "incorrect")
        assert user is None

    def test_authenticate_nonexistent_user(self):
        from app.core.user_engine import authenticate
        user = authenticate("noexist@example.com", "pass")
        assert user is None

    def test_get_user(self):
        from app.core.user_engine import register_user, get_user
        created = register_user("get@example.com", "getuser", "password123")
        found = get_user(created["id"])
        assert found is not None
        assert found["email"] == "get@example.com"

    def test_save_load_user_data(self):
        from app.core.user_engine import register_user, save_user_data, load_user_data
        user = register_user("data@example.com", "datauser", "password123")
        uid = user["id"]

        test_data = {"watchlist": ["BTCUSDT", "ETHUSDT"], "theme": "dark"}
        save_user_data(uid, "preferences", test_data)

        loaded = load_user_data(uid, "preferences")
        assert loaded == test_data

    def test_load_nonexistent_data(self):
        from app.core.user_engine import register_user, load_user_data
        user = register_user("nodata@example.com", "nodatauser", "password123")
        loaded = load_user_data(user["id"], "nonexistent_key")
        assert loaded is None


# ══════════════════════════════════════════════════════════════════════
# 2. AUTH API TESTS
# ══════════════════════════════════════════════════════════════════════

class TestAuthAPI:
    """Test auth blueprint endpoints."""

    def test_register_api(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "api@example.com",
            "username": "apiuser",
            "password": "password123",
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["ok"] is True
        assert data["user"]["email"] == "api@example.com"

    def test_register_missing_fields(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "missing@example.com",
        })
        assert resp.status_code == 400

    def test_login_api(self, client):
        # Register first
        client.post("/api/auth/register", json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "password123",
        })
        # Login
        resp = client.post("/api/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["ok"] is True
        assert data["user"]["email"] == "login@example.com"

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={
            "email": "wronglogin@example.com",
            "username": "wrongloginuser",
            "password": "correctpass",
        })
        resp = client.post("/api/auth/login", json={
            "email": "wronglogin@example.com",
            "password": "wrongpass",
        })
        assert resp.status_code == 401

    def test_me_logged_in(self, client):
        client.post("/api/auth/register", json={
            "email": "me@example.com",
            "username": "meuser",
            "password": "password123",
        })
        resp = client.get("/api/auth/me")
        data = resp.get_json()
        assert data["logged_in"] is True
        assert data["user"]["email"] == "me@example.com"

    def test_me_not_logged_in(self, client):
        resp = client.get("/api/auth/me")
        data = resp.get_json()
        assert data["logged_in"] is False

    def test_logout(self, client):
        client.post("/api/auth/register", json={
            "email": "logout@example.com",
            "username": "logoutuser",
            "password": "password123",
        })
        # Should be logged in after register
        me = client.get("/api/auth/me").get_json()
        assert me["logged_in"] is True

        # Logout
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200

        # Should not be logged in
        me = client.get("/api/auth/me").get_json()
        assert me["logged_in"] is False

    def test_cloud_data_save_load(self, client):
        # Register + auto login
        client.post("/api/auth/register", json={
            "email": "cloud@example.com",
            "username": "clouduser",
            "password": "password123",
        })

        # Save data
        resp = client.post("/api/auth/data/save", json={
            "key": "watchlist",
            "data": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        })
        data = resp.get_json()
        assert data["ok"] is True

        # Load data
        resp = client.post("/api/auth/data/load", json={
            "key": "watchlist",
        })
        data = resp.get_json()
        assert data["ok"] is True
        assert data["data"] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def test_cloud_data_requires_login(self, client):
        resp = client.post("/api/auth/data/save", json={
            "key": "test",
            "data": {"test": True},
        })
        assert resp.status_code == 401

    def test_login_page(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Giriş".encode() in resp.data or b"login" in resp.data.lower()

    def test_register_page(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200
        assert "Kayıt".encode() in resp.data or b"register" in resp.data.lower()


# ══════════════════════════════════════════════════════════════════════
# 3. JOURNAL USER_ID LINKING
# ══════════════════════════════════════════════════════════════════════

class TestJournalUserLink:
    """Test journal entries are linked to user_id."""

    def test_journal_add_with_user_id(self, client):
        # Register and login
        client.post("/api/auth/register", json={
            "email": "journal@example.com",
            "username": "journaluser",
            "password": "password123",
        })

        # Add journal entry (logged in)
        resp = client.post("/api/journal", json={
            "symbol": "BTCUSDT",
            "side": "buy",
            "entry_price": 70000,
            "exit_price": 72000,
            "quantity": 0.1,
            "pnl": 200,
            "emotion": "confident",
        })
        data = resp.get_json()
        assert resp.status_code == 201
        assert data["ok"] is True
        assert data["entry"]["symbol"] == "BTCUSDT"

    def test_journal_list_filters_by_user(self, client):
        # Register user1
        client.post("/api/auth/register", json={
            "email": "juser1@example.com",
            "username": "juser1",
            "password": "password123",
        })
        client.post("/api/journal", json={
            "symbol": "BTCUSDT",
            "side": "buy",
            "entry_price": 70000,
        })
        client.post("/api/auth/logout")

        # Register user2
        client.post("/api/auth/register", json={
            "email": "juser2@example.com",
            "username": "juser2",
            "password": "password123",
        })
        client.post("/api/journal", json={
            "symbol": "ETHUSDT",
            "side": "sell",
            "entry_price": 3500,
        })

        # User2 should only see their own entries
        resp = client.get("/api/journal")
        data = resp.get_json()
        assert data["ok"] is True
        symbols = [e["symbol"] for e in data["entries"]]
        assert "ETHUSDT" in symbols
        assert "BTCUSDT" not in symbols


# ══════════════════════════════════════════════════════════════════════
# 4. STRATEGY USER_ID LINKING
# ══════════════════════════════════════════════════════════════════════

class TestStrategyUserLink:
    """Test strategies are linked to user_id."""

    def test_strategy_save_with_user_id(self, client):
        client.post("/api/auth/register", json={
            "email": "strat@example.com",
            "username": "stratuser",
            "password": "password123",
        })

        resp = client.post("/api/strategy/save", json={
            "name": "TestStrategy",
            "code": "RSI < 30",
            "conditions": [
                {"indicator": "RSI", "operator": "<", "value": 30}
            ],
        })
        data = resp.get_json()
        assert data["ok"] is True

    def test_strategy_list_per_user(self, client):
        # Register user1
        client.post("/api/auth/register", json={
            "email": "su1@example.com",
            "username": "su1",
            "password": "password123",
        })
        client.post("/api/strategy/save", json={
            "name": "User1Strategy",
            "code": "MACD > 0",
            "conditions": [],
        })
        client.post("/api/auth/logout")

        # Register user2
        client.post("/api/auth/register", json={
            "email": "su2@example.com",
            "username": "su2",
            "password": "password123",
        })

        resp = client.get("/api/strategy/list")
        data = resp.get_json()
        assert data["ok"] is True
        names = [s["name"] for s in data.get("strategies", [])]
        assert "User1Strategy" not in names


# ══════════════════════════════════════════════════════════════════════
# 5. SIMULATOR USER_ID LINKING
# ══════════════════════════════════════════════════════════════════════

class TestSimulatorUserLink:
    """Test simulator accounts are linked to user_id."""

    def test_account_per_user(self, client):
        # Register user1
        client.post("/api/auth/register", json={
            "email": "sim1@example.com",
            "username": "sim1",
            "password": "password123",
        })

        resp1 = client.get("/api/simulator/account")
        data1 = resp1.get_json()
        assert data1["ok"] is True
        acc_id1 = data1["account"]["id"]

        client.post("/api/auth/logout")

        # Register user2
        client.post("/api/auth/register", json={
            "email": "sim2@example.com",
            "username": "sim2",
            "password": "password123",
        })

        resp2 = client.get("/api/simulator/account")
        data2 = resp2.get_json()
        assert data2["ok"] is True
        acc_id2 = data2["account"]["id"]

        # Different users should have different accounts
        assert acc_id1 != acc_id2


# ══════════════════════════════════════════════════════════════════════
# 6. INTEGRATION — ALL TOGETHER
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Full flow: register → login → use features → logout → verify isolation."""

    def test_full_user_workflow(self, client):
        # 1. Register
        resp = client.post("/api/auth/register", json={
            "email": "fulltest@example.com",
            "username": "fulltest",
            "password": "password123",
        })
        assert resp.status_code == 201
        user_data = resp.get_json()
        user_id = user_data["user"]["id"]

        # 2. Check logged in
        me = client.get("/api/auth/me").get_json()
        assert me["logged_in"] is True
        assert me["user"]["username"] == "fulltest"

        # 3. Save cloud data (drawings)
        client.post("/api/auth/data/save", json={
            "key": "drawings",
            "data": {"chart1": [{"id": "d1", "type": "line"}]},
        })

        # 4. Load cloud data
        resp = client.post("/api/auth/data/load", json={"key": "drawings"})
        drawings = resp.get_json()
        assert drawings["data"]["chart1"][0]["id"] == "d1"

        # 5. Journal entry
        resp = client.post("/api/journal", json={
            "symbol": "BTCUSDT",
            "side": "buy",
            "entry_price": 70000,
            "pnl": 500,
        })
        assert resp.status_code == 201

        # 6. Strategy save
        resp = client.post("/api/strategy/save", json={
            "name": "IntegrationStrategy",
            "code": "MACD > 0",
            "conditions": [{"indicator": "MACD", "operator": ">", "value": 0}],
        })
        assert resp.get_json()["ok"] is True

        # 7. Logout
        client.post("/api/auth/logout")
        me = client.get("/api/auth/me").get_json()
        assert me["logged_in"] is False

        # 8. Cloud data should be protected
        resp = client.post("/api/auth/data/load", json={"key": "drawings"})
        assert resp.status_code == 401
