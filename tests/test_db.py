import unittest
import tempfile
import os
from pathlib import Path


class TestDBHelpers(unittest.TestCase):
    def setUp(self):
        # use a temporary DB file for tests
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'waypoint_test.db'
        # patch services.db.DB_PATH
        import importlib
        self.db = importlib.import_module('services.db')
        self.orig_db_path = getattr(self.db, 'DB_PATH')
        self.db.DB_PATH = self.db_path
        # ensure data dir exists
        self.db.init_db()

    def tearDown(self):
        # restore DB_PATH
        self.db.DB_PATH = self.orig_db_path
        self.tmpdir.cleanup()

    def test_pref_magic_session_export_flow(self):
        # prefs
        ok = self.db.set_pref('last_user', 'tester')
        self.assertTrue(ok)
        v = self.db.get_pref('last_user')
        self.assertEqual(v, 'tester')

        # magic token -> consume
        token = self.db.create_magic_token('u@example.com')
        self.assertTrue(isinstance(token, str) and len(token) > 0)
        email = self.db.consume_magic_token(token)
        self.assertEqual(email, 'u@example.com')

        # session create/get/delete
        sid = self.db.create_session('u@example.com', ttl_seconds=60)
        self.assertTrue(isinstance(sid, str) and len(sid) > 0)
        user = self.db.get_session_user(sid)
        self.assertEqual(user, 'u@example.com')
        okdel = self.db.delete_session(sid)
        self.assertTrue(okdel)

        # save export file and history
        content = b'{"ok": true}'
        outp = self.db.save_export_file('test_export.json', content, user='u@example.com')
        self.assertTrue(outp and Path(outp).exists())
        hist = self.db.list_history(limit=10)
        self.assertTrue(any(h.get('action') == 'export_explanation' for h in hist))


if __name__ == '__main__':
    unittest.main()
