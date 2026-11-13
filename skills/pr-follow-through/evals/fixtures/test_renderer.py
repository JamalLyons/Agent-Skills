import unittest

from renderer import greeting


class GreetingTests(unittest.TestCase):
    def test_english(self):
        self.assertEqual(greeting("en"), "Welcome")

    def test_french(self):
        self.assertEqual(greeting("fr"), "Bienvenue")


if __name__ == "__main__":
    unittest.main()
