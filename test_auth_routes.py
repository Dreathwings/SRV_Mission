import html
import importlib
import os
import re
import unittest
import copy
from datetime import datetime
from unittest import mock


os.environ["MISSION_ENV"] = "development"
os.environ["MISSION_CAS_ENABLED"] = "false"

serveur = importlib.import_module("serveur")


class FakeMissionCursor:
    def __init__(self, db):
        self.db = db
        self._fetchone = None
        self._fetchall = []

    def execute(self, query, params=None):
        normalized_query = " ".join(query.split())
        self.db.executed_queries.append((normalized_query, params))
        self._fetchone = None
        self._fetchall = []

        if normalized_query.startswith("SELECT setting_value FROM mission.admin_settings"):
            value = self.db.settings.get(params[0])
            self._fetchone = (value,) if value is not None else None
            return

        if normalized_query == "SELECT login, role FROM mission.admin_roles":
            self._fetchall = [(login, role) for login, role in self.db.roles.items()]
            return

        if normalized_query.startswith("SELECT role FROM mission.admin_roles WHERE login = %s"):
            role = self.db.roles.get(params[0])
            self._fetchone = (role,) if role is not None else None
            return

        if normalized_query.startswith("INSERT INTO mission.admin_settings(setting_key, setting_value, updated_at)"):
            self.db.settings[params[0]] = params[1]
            return

        if normalized_query.startswith("INSERT INTO mission.admin_roles(login, role, updated_at)"):
            self.db.roles[params[0]] = params[1]
            return

        if normalized_query.startswith("DELETE FROM mission.admin_roles WHERE login = %s"):
            self.db.roles.pop(params[0], None)
            return

        if normalized_query.startswith("SELECT suivi_mission.ID, suivi_mission.NOM_MISSION, ordre_mission.D_RETOUR, ordre_mission.H_RETOUR FROM mission.suivi_mission"):
            closed_status = params[0]
            self._fetchall = [
                (row["id"], row["mission_name"], row["return_date"], row["return_time"])
                for row in self.db.autoclose_rows
                if row["status"] != closed_status
            ]
            return

        if normalized_query.startswith("UPDATE mission.suivi_mission SET STATUE=%s WHERE ID=%s"):
            new_status, mission_id = params
            self.db.updated_statuses.append((mission_id, new_status))
            for row in self.db.autoclose_rows:
                if row["id"] == mission_id:
                    row["status"] = new_status
            return

        if normalized_query.startswith("INSERT INTO mission.ordre_mission"):
            self.db.inserted_orders.append(params)
            return

        if normalized_query.startswith("INSERT INTO mission.suivi_mission"):
            self.db.inserted_tracking.append(params)
            return

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return list(self._fetchall)


class FakeMissionDB:
    def __init__(self, settings=None, autoclose_rows=None, roles=None):
        self.settings = dict(settings or {})
        self.roles = dict(roles or {})
        self.autoclose_rows = [
            {
                "id": row[0],
                "mission_name": row[1],
                "return_date": row[2],
                "return_time": row[3],
                "status": row[4],
            }
            for row in (autoclose_rows or [])
        ]
        self.executed_queries = []
        self.updated_statuses = []
        self.inserted_orders = []
        self.inserted_tracking = []

    def cursor(self):
        return FakeMissionCursor(self)


class FakeCasCursor:
    def __init__(self, db):
        self.db = db
        self._fetchall = []

    def execute(self, query, params=None):
        normalized_query = " ".join(query.split())
        self.db.executed_queries.append((normalized_query, params))
        self._fetchall = []

        if normalized_query == "SELECT login, nom FROM personnels ORDER BY nom, login":
            self._fetchall = list(self.db.users)

    def fetchall(self):
        return list(self._fetchall)


