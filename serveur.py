from uuid import uuid4
from flask import Flask, abort, redirect, render_template, request, session, url_for
import requests as REQ
import flask
import mariadb
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.secret_key='CECIESTLACLEFSECRETDEGEII'
app.config.update(TEMPLATES_AUTO_RELOAD=True)

oauth_user = dict()
authorized_user = {"wprivat":"ADMIN",
                   "vgalland":"GESTION"}
### Activate CAS oauth ###
CAS = True
##########################

@app.route("/mission/", methods=['GET'])
def index():
    if CAS:
        if request.cookies.get("SESSID") != None:
            print("SESSID exist")
            if request.cookies.get("SESSID") in oauth_user.keys() :
                print("SESSID autorized")
                return render_template('index.html')
            else:
                return redirect("/mission/oauth")
        else:
            return redirect("/mission/oauth")
    else:
        return render_template('index.html')

@app.route("/mission/oauth/")
def oauth():
    if 'ticket' in request.values:
        PARAMS = {"ticket":request.values['ticket'],
                  'service':"http://geii.iut.u-bordeaux.fr/mission/oauth"}
        # print(f"Ticket :{request.values['ticket']}")

        RESP = REQ.get(url = "https://cas.u-bordeaux.fr/cas/serviceValidate",params=PARAMS)
        if "authenticationSuccess" in str(RESP.content):
            id = str(RESP.content).split('cas:user')[1].removeprefix('>').removesuffix("</")
            DB = connect_to_DB_cas()
            cur = DB.cursor()
            ids = cur.execute("SELECT * FROM `db_cas`.`personnels` LIMIT 1000;")
            print(f"Login {ids}")
            if id in authorized_user.keys(): # Verif si user autorised sinon 403 list(cur.execute("SELECT ID FROM "))
                if id in oauth_user.items(): #Verif si user deja un SESSID
                    key = {i for i in oauth_user if oauth_user[i]==id}
                    oauth_user.pop(key)

                SESSID = uuid4().__str__()
                print(SESSID)
                oauth_user[SESSID] = id
                resp = flask.make_response(redirect("/mission"))  
                resp.set_cookie("SESSID", value = SESSID)
                print(f"USER {id} authorized")
            else:return abort(403)
                
            return resp
        else:
            return redirect("https://cas.u-bordeaux.fr/cas/login?service=http://geii.iut.u-bordeaux.fr/mission/oauth")
    else:
        return redirect("https://cas.u-bordeaux.fr/cas/login?service=http://geii.iut.u-bordeaux.fr/mission/oauth")


@app.route("/mission/create_mission", methods=['GET'])
def ordre():
    return render_template('new_order.html')



@app.route("/mission/view_mission", methods=['GET'])
def view():
    DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",autocommit=True)
    cur = DB.cursor()
    try:
        mission = cur.execute("")
        return render_template('view.html', Mission=mission)
    except Exception as e:
        error_text = "<p>The error:<br>" + str(e) + "</p>"
        hed = '<h1>Something is broken.</h1>'
        return hed + error_text

@app.route("/mission/create_mission", methods=['POST'])
def create_new_mission():
    for value in request.values:
        print(f"{value} | {request.values[value]} | {type(request.values[value])}")
        val = request.values
    DB = connect_to_DB_mission()
    cur = DB.cursor()
    ID = new_ID()
    user_id = oauth_user[request.cookies.get("SESSID")]
    if val['MISSION'] == "FRANCE":
        PAYS = "FRANCE"
    else:
        PAYS = val["pays"]
    try:
        cur.execute("INSERT INTO mission.ordre_mission(ID,NOM,PRENOM,DATE_AJD,NOM_MISSION,PAYS_MISSION,FRAIS,D_DEPART,D_RETOUR,TRANSPORT,LIEU,CODE_PTL,VILLE,HOTEL,PTDEJ,QUILL_URL) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(ID.__repr__(),val["NOM"],val["PRENOM"],val["DATE_AJD"],val["NOM_MISSION"],PAYS,val["FRAIS"],val["D_DEPART"],val["D_RETOUR"],val["TRANSPORT"],val["LIEU"],val["CODE_PTL"],val["VILLE"],val["HOTEL"],val["PTDEJ"],'BOBO'))
        statu_crea = 0
        cur.execute("INSERT INTO mission.suivi_mission(ID,ID_USER,DATE_CREA,STATUE) VALUES (?,?,?,?)",(ID.__str__(),user_id,val["DATE_AJD"],statu_crea))
        print(f"Ordre mission {ID} success")
    except mariadb.Error as e: 
        print(f"Error: {e}")

    return redirect("/mission/")


@app.route("/mission/DB")
def DBConnect():
    try:
        DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",
                            autocommit=True)
        print(DB)
    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
    return "<html><body> <h1>  DB  </h1></body></html>"


@app.route("/mission/who_is_loged")
def WHO_IS():
    ID = request.cookies.get('SESSID')
    name = oauth_user[ID]
    return f"<html><body> <h1>  {name} with key {ID}  </h1></body></html>"

def new_ID():
    import uuid
    ID = uuid.uuid4()
    return ID.__str__()

def connect_to_DB_mission():
    try:
        DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",
                            autocommit=True)
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
        return DB
    except mariadb.Error as e:
        raise Exception(f"Error connecting to the database: {e}")
    
@app.errorhandler(403)
def access_denied(e):
    # note that we set the 403 status explicitly
    return render_template('403.html'), 403

# Running the API
if __name__ == "__main__":
    with app.app_context():
        for rule in app.url_map.iter_rules():
    	    print(f"{rule.endpoint}: {rule.methods} - {rule}")
        app.run(port=6969,debug=True)
