from datetime import datetime
from uuid import uuid4
from flask import Flask, abort, redirect, render_template, request, session, url_for,jsonify
import requests as REQ
import flask
import mariadb
import smtplib
import os

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart
    
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


APP_ENV = os.getenv("MISSION_ENV", "development").strip().lower()
IS_PRODUCTION = APP_ENV == "production"
SECRET_KEY = os.getenv("MISSION_SECRET_KEY")
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError("MISSION_SECRET_KEY est obligatoire en production.")

app.secret_key = SECRET_KEY or 'CECIESTLACLEFSECRETDEGEII'
app.config.update(
    TEMPLATES_AUTO_RELOAD=not IS_PRODUCTION,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE=os.getenv("MISSION_SESSION_COOKIE_SAMESITE", "Lax"),
    SESSION_COOKIE_SECURE=env_flag("MISSION_SESSION_COOKIE_SECURE", IS_PRODUCTION),
)
           
oauth_user = dict()#
### Structure ####
### {[0] login     : login gen a la connection validé par le CAS,
#    [1] nom  : nom recup via le CAS,
#    [2] status : Privilege de l'utilisateur "BASIC" "ADMIN" "GESTION"
#}

LOCAL_USER = (
    os.getenv("MISSION_LOCAL_USER_LOGIN", "localdev"),
    os.getenv("MISSION_LOCAL_USER_NAME", "Utilisateur local"),
    os.getenv("MISSION_LOCAL_USER_ROLE", "ADMIN" if not IS_PRODUCTION else "BASIC"),
)

admin_user = {"wprivat":"ADMIN",
              "vgalland":"GESTION"}
### Activate CAS oauth ###
CAS = env_flag("MISSION_CAS_ENABLED", IS_PRODUCTION)
##########################
DEV_MODE = env_flag("MISSION_DEV_MODE", (not CAS) and (not IS_PRODUCTION))
if IS_PRODUCTION and DEV_MODE:
    raise RuntimeError("MISSION_DEV_MODE doit etre desactive en production.")
if IS_PRODUCTION and not CAS:
    raise RuntimeError("MISSION_CAS_ENABLED doit etre active en production.")

CAS_BASE_URL = os.getenv("MISSION_CAS_BASE_URL", "https://cas.u-bordeaux.fr/cas").rstrip("/")
PUBLIC_BASE_URL = os.getenv("MISSION_PUBLIC_BASE_URL", "").rstrip("/")
MISSION_DB_CONFIG = {
    "host": os.getenv("MISSION_DB_HOST", "localhost"),
    "port": env_int("MISSION_DB_PORT", 3306),
    "user": os.getenv("MISSION_DB_USER", "mission"),
    "password": os.getenv("MISSION_DB_PASSWORD", ""),
    "database": os.getenv("MISSION_DB_NAME", "mission"),
}
CAS_DB_CONFIG = {
    "host": os.getenv("MISSION_CAS_DB_HOST", MISSION_DB_CONFIG["host"]),
    "port": env_int("MISSION_CAS_DB_PORT", MISSION_DB_CONFIG["port"]),
    "user": os.getenv("MISSION_CAS_DB_USER", MISSION_DB_CONFIG["user"]),
    "password": os.getenv("MISSION_CAS_DB_PASSWORD", MISSION_DB_CONFIG["password"]),
    "database": os.getenv("MISSION_CAS_DB_NAME", "db_cas"),
}
MAIL_SENDER = os.getenv("MISSION_MAIL_SENDER", "serveur.mission.geii@gmail.com")
MAIL_RECEIVER = os.getenv("MISSION_MAIL_RECEIVER", "valerie.galland@u-bordeaux.fr")
MAIL_SMTP_HOST = os.getenv("MISSION_SMTP_HOST", "smtpauth.u-bordeaux.fr")
MAIL_SMTP_PORT = env_int("MISSION_SMTP_PORT", 587)