class FakeCasDB:
    def __init__(self, users=None):
        self.users = list(users or [])
        self.executed_queries = []

    def cursor(self):
        return FakeCasCursor(self)


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = serveur.app.test_client()
        self.original_dev_admin_state = copy.deepcopy(serveur.DEV_ADMIN_STATE)

    def tearDown(self):
        serveur.DEV_ADMIN_STATE.clear()
        serveur.DEV_ADMIN_STATE.update(copy.deepcopy(self.original_dev_admin_state))

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

    def test_admin_page_is_available_for_admin_users(self):
        with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db, \
             mock.patch.object(serveur, "connect_to_DB_cas") as connect_cas:
            response = self.client.get("/mission/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Destinataires email", html.unescape(response.get_data(as_text=True)))
        self.assertIn("Mode développement", html.unescape(response.get_data(as_text=True)))
        self.assertIn('name="recipient_email"', response.get_data(as_text=True))
        connect_db.assert_not_called()
        connect_cas.assert_not_called()

    def test_admin_page_rejects_basic_users(self):
        with self.client.session_transaction() as current_session:
            current_session["mission_user"] = ["basic", "Utilisateur basic", "BASIC"]

        with mock.patch.object(serveur, "connect_to_DB_mission") as connect_db:
            response = self.client.get("/mission/admin", follow_redirects=False)

        self.assertEqual(response.status_code, 403)
        connect_db.assert_not_called()

    def test_notification_recipients_fall_back_to_env_when_setting_missing(self):
        fake_db = FakeMissionDB()

        with mock.patch.object(serveur, "DEV_MODE", False):
            recipients = serveur.get_notification_recipients(fake_db)

        self.assertEqual(recipients, [serveur.MAIL_RECEIVER])

    def test_notification_recipients_validation_rejects_invalid_email(self):
        with self.assertRaisesRegex(ValueError, "Adresse email invalide"):
            serveur.normalize_notification_recipients("adresse-invalide")

    def test_notification_recipients_are_trimmed_deduplicated_and_saved(self):
        fake_db = FakeMissionDB()

        with mock.patch.object(serveur, "DEV_MODE", False):
            recipients, normalized_value = serveur.save_notification_recipients(
                fake_db,
                " alice@example.com \nALICE@example.com\nbob@example.com ",
            )

        self.assertEqual(
            recipients,
            [
                {"email": "alice@example.com", "enabled": True},
                {"email": "bob@example.com", "enabled": True},
            ],
        )
        self.assertEqual(
            normalized_value,
            '[{"email": "alice@example.com", "enabled": true}, {"email": "bob@example.com", "enabled": true}]',
        )
        self.assertEqual(
            fake_db.settings[serveur.ADMIN_SETTINGS_NOTIFICATION_RECIPIENTS],
            '[{"email": "alice@example.com", "enabled": true}, {"email": "bob@example.com", "enabled": true}]',
        )

    def test_notification_recipients_support_disabled_entries(self):
        fake_db = FakeMissionDB(
            settings={
                serveur.ADMIN_SETTINGS_NOTIFICATION_RECIPIENTS: '[{"email": "admin1@example.com", "enabled": true}, {"email": "admin2@example.com", "enabled": false}]'
            }
        )

        with mock.patch.object(serveur, "DEV_MODE", False):
            recipients = serveur.get_notification_recipients(fake_db)
            entries = serveur.get_notification_recipient_entries(fake_db)

        self.assertEqual(recipients, ["admin1@example.com"])
        self.assertEqual(
            entries,
            [
                {"email": "admin1@example.com", "enabled": True},
                {"email": "admin2@example.com", "enabled": False},
            ],
        )

    def test_create_mission_sends_email_to_configured_recipients(self):
        fake_db = FakeMissionDB(
            settings={
                serveur.ADMIN_SETTINGS_NOTIFICATION_RECIPIENTS: '[{"email": "admin1@example.com", "enabled": true}, {"email": "admin2@example.com", "enabled": false}, {"email": "admin3@example.com", "enabled": true}]'
            }
        )
        smtp_server = mock.MagicMock()
        smtp_context = mock.MagicMock()
        smtp_context.__enter__.return_value = smtp_server

        with mock.patch.object(serveur, "DEV_MODE", False), \
             mock.patch.object(serveur, "connect_to_DB_mission", return_value=fake_db), \
             mock.patch.object(serveur, "new_ID", return_value=1234567890), \
             mock.patch("serveur.smtplib.SMTP", return_value=smtp_context):
            response = self.client.post(
                "/mission/create_mission",
                data=self.build_mission_payload(),
                follow_redirects=False,
            )

        self.assertEqual(response.status_code, 302)
        smtp_server.starttls.assert_called_once()
        smtp_server.sendmail.assert_called_once()
        sendmail_args = smtp_server.sendmail.call_args.args
        self.assertEqual(sendmail_args[1], ["admin1@example.com", "admin3@example.com"])

    def test_autoclose_overdue_missions_closes_only_due_non_closed_missions(self):
        fake_db = FakeMissionDB(
            autoclose_rows=[
                ("MISSION-1", "Mission en retard", "01/04/2026", "08:00", 0),
                ("MISSION-2", "Mission future", "12/04/2026", "08:00", 1),
                ("MISSION-3", "Mission deja cloturee", "01/04/2026", "08:00", 3),
            ]
        )

        summary = serveur.autoclose_overdue_missions(
            fake_db,
            now=datetime(2026, 4, 8, 9, 0),
        )

        self.assertEqual(summary["closed_count"], 1)
        self.assertEqual(summary["missions"][0]["id"], "MISSION-1")
        self.assertEqual(fake_db.updated_statuses, [("MISSION-1", 3)])
        remaining_open_ids = {row["id"] for row in fake_db.autoclose_rows if row["status"] != 3}
        self.assertEqual(remaining_open_ids, {"MISSION-2"})

    def test_admin_autoclose_route_returns_summary(self):
        original_tracking = list(serveur.DEV_TRACKING_MISSIONS)
        original_index = dict(serveur.DEV_TRACKING_INDEX)
        original_order = dict(serveur.DEV_ORDER_MISSIONS)

        serveur.DEV_TRACKING_MISSIONS[:] = [
            ("MISSION-10", "localdev", "Alice Admin", "Mission cloturee par batch", serveur._timestamp_ms(2026, 4, 2, 10, 0), 2),
            ("MISSION-11", "localdev", "Alice Admin", "Mission a venir", serveur._timestamp_ms(2026, 4, 7, 10, 0), 1),
        ]
        serveur.DEV_TRACKING_INDEX.clear()
        for mission in serveur.DEV_TRACKING_MISSIONS:
            serveur.DEV_TRACKING_INDEX[mission[0]] = mission
        serveur.DEV_ORDER_MISSIONS["MISSION-10"] = (
            "MISSION-10", "Admin", "Alice", serveur._timestamp_ms(2026, 4, 2, 10, 0),
            "Mission cloturee par batch", "FRANCE", "SANS",
            "07/04/2026", "08:00", "07/04/2026", "10:00",
            "TRAIN", "Bordeaux", "33000", "Bordeaux",
            "NON", "NON", "<p>Test</p>"
        )
        serveur.DEV_ORDER_MISSIONS["MISSION-11"] = (
            "MISSION-11", "Admin", "Alice", serveur._timestamp_ms(2026, 4, 7, 10, 0),
            "Mission a venir", "FRANCE", "SANS",
            "12/04/2026", "08:00", "12/04/2026", "18:00",
            "TRAIN", "Bordeaux", "33000", "Bordeaux",
            "NON", "NON", "<p>Test</p>"
        )

        with mock.patch.object(serveur, "get_current_local_datetime", return_value=datetime(2026, 4, 8, 9, 0)):
            response = self.client.post(
                "/mission/admin",
                data={"FORM_ACTION": "run_autoclose"},
                follow_redirects=False,
            )

        serveur.DEV_TRACKING_MISSIONS[:] = original_tracking
        serveur.DEV_TRACKING_INDEX.clear()
        serveur.DEV_TRACKING_INDEX.update(original_index)
        serveur.DEV_ORDER_MISSIONS.clear()
        serveur.DEV_ORDER_MISSIONS.update(original_order)

        response_html = html.unescape(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertIn("1 mission(s)", response_html)
        self.assertIn("MISSION-10", response_html)

    def test_admin_role_changes_work_in_fake_dev_mode(self):
        response = self.client.post(
            "/mission/admin",
            data={"FORM_ACTION": "save_roles", "role__jmartin": "GESTION"},
            follow_redirects=False,
        )

        response_html = html.unescape(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertIn("1 autorisation(s) mise(s) à jour", response_html)
        self.assertEqual(serveur.DEV_ADMIN_STATE["user_roles"]["jmartin"], "GESTION")

    def test_admin_notification_changes_work_in_fake_dev_mode(self):
        response = self.client.post(
            "/mission/admin",
            data={
                "FORM_ACTION": "save_recipients",
                "recipient_email": ["alpha@example.com", "beta@example.com"],
                "recipient_enabled": ["1", "0"],
            },
            follow_redirects=False,
        )

        response_html = html.unescape(response.get_data(as_text=True))
        self.assertEqual(response.status_code, 200)
        self.assertIn("1 destinataire(s) actif(s) sur 2 enregistré(s).", response_html)
        self.assertEqual(
            serveur.DEV_ADMIN_STATE["notification_recipients"],
            [
                {"email": "alpha@example.com", "enabled": True},
                {"email": "beta@example.com", "enabled": False},
            ],
        )

    def test_list_cas_users_with_roles_uses_saved_overrides(self):
        fake_mission_db = FakeMissionDB(roles={"jmartin": "ADMIN"})
        fake_cas_db = FakeCasDB(
            users=[
                ("jmartin", "Julie Martin"),
                ("vgalland", "Valerie Galland"),
            ]
        )

        with mock.patch.object(serveur, "DEV_MODE", False):
            users = serveur.list_cas_users_with_roles(fake_cas_db, fake_mission_db)

        self.assertEqual(
            users,
            [
                {"login": "jmartin", "name": "Julie Martin", "role": "ADMIN"},
                {"login": "vgalland", "name": "Valerie Galland", "role": "GESTION"},
            ],
        )

    def test_save_user_roles_persists_only_overrides(self):
        fake_mission_db = FakeMissionDB(roles={"jmartin": "ADMIN", "wprivat": "BASIC"})

        with mock.patch.object(serveur, "DEV_MODE", False):
            updated_count = serveur.save_user_roles(
                fake_mission_db,
                {"jmartin": "BASIC", "wprivat": "ADMIN"},
                {"jmartin", "wprivat"},
            )

        self.assertEqual(updated_count, 2)
        self.assertEqual(fake_mission_db.roles, {})


if __name__ == "__main__":
    unittest.main()
