import os
import unittest


class TestBasic(unittest.TestCase):
    def test_readme_exists(self):
        self.assertTrue(os.path.exists('README.md'))

    def test_requirements_exists(self):
        self.assertTrue(os.path.exists('requirements.txt'))


if __name__ == '__main__':
    unittest.main()