if IS_PRODUCTION and not MISSION_DB_CONFIG["password"]:
    raise RuntimeError("MISSION_DB_PASSWORD est obligatoire en production.")
if IS_PRODUCTION and not CAS_DB_CONFIG["password"]:
    raise RuntimeError("MISSION_CAS_DB_PASSWORD est obligatoire en production.")

DB_UNAVAILABLE_TEXT = "Connexion a la base de donnees impossible. Verifie que MariaDB est demarre sur localhost:3306."


class DatabaseUnavailableError(Exception):
    pass


def db_unavailable_response(message=DB_UNAVAILABLE_TEXT):
    return render_template(
        '403.html',
        page_title='Service indisponible',
        page_nav_context='Service indisponible',
        error_code='Erreur 503',
        error_title='Base de donnees indisponible',
        error_copy=message
    ), 503


def public_url(path, request_context=None):
    base_url = PUBLIC_BASE_URL
    if not base_url and request_context is not None:
        base_url = request_context.host_url.rstrip("/")
    if not base_url:
        base_url = f"http://localhost:{env_int('PORT', 6969)}"
    return f"{base_url.rstrip('/')}{path}"


def _timestamp_ms(year, month, day, hour=9, minute=0):
    return int(datetime(year, month, day, hour, minute).timestamp() * 1000)


DEV_ORDER_MISSIONS = {
    "DEV-1001": (
        "DEV-1001", "Lefevre", "Camille", _timestamp_ms(2026, 4, 7, 9, 10),
        "Forum pedagogique GEII", "FRANCE", "AVEC",
        "18/04/2026", "08:30", "18/04/2026", "18:15",
        "TRAIN", "IUT Bordeaux Gradignan", "33170", "Gradignan",
        "NON", "NON",
        "<p>Presentation du departement et echanges avec les partenaires industriels.</p>"
    ),
    "DEV-1002": (
        "DEV-1002", "Martin", "Julie", _timestamp_ms(2026, 4, 6, 14, 20),
        "Visite de laboratoire", "FRANCE", "SANS",
        "22/04/2026", "07:45", "22/04/2026", "19:00",
        "V_PERSO", "Campus Talence", "33400", "Talence",
        "NON", "NON",
        "<p>Deplacement sur une journee pour une visite technique et une reunion de coordination.</p>"
    ),
    "DEV-1003": (
        "DEV-1003", "Bernard", "Nina", _timestamp_ms(2026, 4, 5, 11, 35),
        "Seminaire europeen", "BELGIQUE", "AVEC",
        "12/05/2026", "06:20", "14/05/2026", "21:10",
        "AVION", "ULB Solbosch", "", "Bruxelles",
        "OUI", "OUI",
        "<p>Participation a un seminaire europeen avec restitution et prise de contact pour un futur partenariat.</p>"
    ),
    "DEV-1004": (
        "DEV-1004", "Durand", "Alexis", _timestamp_ms(2026, 4, 4, 8, 45),
        "Intervention entreprise", "FRANCE", "AVEC",
        "05/05/2026", "09:00", "05/05/2026", "17:30",
        "V_UB", "MecaTech", "33700", "Merignac",
        "NON", "NON",
        "<p>Intervention sur site pour presenter les projets tutores et visiter l'atelier de production.</p>"
    ),
    "DEV-1005": (
        "DEV-1005", "Rousseau", "Emma", _timestamp_ms(2026, 4, 3, 16, 5),
        "Colloque national", "FRANCE", "SANS",
        "28/05/2026", "10:10", "30/05/2026", "16:40",
        "TRAIN", "Palais des congres", "44000", "Nantes",
        "OUI", "NON",
        "<p>Participation au colloque national avec session poster et rendez-vous institutionnels.</p>"
    ),
    "DEV-1006": (
        "DEV-1006", "Petit", "Lucas", _timestamp_ms(2026, 4, 2, 10, 55),
        "Reunion de projet", "ESPAGNE", "AVEC",
        "09/06/2026", "05:55", "10/06/2026", "23:10",
        "AVION", "Universitat Politecnica", "", "Valence",
        "OUI", "OUI",
        "<p>Reunion de lancement d'un projet pedagogique international et cadrage du planning.</p>"
    ),
}

