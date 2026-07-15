import unittest
import tempfile
import os
from pathlib import Path

class TestDBExtra(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / 'waypoint_test.db'
        import importlib
        self.db = importlib.import_module('services.db')
        self.orig_db_path = getattr(self.db, 'DB_PATH')
        self.db.DB_PATH = self.db_path
        self.db.init_db()

    def tearDown(self):
        self.db.DB_PATH = self.orig_db_path
        self.tmpdir.cleanup()

    def test_sessions_listing_and_deletion(self):
        sid1 = self.db.create_session('a@example.com', ttl_seconds=60)
        sid2 = self.db.create_session('b@example.com', ttl_seconds=60)
        sid3 = self.db.create_session('a@example.com', ttl_seconds=60)
        all_sessions = self.db.list_sessions()
        self.assertTrue(len(all_sessions) >= 3)
        a_sessions = self.db.list_sessions(user='a@example.com')
        self.assertTrue(all(s['user'] == 'a@example.com' for s in a_sessions))
        deleted = self.db.delete_sessions_for_user('a@example.com')
        self.assertTrue(deleted >= 2)

    def test_favorites_and_feedback(self):
        self.db.save_favorite('Place A', score=4.5, meta={'tag':'x'}, user='u1')
        self.db.save_favorite('Place B', score=3.0, meta={}, user='u2')
        favs_u1 = self.db.list_favorites(user='u1')
        self.assertTrue(len(favs_u1) == 1)
        # delete favorite
        fid = favs_u1[0]['id']
        self.db.delete_favorite(fid)
        favs_u1_after = self.db.list_favorites(user='u1')
        self.assertEqual(len(favs_u1_after), 0)

        # feedback
        self.db.save_feedback('Place A', 'nice', details={'m':'ok'}, user='u1')
        f = self.db.list_feedback(user='u1')
        self.assertTrue(len(f) >= 1)

    def test_history_export_and_delete_export(self):
        # record history via save_export_file
        content = b'hello'
        path = self.db.save_export_file('x.csv', content, user='u1')
        self.assertTrue(path and Path(path).exists())
        hist = self.db.list_history(limit=10)
        rec = next((h for h in hist if h.get('action') == 'export_explanation'), None)
        self.assertIsNotNone(rec)
        hid = rec['id']
        # delete export by history id
        ok = self.db.delete_export(hid)
        self.assertTrue(ok)
        # ensure file removed
        p = Path(path)
        self.assertFalse(p.exists())

    def test_export_history_csv(self):
        # add a couple history rows
        self.db.save_history('action1', 'Place1', {'a':1}, user='u1')
        self.db.save_history('action2', 'Place2', {'b':2}, user='u2')
        outpath = Path(self.tmpdir.name) / 'hist.csv'
        res = self.db.export_history_csv(str(outpath))
        self.assertTrue(res and Path(res).exists())

if __name__ == '__main__':
    unittest.main()
