import html
import importlib
import os
import re
import unittest
from unittest import mock


os.environ["MISSION_ENV"] = "development"
os.environ["MISSION_CAS_ENABLED"] = "false"

serveur = importlib.import_module("serveur")


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = serveur.app.test_client()

    def build_mission_payload(self, **overrides):
        payload = {
            "NOM": "Durand",
            "PRENOM": "Alice",
            "DATE_AJD": "1712563200000",
            "NOM_MISSION": "Mission test",
            "MISSION": "FRANCE",
            "pays": "",
            "FRAIS": "AVEC",
            "D_DEPART": "22/04/2026",
            "H_DEPART": "09:00",
            "D_RETOUR": "22/04/2026",
            "H_RETOUR": "18:00",
            "TRANSPORT": "TRAIN",
            "LIEU": "IUT Bordeaux Gradignan",
            "CODE_PTL": "33170",
            "VILLE": "Gradignan",
            "HOTEL": "NON",
            "PTDEJ": "NON",
            "QUILL": "<p>Mission</p>",
        }
        payload.update(overrides)
        return payload

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

    def test_create_mission_form_marks_address_fields_as_required_for_france(self):
        response = self.client.get("/mission/create_mission", follow_redirects=False)
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertRegex(html, re.compile(r'name="LIEU"[^>]*required', re.IGNORECASE))
        self.assertRegex(html, re.compile(r'name="CODE_PTL"[^>]*required', re.IGNORECASE))
        self.assertRegex(html, re.compile(r'name="VILLE"[^>]*required', re.IGNORECASE))

    def test_create_mission_rejects_missing_postal_code_for_french_mission(self):
        with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db:
            response = self.client.post(
                "/mission/create_mission",
                data=self.build_mission_payload(CODE_PTL=""),
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Le code postal est obligatoire", response.get_data(as_text=True))
        connect_db.assert_not_called()

    def test_create_mission_rejects_missing_country_for_foreign_mission(self):
        with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db:
            response = self.client.post(
                "/mission/create_mission",
                data=self.build_mission_payload(MISSION="AUTRE", pays="", CODE_PTL=""),
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Le pays est obligatoire", response.get_data(as_text=True))
        connect_db.assert_not_called()

    def test_create_mission_rejects_missing_identity_fields(self):
        cases = (
            ("PRENOM", "Le prenom est obligatoire"),
            ("NOM", "Le nom est obligatoire"),
            ("NOM_MISSION", "Le nom de la mission est obligatoire"),
        )

        for field_name, expected_message in cases:
            with self.subTest(field_name=field_name):
                with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db:
                    response = self.client.post(
                        "/mission/create_mission",
                        data=self.build_mission_payload(**{field_name: ""}),
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_message, html.unescape(response.get_data(as_text=True)))
                connect_db.assert_not_called()

    def test_create_mission_rejects_missing_datetime_fields(self):
        cases = (
            ("DATE_AJD", "La date de creation est obligatoire"),
            ("D_DEPART", "La date de depart est obligatoire"),
            ("H_DEPART", "L'heure de depart est obligatoire"),
            ("D_RETOUR", "La date de retour est obligatoire"),
            ("H_RETOUR", "L'heure de retour est obligatoire"),
        )

        for field_name, expected_message in cases:
            with self.subTest(field_name=field_name):
                with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db:
                    response = self.client.post(
                        "/mission/create_mission",
                        data=self.build_mission_payload(**{field_name: ""}),
                        follow_redirects=False,
                    )

                self.assertEqual(response.status_code, 400)
                self.assertIn(expected_message, html.unescape(response.get_data(as_text=True)))
                connect_db.assert_not_called()


if __name__ == "__main__":
    unittest.main()