DEV_TRACKING_MISSIONS = [
    ("DEV-1001", "localdev", "Camille Lefevre", "Forum pedagogique GEII", _timestamp_ms(2026, 4, 7, 9, 10), 0),
    ("DEV-1002", "localdev", "Julie Martin", "Visite de laboratoire", _timestamp_ms(2026, 4, 6, 14, 20), 1),
    ("DEV-1003", "localdev", "Nina Bernard", "Seminaire europeen", _timestamp_ms(2026, 4, 5, 11, 35), 2),
    ("DEV-1004", "localdev", "Alexis Durand", "Intervention entreprise", _timestamp_ms(2026, 4, 4, 8, 45), 0),
    ("DEV-1005", "localdev", "Emma Rousseau", "Colloque national", _timestamp_ms(2026, 4, 3, 16, 5), 3),
    ("DEV-1006", "localdev", "Lucas Petit", "Reunion de projet", _timestamp_ms(2026, 4, 2, 10, 55), 1),
]

DEV_TRACKING_INDEX = {mission[0]: mission for mission in DEV_TRACKING_MISSIONS}
MISSION_STATUS_LABELS = ["Ouvert", "En cours de validation", "Validé", "Cloturé"]


def is_admin_user(data):
    return data[2] in ("ADMIN", "GESTION")


def empty_mission_values():
    return {
        "ID": "",
        "NOM": "",
        "PRENOM": "",
        "DATE_AJD": "",
        "NOM_MISSION": "",
        "MISSION": "FRANCE",
        "pays": "",
        "FRAIS": "SANS",
        "D_DEPART": "",
        "H_DEPART": "",
        "D_RETOUR": "",
        "H_RETOUR": "",
        "TRANSPORT": "V_PERSO",
        "LIEU": "",
        "CODE_PTL": "",
        "VILLE": "",
        "HOTEL": "NON",
        "PTDEJ": "NON",
        "QUILL": "",
    }


def mission_values_from_record(record):
    values = empty_mission_values()
    if record is None:
        return values

    country = (record[5] or "").strip()
    is_france = country == "FRANCE"
    values.update({
        "ID": str(record[0] or ""),
        "NOM": record[1] or "",
        "PRENOM": record[2] or "",
        "DATE_AJD": str(record[3] or ""),
        "NOM_MISSION": record[4] or "",
        "MISSION": "FRANCE" if is_france else "AUTRE",
        "pays": "" if is_france else country,
        "FRAIS": record[6] or "SANS",
        "D_DEPART": record[7] or "",
        "H_DEPART": record[8] or "",
        "D_RETOUR": record[9] or "",
        "H_RETOUR": record[10] or "",
        "TRANSPORT": record[11] or "V_PERSO",
        "LIEU": record[12] or "",
        "CODE_PTL": record[13] or "",
        "VILLE": record[14] or "",
        "HOTEL": record[15] or "NON",
        "PTDEJ": record[16] or "NON",
        "QUILL": record[17] or "",
    })
    return values


def sort_tracking_missions(missions):
    return sorted(missions, key=lambda mission: int(mission[4]), reverse=True)


def render_mission_form(page_mode, admin=False, mission_values=None, can_edit_mission=True, show_admin_panel=False, detail_id=None, detail_stat=0):
    return render_template(
        'new_order.html',
        ADMIN=admin,
        page_mode=page_mode,
        mission_values=mission_values or empty_mission_values(),
        can_edit_mission=can_edit_mission,
        show_admin_panel=show_admin_panel,
        detail_id=detail_id,
        detail_stat=detail_stat
    )

