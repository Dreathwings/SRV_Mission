import importlib
import os
import unittest


os.environ["MISSION_ENV"] = "development"
os.environ["MISSION_CAS_ENABLED"] = "false"

serveur = importlib.import_module("serveur")


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = serveur.app.test_client()

    def test_index_without_trailing_slash_is_served_without_canonical_redirect(self):
        response = self.client.get("/mission", follow_redirects=False)

        self.assertEqual(response.status_code, 200)

    def test_oauth_without_trailing_slash_redirects_directly_to_cas(self):
        response = self.client.get("/mission/oauth", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?service=", response.headers["Location"])

    def test_oauth_with_trailing_slash_still_redirects_to_cas(self):
        response = self.client.get("/mission/oauth/", follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login?service=", response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
