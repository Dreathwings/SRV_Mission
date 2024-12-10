from uuid import uuid4
from flask import Flask, abort, redirect, render_template, request, session, url_for
import requests as REQ
import flask
import mariadb
import smtplib

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart
    
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.secret_key='CECIESTLACLEFSECRETDEGEII'
app.config.update(TEMPLATES_AUTO_RELOAD=True)
           
oauth_user = dict()#
### Structure ####
### {[0] login     : login gen a la connection validé par le CAS,
#    [1] nom  : nom recup via le CAS,
#    [2] status : Privilege de l'utilisateur "BASIC" "ADMIN" "GESTION"
#}


admin_user = {"wprivat":"ADMIN",
              "vgalland":"GESTION"}
### Activate CAS oauth ###
CAS = True
##########################

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
    if 'ticket' in request.values:
        PARAMS = {"ticket":request.values['ticket'],
                  'service':"http://geii.iut.u-bordeaux.fr/mission/oauth"}
        # #print(f"Ticket :{request.values['ticket']}")

        RESP = REQ.get(url = "https://cas.u-bordeaux.fr/cas/serviceValidate",params=PARAMS)
        if "authenticationSuccess" in str(RESP.content):
            id = str(RESP.content).split('cas:user')[1].removeprefix('>').removesuffix("</")

            DB = connect_to_DB_cas()
            
            cur = DB.cursor()
            cur.execute(f"SELECT nom FROM personnels WHERE login = '{id}' ")
            login = str(cur.fetchone()[0])
            
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
            return redirect("https://cas.u-bordeaux.fr/cas/login?service=http://geii.iut.u-bordeaux.fr/mission/oauth")
    else:
        return redirect("https://cas.u-bordeaux.fr/cas/login?service=http://geii.iut.u-bordeaux.fr/mission/oauth")


@app.route("/mission/create_mission", methods=['GET'])
def ordre():
    Verif_Connection(request)
    return render_template('new_order.html')

#################################

@app.route("/mission/view_mission", methods=['GET'])
def view():
    Verif_Connection(request)
    
    data = oauth_user[request.cookies.get("SESSID")]
    DB = connect_to_DB_mission()
    cur = DB.cursor()
    DB_CAS= connect_to_DB_cas()
    cur_cas = DB_CAS.cursor()
    ADMIN = False
    try:

        if data[2] == "BASIC":
            cur.execute(f"SELECT * FROM suivi_mission WHERE ID_USER = '{data[0]}'")
            mission = cur.fetchall()
            return render_template('view.html', Missions=mission , ADMIN=ADMIN)
        elif data[2] == "ADMIN" or data[2] == "GESTION":
            cur.execute(f"SELECT * FROM suivi_mission")
            mission = list(cur.fetchall())
            cur.execute(f"SELECT DISTINCT ID_USER FROM suivi_mission")
            users = tuple(item[0] for item in cur.fetchall())
            cur_cas.execute(f"SELECT nom FROM personnels WHERE login IN {users}")
            all_user = list(item[0] for item in cur_cas.fetchall())
            ADMIN = True
            return render_template('view.html', Missions=mission , ADMIN=ADMIN, All_User=all_user)
    except mariadb.Error as e: 
        #print(f"Error: {e}")
        return "oups"
    except Exception as e:
        error_text = "<p>The error:<br>" + str(e) + "</p>"
        hed = '<h1>Something is broken.</h1>'
        return hed + error_text

#################################
@app.route("/mission/view_mission/<id_mission>", methods=['GET'])
def show_mission(id_mission):
    Verif_Connection(request)
    DB = connect_to_DB_mission()
    cur = DB.cursor()
    cur.execute(f"SELECT ID_USER , STATUE FROM suivi_mission WHERE ID ='{id_mission}'")
    data = oauth_user[request.cookies.get("SESSID")]
    dimitri = cur.fetchone()
    user = dimitri[0]
    BOB = dimitri[1]
    if data[2] == "ADMIN" or data[2] == "GESTION" or data[0] == user:
        cur.execute(f"SELECT * FROM ordre_mission WHERE ID ='{id_mission}'")
        mission = list(item for item in cur.fetchall()[0])
        return render_template('order.html', Mission=mission, STAT=BOB)
        #return f"<html><body> <h1>  {id_mission} {mission}  </h1></body></html>"
    else:
        print(f'Connection refusé to {data[1]}')
        return abort(403)