@app.route("/mission/", methods=['GET'])
def index():
    if CAS:
        if request.cookies.get("SESSID") != None:
            if request.cookies.get("SESSID") in oauth_user.keys() :
                return render_template('index.html')
            else:
                return redirect("/mission/oauth")
        else:
            return redirect("/mission/oauth")
    else:
        return render_template('index.html')

#################################

@app.route("/mission/oauth/")
def oauth():
    service_url = public_url("/mission/oauth", request)
    if 'ticket' in request.values:
        PARAMS = {"ticket":request.values['ticket'],
                  'service':service_url}
        
        

        RESP = REQ.get(url = f"{CAS_BASE_URL}/serviceValidate",params=PARAMS)
        if "authenticationSuccess" in str(RESP.content):
            id = str(RESP.content).split('cas:user')[1].removeprefix('>').removesuffix("</")
            try:
                DB = connect_to_DB_cas()
                cur = DB.cursor()
                cur.execute("SELECT nom FROM personnels WHERE login = %s", (id,))
                login = str(cur.fetchone()[0])
            except (DatabaseUnavailableError, mariadb.Error):
                return db_unavailable_response()
            
            ##print(f" {DB.user} | Login {data}")

            if login != None: # Verif si user autorised sinon 403 list(cur.execute("SELECT ID FROM "))
                if id in oauth_user.items(): #Verif si user deja un SESSID
                    key = {i for i in oauth_user if oauth_user[i]==id}
                    oauth_user.pop(key)

                SESSID = uuid4().int.__str__()[:10]
                status = admin_user.get(id,"BASIC")
                oauth_user[SESSID] = [id,login,status]
                ##print(oauth_user[SESSID])
                resp = flask.make_response(redirect("/mission"))  
                resp.set_cookie("SESSID", value = SESSID)

                ##print(f"USER {id} authorized with {status} authority")
            else:return abort(403)
                
            return resp
        else:
            return redirect(f"{CAS_BASE_URL}/login?service={service_url}")
    else:
        return redirect(f"{CAS_BASE_URL}/login?service={service_url}")


@app.route("/mission/create_mission", methods=['GET'])
def ordre():
    data = Verif_Connection(request)
    ADMIN = is_admin_user(data)
    return render_mission_form(
        page_mode='create',
        admin=ADMIN,
        mission_values=empty_mission_values(),
        can_edit_mission=True,
        show_admin_panel=False
    )

#################################

@app.route("/mission/view_mission", methods=['GET']) # type: ignore
def view():
    data = Verif_Connection(request)
    ADMIN = is_admin_user(data)
    if DEV_MODE:
        all_user = sorted({mission[2] for mission in DEV_TRACKING_MISSIONS}) if ADMIN else None
        return render_template('view.html', Missions=sort_tracking_missions(DEV_TRACKING_MISSIONS), ADMIN=ADMIN, All_User=all_user)
    try:
        DB = connect_to_DB_mission()
        cur = DB.cursor()

        if data[2] == "BASIC":
            cur.execute(f"SELECT * FROM suivi_mission WHERE ID_USER = '{data[0]}'")
            mission = sort_tracking_missions(list(cur.fetchall()))
            return render_template('view.html', Missions=mission , ADMIN=ADMIN)
        elif data[2] == "ADMIN" or data[2] == "GESTION":
            DB_CAS= connect_to_DB_cas()
            cur_cas = DB_CAS.cursor()
            cur.execute(f"SELECT * FROM suivi_mission")
            mission = sort_tracking_missions(list(cur.fetchall()))
            cur.execute(f"SELECT DISTINCT ID_USER FROM suivi_mission")
            users = tuple(item[0] for item in cur.fetchall())
            cur_cas.execute(f"SELECT nom FROM personnels WHERE login IN {users}")
            all_user = list(item[0] for item in cur_cas.fetchall())
            ADMIN = True
            return render_template('view.html', Missions=mission , ADMIN=ADMIN, All_User=all_user)
    except (DatabaseUnavailableError, mariadb.Error):
        return db_unavailable_response()

