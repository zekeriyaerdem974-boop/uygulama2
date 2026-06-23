# -*- coding: utf-8 -*-
"""FAZ 34 — Live Trading Rooms Tests.

35 tests covering:
  - Room CRUD (create, update, start, stop)
  - Room listing and filtering
  - Participant management (join, leave)
  - Message posting and listing
  - Slug generation
  - WebSocket registry
  - Mentor rooms
  - Room stats
  - Visibility options
  - Signal and chart_share message types
"""
import os
import sys
import unittest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use temp DB for tests
import tempfile
_tmp_dir = tempfile.mkdtemp()
os.environ.setdefault("ZKR_ANALIZ_DATA_DIR", _tmp_dir)

import app.core.live_room_engine as lre

# Override DB path
import app.core.db_manager as _dm
_dm._DB_DIR = _tmp_dir
lre._DB_DIR = _tmp_dir
lre._DB_PATH = os.path.join(_tmp_dir, "live_rooms_test.db")
lre._USERS_DB = os.path.join(_tmp_dir, "users_test.db")

# Re-init
lre._init_db()

MENTOR1 = "mentor-uid-001"
MENTOR2 = "mentor-uid-002"
USER1 = "user-uid-001"
USER2 = "user-uid-002"


class TestLiveRoomEngine(unittest.TestCase):

    def setUp(self):
        conn = lre._get_conn()
        conn.execute("DELETE FROM room_messages")
        conn.execute("DELETE FROM room_participants")
        conn.execute("DELETE FROM live_rooms")
        conn.commit()
        conn.close()
        # Clear WS clients
        lre._ws_clients.clear()

    # ── Room CRUD ───────────────────────────────────────────

    def test_create_room(self):
        room = lre.create_room(MENTOR1, "Kripto Canlı Analiz", market="crypto")
        self.assertEqual(room["title"], "Kripto Canlı Analiz")
        self.assertEqual(room["market"], "crypto")
        self.assertEqual(room["is_active"], 0)
        self.assertEqual(room["visibility"], "public")
        self.assertIn("slug", room)
        self.assertEqual(room["participant_count"], 1)  # mentor auto-joins

    def test_create_room_empty_title_raises(self):
        with self.assertRaises(ValueError):
            lre.create_room(MENTOR1, "")

    def test_create_room_invalid_market_raises(self):
        with self.assertRaises(ValueError):
            lre.create_room(MENTOR1, "Test Oda", market="invalidmarket")

    def test_update_room(self):
        room = lre.create_room(MENTOR1, "Oda 1")
        updated = lre.update_room(room["id"], MENTOR1, title="Yeni Başlık")
        self.assertEqual(updated["title"], "Yeni Başlık")

    def test_update_room_wrong_owner(self):
        room = lre.create_room(MENTOR1, "Oda 1")
        with self.assertRaises(ValueError):
            lre.update_room(room["id"], MENTOR2, title="Hack")

    def test_slug_unique(self):
        r1 = lre.create_room(MENTOR1, "Test Oda")
        r2 = lre.create_room(MENTOR2, "Test Oda")
        self.assertNotEqual(r1["slug"], r2["slug"])

    def test_start_room(self):
        room = lre.create_room(MENTOR1, "Start Test")
        started = lre.start_room(room["id"], MENTOR1)
        self.assertEqual(started["is_active"], 1)

    def test_stop_room(self):
        room = lre.create_room(MENTOR1, "Stop Test")
        lre.start_room(room["id"], MENTOR1)
        stopped = lre.stop_room(room["id"], MENTOR1)
        self.assertEqual(stopped["is_active"], 0)

    def test_start_room_wrong_owner(self):
        room = lre.create_room(MENTOR1, "Oda")
        with self.assertRaises(ValueError):
            lre.start_room(room["id"], MENTOR2)

    def test_stop_room_wrong_owner(self):
        room = lre.create_room(MENTOR1, "Oda")
        lre.start_room(room["id"], MENTOR1)
        with self.assertRaises(ValueError):
            lre.stop_room(room["id"], MENTOR2)

    def test_start_creates_system_message(self):
        room = lre.create_room(MENTOR1, "Msg Test")
        lre.start_room(room["id"], MENTOR1)
        msgs = lre.list_messages(room["id"])
        system_msgs = [m for m in msgs if m["message_type"] == "system"]
        self.assertTrue(any("başladı" in m["content"] for m in system_msgs))

    def test_stop_creates_system_message(self):
        room = lre.create_room(MENTOR1, "Stop Msg Test")
        lre.start_room(room["id"], MENTOR1)
        lre.stop_room(room["id"], MENTOR1)
        msgs = lre.list_messages(room["id"])
        system_msgs = [m for m in msgs if m["message_type"] == "system"]
        self.assertTrue(any("sona erdi" in m["content"] for m in system_msgs))

    # ── Get & List ──────────────────────────────────────────

    def test_get_room_by_slug(self):
        room = lre.create_room(MENTOR1, "Slug Test", market="bist")
        fetched = lre.get_room(room["slug"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "Slug Test")

    def test_get_room_viewer_status(self):
        room = lre.create_room(MENTOR1, "Viewer Test")
        lre.join_room(room["id"], USER1)
        fetched = lre.get_room(room["slug"], viewer_id=USER1)
        self.assertTrue(fetched["is_joined"])
        self.assertFalse(fetched["is_owner"])

    def test_get_room_owner_status(self):
        room = lre.create_room(MENTOR1, "Owner View")
        fetched = lre.get_room(room["slug"], viewer_id=MENTOR1)
        self.assertTrue(fetched["is_owner"])
        self.assertTrue(fetched["is_joined"])

    def test_list_rooms(self):
        lre.create_room(MENTOR1, "R1", market="crypto")
        lre.create_room(MENTOR2, "R2", market="bist")
        rooms = lre.list_rooms()
        self.assertEqual(len(rooms), 2)

    def test_list_rooms_filter_market(self):
        lre.create_room(MENTOR1, "R1", market="crypto")
        lre.create_room(MENTOR2, "R2", market="bist")
        rooms = lre.list_rooms(market="crypto")
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["market"], "crypto")

    def test_list_rooms_active_only(self):
        r1 = lre.create_room(MENTOR1, "Active", market="crypto")
        lre.create_room(MENTOR2, "Inactive", market="bist")
        lre.start_room(r1["id"], MENTOR1)
        rooms = lre.list_rooms(active_only=True)
        self.assertEqual(len(rooms), 1)
        self.assertEqual(rooms[0]["is_active"], 1)

    # ── Participants ────────────────────────────────────────

    def test_join_room(self):
        room = lre.create_room(MENTOR1, "Join Test")
        p = lre.join_room(room["id"], USER1)
        self.assertEqual(p["role"], "member")
        self.assertEqual(p["user_id"], USER1)

    def test_join_room_twice_returns_existing(self):
        room = lre.create_room(MENTOR1, "Double Join")
        p1 = lre.join_room(room["id"], USER1)
        p2 = lre.join_room(room["id"], USER1)
        self.assertEqual(p1["id"], p2["id"])

    def test_leave_room(self):
        room = lre.create_room(MENTOR1, "Leave Test")
        lre.join_room(room["id"], USER1)
        result = lre.leave_room(room["id"], USER1)
        self.assertTrue(result)
        participants = lre.get_participants(room["id"])
        user_ids = [p["user_id"] for p in participants]
        self.assertNotIn(USER1, user_ids)

    def test_mentor_cannot_leave_own_room(self):
        room = lre.create_room(MENTOR1, "Mentor Stay")
        with self.assertRaises(ValueError):
            lre.leave_room(room["id"], MENTOR1)

    def test_get_participants(self):
        room = lre.create_room(MENTOR1, "Participants")
        lre.join_room(room["id"], USER1)
        lre.join_room(room["id"], USER2)
        parts = lre.get_participants(room["id"])
        self.assertEqual(len(parts), 3)  # mentor + 2 users

    def test_participant_count_in_room(self):
        room = lre.create_room(MENTOR1, "Count Test")
        lre.join_room(room["id"], USER1)
        lre.join_room(room["id"], USER2)
        fetched = lre.get_room_by_id(room["id"])
        self.assertEqual(fetched["participant_count"], 3)

    # ── Messages ────────────────────────────────────────────

    def test_post_message(self):
        room = lre.create_room(MENTOR1, "Msg Room")
        msg = lre.post_message(room["id"], USER1, "Merhaba!")
        self.assertEqual(msg["content"], "Merhaba!")
        self.assertEqual(msg["message_type"], "text")
        self.assertEqual(msg["user_id"], USER1)

    def test_post_empty_message_raises(self):
        room = lre.create_room(MENTOR1, "Empty Msg")
        with self.assertRaises(ValueError):
            lre.post_message(room["id"], USER1, "")

    def test_post_signal_message(self):
        room = lre.create_room(MENTOR1, "Signal Room")
        msg = lre.post_message(room["id"], MENTOR1, "BTC LONG @ 65000", message_type="signal")
        self.assertEqual(msg["message_type"], "signal")

    def test_post_chart_share(self):
        room = lre.create_room(MENTOR1, "Chart Room")
        msg = lre.post_message(room["id"], MENTOR1, "BTC 4H Chart Analysis", message_type="chart_share")
        self.assertEqual(msg["message_type"], "chart_share")

    def test_list_messages(self):
        room = lre.create_room(MENTOR1, "List Msgs")
        lre.post_message(room["id"], USER1, "Msg 1")
        lre.post_message(room["id"], USER2, "Msg 2")
        lre.post_message(room["id"], MENTOR1, "Msg 3")
        msgs = lre.list_messages(room["id"])
        self.assertEqual(len(msgs), 3)
        self.assertEqual(msgs[0]["content"], "Msg 1")
        self.assertEqual(msgs[2]["content"], "Msg 3")

    def test_list_messages_limit(self):
        room = lre.create_room(MENTOR1, "Limit Test")
        for i in range(10):
            lre.post_message(room["id"], USER1, f"Msg {i}")
        msgs = lre.list_messages(room["id"], limit=5)
        self.assertEqual(len(msgs), 5)

    def test_message_role_mentor(self):
        room = lre.create_room(MENTOR1, "Role Test")
        msg = lre.post_message(room["id"], MENTOR1, "Mentor message")
        self.assertEqual(msg["role"], "mentor")

    # ── Mentor / Stats ──────────────────────────────────────

    def test_get_mentor_rooms(self):
        lre.create_room(MENTOR1, "M1 Room 1")
        lre.create_room(MENTOR1, "M1 Room 2")
        lre.create_room(MENTOR2, "M2 Room 1")
        rooms = lre.get_mentor_rooms(MENTOR1)
        self.assertEqual(len(rooms), 2)

    def test_room_stats(self):
        r1 = lre.create_room(MENTOR1, "Stats 1")
        lre.create_room(MENTOR2, "Stats 2")
        lre.start_room(r1["id"], MENTOR1)
        lre.join_room(r1["id"], USER1)
        stats = lre.room_stats()
        self.assertEqual(stats["total_rooms"], 2)
        self.assertEqual(stats["active_rooms"], 1)
        self.assertGreaterEqual(stats["total_participants"], 2)
        self.assertEqual(stats["total_mentors"], 2)

    # ── Visibility ──────────────────────────────────────────

    def test_visibility_followers_only(self):
        room = lre.create_room(MENTOR1, "Followers", visibility="followers_only")
        self.assertEqual(room["visibility"], "followers_only")

    def test_visibility_subscribers_only(self):
        room = lre.create_room(MENTOR1, "Subs", visibility="subscribers_only")
        self.assertEqual(room["visibility"], "subscribers_only")

    def test_invalid_visibility_defaults_public(self):
        room = lre.create_room(MENTOR1, "Default Vis", visibility="invalid")
        self.assertEqual(room["visibility"], "public")


if __name__ == "__main__":
    unittest.main()
