import os
import unittest
from pathlib import Path
from unittest.mock import patch

from services import auth


class TestAuthAdminFile(unittest.TestCase):
    def setUp(self):
        self.config_dir = Path(__file__).parent.parent / 'config'
        self.admin_file = self.config_dir / 'admins.txt'
        if self.admin_file.exists():
            self.admin_file.unlink()

    def tearDown(self):
        if self.admin_file.exists():
            self.admin_file.unlink()

    def test_add_and_remove_admin(self):
        with patch('services.db.add_admin_db', side_effect=Exception('no db')):
            with patch('services.db.remove_admin_db', side_effect=Exception('no db')):
                with patch('services.db.list_admins_db', side_effect=Exception('no db')):
                    self.assertTrue(auth.add_admin('new_admin'))
                    self.assertIn('new_admin', auth.load_admins())
                    self.assertTrue(auth.remove_admin('new_admin'))
                    self.assertNotIn('new_admin', auth.load_admins())

    def test_remove_missing_admin(self):
        if self.admin_file.exists():
            self.admin_file.unlink()
        self.assertFalse(auth.remove_admin('missing'))

    def test_load_admins_default(self):
        if self.admin_file.exists():
            self.admin_file.unlink()
        self.assertEqual(auth.load_admins(), ['admin'])


if __name__ == '__main__':
    unittest.main()