#################################
@app.route("/mission/view_mission/<id_mission>", methods=['GET'])
def show_mission(id_mission):
    data = Verif_Connection(request)
    ADMIN = is_admin_user(data)
    if DEV_MODE and id_mission in DEV_ORDER_MISSIONS:
        tracking = DEV_TRACKING_INDEX[id_mission]
        return render_mission_form(
            page_mode='detail',
            admin=ADMIN,
            mission_values=mission_values_from_record(DEV_ORDER_MISSIONS[id_mission]),
            can_edit_mission=ADMIN,
            show_admin_panel=ADMIN,
            detail_id=id_mission,
            detail_stat=tracking[5]
        )
    try:
        DB = connect_to_DB_mission()
        cur = DB.cursor()
        cur.execute("SELECT ID_USER , STATUE FROM suivi_mission WHERE ID = %s", (id_mission,))
        dimitri = cur.fetchone()
        if dimitri is None:
            return abort(404)
        user = dimitri[0]
        BOB = dimitri[1]
        if ADMIN or data[0] == user:
            cur.execute("SELECT * FROM ordre_mission WHERE ID = %s", (id_mission,))
            mission = cur.fetchone()
            if mission is None:
                return abort(404)
            return render_mission_form(
                page_mode='detail',
                admin=ADMIN,
                mission_values=mission_values_from_record(mission),
                can_edit_mission=ADMIN,
                show_admin_panel=ADMIN,
                detail_id=id_mission,
                detail_stat=BOB
            )
        else:
            print(f'Connection refusé to {data[1]}')
            return abort(403)
    except (DatabaseUnavailableError, mariadb.Error):
        return db_unavailable_response()

@app.route("/mission/view_mission/<id_mission>",methods=['POST'])
def upstatmiss_mission(id_mission):
    data = Verif_Connection(request)
    ADMIN = is_admin_user(data)
    form_action = request.form.get('FORM_ACTION', 'admin_status')
    if DEV_MODE and id_mission in DEV_ORDER_MISSIONS:
        if not ADMIN:
            return abort(403)
        if form_action == 'update_mission':
            return redirect(url_for('show_mission', id_mission=id_mission))
        return redirect(url_for('view'))
    try:
        DB = connect_to_DB_mission()
        cur = DB.cursor()
        cur.execute("SELECT ID_USER FROM suivi_mission WHERE ID = %s", (id_mission,))
        tracking = cur.fetchone()
        if tracking is None:
            return abort(404)

        if form_action == 'update_mission':
            if not ADMIN:
                return abort(403)

            val = request.values
            country = "FRANCE" if val["MISSION"] == "FRANCE" else val["pays"]
            cur.execute(
                "UPDATE mission.ordre_mission SET NOM=%s, PRENOM=%s, DATE_AJD=%s, NOM_MISSION=%s, PAYS_MISSION=%s, FRAIS=%s, D_DEPART=%s, H_DEPART=%s, D_RETOUR=%s, H_RETOUR=%s, TRANSPORT=%s, LIEU=%s, CODE_PTL=%s, VILLE=%s, HOTEL=%s, PTDEJ=%s, QUILL=%s WHERE ID=%s",
                (
                    val["NOM"], val["PRENOM"], val["DATE_AJD"], val["NOM_MISSION"], country, val["FRAIS"],
                    val["D_DEPART"], val["H_DEPART"], val["D_RETOUR"], val["H_RETOUR"], val["TRANSPORT"],
                    val["LIEU"], val["CODE_PTL"], val["VILLE"], val["HOTEL"], val["PTDEJ"], val["QUILL"], id_mission
                )
            )
            cur.execute(
                "UPDATE mission.suivi_mission SET NOM_MISSION=%s WHERE ID=%s",
                (val["NOM_MISSION"], id_mission)
            )
            return redirect(url_for('show_mission', id_mission=id_mission))

        if not ADMIN:
            return abort(403)

        val = MISSION_STATUS_LABELS.index(request.form.get('STAT')) # type: ignore
        cur.execute("UPDATE mission.suivi_mission SET STATUE=%s WHERE ID=%s", (val, id_mission))
        if request.form.get('DEL') == "on":
            cur.execute("DELETE FROM mission.ordre_mission WHERE ID=%s", (id_mission,))
            cur.execute("DELETE FROM mission.suivi_mission WHERE ID=%s", (id_mission,))

            print(f"DELETE {id_mission}")

        return redirect(url_for('view'))
    except (DatabaseUnavailableError, mariadb.Error):
        return db_unavailable_response()