@app.route("/mission/view_mission/<id_mission>",methods=['POST'])
def upstatmiss_mission(id_mission):
    print(f"UPDATE {id_mission} to {request.form.get('STAT')}")
    return redirect(url_for('show_mission'))
#################################
@app.route("/mission/create_mission", methods=['POST'])
def create_new_mission():
    Verif_Connection(request)

    #for value in request.values:
        #print(f"{value} | {request.values[value]} | {type(request.values[value])}")
    val = request.values
    DB = connect_to_DB_mission()
    cur = DB.cursor()
    ID = new_ID()
    user_id = oauth_user[request.cookies.get("SESSID")][0]
    nom = oauth_user[request.cookies.get("SESSID")][1]
    if val['MISSION'] == "FRANCE":
        PAYS = "FRANCE"
    else:
        PAYS = val["pays"]

    try:
        cur.execute("INSERT INTO mission.ordre_mission(ID,NOM,PRENOM,DATE_AJD,NOM_MISSION,PAYS_MISSION,FRAIS,D_DEPART,H_DEPART,D_RETOUR,H_RETOUR,TRANSPORT,LIEU,CODE_PTL,VILLE,HOTEL,PTDEJ,QUILL) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",(ID.__repr__(),val["NOM"],val["PRENOM"],val["DATE_AJD"],val["NOM_MISSION"],PAYS,val["FRAIS"],val["D_DEPART"],val["H_DEPART"],val["D_RETOUR"],val["H_RETOUR"],val["TRANSPORT"],val["LIEU"],val["CODE_PTL"],val["VILLE"],val["HOTEL"],val["PTDEJ"],val["QUILL"]))
        statu_crea = 0
        cur.execute("INSERT INTO mission.suivi_mission(ID,ID_USER,NAME,NOM_MISSION,DATE_CREA,STATUE) VALUES (%s,%s,%s,%s,%s,%d)",(ID,user_id,nom,val["NOM_MISSION"],val["DATE_AJD"],statu_crea))

        Send_Mail_NM(nom,ID)
        ##print(f"Ordre mission {ID} success")
    except mariadb.Error as e:
        e = 0
        ##print(f"Error: {e}")

    return redirect("/mission/")

#################################

@app.route("/mission/DB")
def DBConnect():
    try:
        DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",
                            autocommit=True)
        #print(DB)
    except mariadb.Error as e:
        #print(f"Error connecting to the database: {e}")
        e=0
    return "<html><body> <h1>  DB  </h1></body></html>"

#################################

@app.route("/mission/who_is_loged")
def WHO_IS():
    ID = request.cookies.get('SESSID')
    name = oauth_user[ID]
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
        DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",
                            autocommit=True)
        DB.autocommit = True
        return DB
    except mariadb.Error as e:
        raise Exception(f"Error connecting to the database: {e}")
    
def connect_to_DB_cas():
    try:
        DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="db_cas",
                            autocommit=True)
        DB.autocommit = True
        return DB
    except mariadb.Error as e:
        raise Exception(f"Error connecting to the database: {e}")

def Verif_Connection(request):
    if oauth_user.get(request.cookies.get("SESSID",None),None) == None:
        abort(403)

def Send_Mail_NM(user,id_mission):
    
    # Informations de connexion et de l'expéditeur
    sender_email = "serveur.mission.geii@gmail.com"
    #receiver_email = "valerie.galland@u-bordeaux.fr"
    receiver_email = "warren.privat@u-bordeaux.fr"

    # Configuration du message
    subject = f"Nouvelle demande de mission de {user}"
    body =f"""
<div>Hey, Valerie
<br>&nbsp;&nbsp; &nbsp;<br>&nbsp;&nbsp; &nbsp;
{user} a ouvert une nouvelle demande de mission: <a href="http://geii.iut.u-bordeaux.fr/mission/view_mission/{id_mission}" target="_blank" rel="noopener" data-mce-href="http://geii.iut.u-bordeaux.fr/mission/view_mission/{id_mission}" data-mce-selected="inline-boundary">{id_mission} </a>
&nbsp;<br>
Courage<br>
@+<br>&nbsp;&nbsp; &nbsp;</div>
"""

    # Création de l'objet message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject

    # Ajout du corps de texte
    message.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP("smtpauth.u-bordeaux.fr", 587) as server:
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
        app.run(port=6969,debug=True)
