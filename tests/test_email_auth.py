import os
import shutil
import unittest

from services import auth, email


class TestEmailAuth(unittest.TestCase):
    def setUp(self):
        # ensure config dir is clean for tests
        cfg = os.path.join(os.path.dirname(__file__), '..', 'config')
        cfg = os.path.normpath(cfg)
        if os.path.exists(cfg):
            # remove only admins.txt if present to avoid disturbing other configs
            p = os.path.join(cfg, 'admins.txt')
            if os.path.exists(p):
                os.remove(p)

    def test_send_email_without_smtp_env(self):
        # Ensure SMTP env vars unset
        os.environ.pop('SMTP_HOST', None)
        os.environ.pop('SMTP_PORT', None)
        ok = email.send_email_smtp('x@example.com', 'subj', 'body')
        self.assertFalse(ok)

    def test_magic_link_flow(self):
        # create a magic link and consume it
        res = auth.initiate_magic_link('tester@example.com', host='http://localhost:8501')
        self.assertTrue(res.get('ok'))
        token = res.get('token')
        self.assertTrue(token)
        v = auth.verify_magic_link(token)
        self.assertTrue(v.get('ok'))
        sid = v.get('session_id')
        user = v.get('user')
        self.assertTrue(sid)
        self.assertEqual(user, 'tester@example.com')
        # verify session lookup
        got = auth.get_user_from_session(sid)
        self.assertEqual(got, 'tester@example.com')

    def tearDown(self):
        # remove config admins file if created
        cfg = os.path.join(os.path.dirname(__file__), '..', 'config')
        p = os.path.normpath(os.path.join(cfg, 'admins.txt'))
        if os.path.exists(p):
            os.remove(p)


if __name__ == '__main__':
    unittest.main()