#################################
@app.route("/mission/create_mission", methods=['POST'])
def create_new_mission():
    data = Verif_Connection(request)

    #for value in request.values:
        #print(f"{value} | {request.values[value]} | {type(request.values[value])}")
    val = request.values
    try:
        DB = connect_to_DB_mission()
        cur = DB.cursor()
        ID = new_ID()
        user_id = data[0]
        nom = data[1]
        if val['MISSION'] == "FRANCE":
            PAYS = "FRANCE"
        else:
            PAYS = val["pays"]

        cur.execute("INSERT INTO mission.ordre_mission(ID,NOM,PRENOM,DATE_AJD,NOM_MISSION,PAYS_MISSION,FRAIS,D_DEPART,H_DEPART,D_RETOUR,H_RETOUR,TRANSPORT,LIEU,CODE_PTL,VILLE,HOTEL,PTDEJ,QUILL) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(ID.__repr__(),val["NOM"],val["PRENOM"],val["DATE_AJD"],val["NOM_MISSION"],PAYS,val["FRAIS"],val["D_DEPART"],val["H_DEPART"],val["D_RETOUR"],val["H_RETOUR"],val["TRANSPORT"],val["LIEU"],val["CODE_PTL"],val["VILLE"],val["HOTEL"],val["PTDEJ"],val["QUILL"]))
        statu_crea = 0
        cur.execute("INSERT INTO mission.suivi_mission(ID,ID_USER,NAME,NOM_MISSION,DATE_CREA,STATUE) VALUES (%s,%s,%s,%s,%s,%d)",(ID,user_id,nom,val["NOM_MISSION"],val["DATE_AJD"],statu_crea))

        Send_Mail_NM(ID.__repr__(),val["NOM"],val["PRENOM"],val["DATE_AJD"],val["NOM_MISSION"],PAYS,val["FRAIS"],val["D_DEPART"],val["H_DEPART"],val["D_RETOUR"],val["H_RETOUR"],val["TRANSPORT"],val["LIEU"],val["CODE_PTL"],val["VILLE"],val["HOTEL"],val["PTDEJ"],val["QUILL"])
        ##print(f"Ordre mission {ID} success")
    except (DatabaseUnavailableError, mariadb.Error):
        return db_unavailable_response()

    return redirect("/mission/")

#################################

@app.route("/mission/DB")
def DBConnect():
    try:
        DB = connect_to_DB_mission()
        #print(DB)
    except (DatabaseUnavailableError, mariadb.Error):
        return db_unavailable_response()
    return "<html><body> <h1>  DB  </h1></body></html>"

#################################

@app.route("/mission/who_is_loged")
def WHO_IS():
    ID = request.cookies.get('SESSID')
    name = Verif_Connection(request)
    return f"<html><body> <h1>  {name} with key {ID}  </h1></body></html>"

def new_ID():
    import uuid
    ID = uuid.uuid4().int
    return int(ID.__str__()[:10])


#################################
#################################
#################################

def connect_to_DB_mission():
    try:
        DB = mariadb.connect(
            host=MISSION_DB_CONFIG["host"],
            port=MISSION_DB_CONFIG["port"],
            user=MISSION_DB_CONFIG["user"],
            password=MISSION_DB_CONFIG["password"],
            database=MISSION_DB_CONFIG["database"],
            autocommit=True
        )
        DB.autocommit = True
        return DB
    except mariadb.Error as e:
        raise DatabaseUnavailableError(f"Error connecting to the database: {e}")
    
def connect_to_DB_cas():
    try:
        DB = mariadb.connect(
            host=CAS_DB_CONFIG["host"],
            port=CAS_DB_CONFIG["port"],
            user=CAS_DB_CONFIG["user"],
            password=CAS_DB_CONFIG["password"],
            database=CAS_DB_CONFIG["database"],
            autocommit=True
        )
        DB.autocommit = True
        return DB
    except mariadb.Error as e:
        raise DatabaseUnavailableError(f"Error connecting to the database: {e}")

def Verif_Connection(request):
    session_id = request.cookies.get("SESSID", None)
    data = oauth_user.get(session_id, None)
    if data is not None:
        return data
    if CAS == True:
        abort(403)
    return LOCAL_USER

def Send_Mail_NM(*data):
    
    # Informations de connexion et de l'expéditeur
    sender_email = MAIL_SENDER
    receiver_email = MAIL_RECEIVER

    # Configuration du message
    subject = f"Nouvelle demande de mission"

    if data[11] == "V_PERSO":vehicule="Véhicule personnel"
    elif data[11] == "V_UB":vehicule="Véhicule de l'université"
    else:
        vehicule = data[11]

    date = datetime.fromtimestamp(int(data[3])/1000).strftime("%Y-%m-%d %H:%M:%S")
    mission_url = public_url(f"/mission/view_mission/{data[0]}")
    body=f"""
<div>Hey, Valérie <br><br>Une nouvelle demande de mission: 
<a href="{mission_url}" target="_blank" rel="noopener" data-mce-href="{mission_url}" data-mce-selected="inline-boundary">{data[0]} </a><br></div><div><br data-mce-bogus=3D"1"></div>
<div>Demandeur: {data[1]} {data[2]} le {date}<br data-mce-bogus=3D"1"></div>
<div>Intitulé de mission: {data[4]}<br data-mce-bogus=3D"1"></div>
<div>Date de départ: le {data[7]} {data[8]}<br data-mce-bogus=3D"1"></div><div>Date de retour: le {data[9]} {data[10]}</div>
<div>Lieu du déplacement: {data[12]} {data[13]} {data[14]} {data[5]}<br data-mce-bogus=3D"1"></div>
<div>Frais ? : {data[6]}<br data-mce-bogus=3D"1"></div>
<div>Moyen de Transport: {vehicule}<br data-mce-bogus=3D"1"></div>
<div>Hôtel?: {data[15]}</div>
<div>Petit déjeuner: {data[16]}<br data-mce-bogus=3D"1"></div><div><br data-mce-bogus=3D"1"></div>
<div>@+<br data-mce-bogus=3D"1"></div>"""

    # Création de l'objet message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Ajout du corps de texte
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP(MAIL_SMTP_HOST, MAIL_SMTP_PORT) as server:
            server.starttls()  # Sécurise la connexion
            server.sendmail(sender_email, receiver_email, message.as_string())
            #print("Email envoyé avec succès")
    except Exception as e:
        #print(f"Erreur lors de l'envoi de l'email : {e}")
        e=0
#################################

@app.errorhandler(403)
def access_denied(e):
    # note that we set the 403 status explicitly
    return render_template('403.html'), 403

# Running the API
if __name__ == "__main__":
    with app.app_context():
        #for rule in app.url_map.iter_rules():
    	    #print(f"{rule.endpoint}: {rule.methods} - {rule}")
        app.run(
            host=os.getenv("MISSION_HOST", "0.0.0.0" if IS_PRODUCTION else "127.0.0.1"),
            port=env_int("PORT", 6969),
            debug=env_flag("MISSION_DEBUG", not IS_PRODUCTION)
        )
