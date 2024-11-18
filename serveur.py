from flask import Flask, redirect, render_template, request, url_for
import requests as REQ
import flask
import mariadb
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.config.update(TEMPLATES_AUTO_RELOAD=True)

@app.route("/mission/", methods=['GET'])
def index():
    if 'SESSID' in request.cookies:
        return render_template('index.html')
    else:
        return redirect("/mission/oauth")

@app.route("/mission/oauth/")
def oauth():
    if 'ticket' in request.values:
        PARAMS = {"ticket":request.values['ticket']}
        print(f"Ticket :{request.values['ticket']}")
        ID = REQ.get(url = "https://cas.u-bordeaux.fr/cas/validate",params=PARAMS)
        print(ID.cookies)
        return str(ID._content)
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
    print()
    for value in request.values:
        print(f"{value} | {request.values[value]} | {type(request.values[value])}")
        val = request.values
    DB = mariadb.connect(host="localhost",
                            port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission",autocommit=True)
    cur = DB.cursor()
    ID = new_ID()
    if val['MISSION'] == "FRANCE":
        PAYS = "FRANCE"
    else:
        PAYS = val["pays"]
    try:
        cur.execute("INSERT INTO mission.ordre_mission(ID,NOM,PRENOM,DATE_AJD,NOM_MISSION,PAYS_MISSION,FRAIS,D_DEPART,D_RETOUR,TRANSPORT,LIEU,CODE_PTL,VILLE,HOTEL,PTDEJ,QUILL_URL) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(ID.__repr__(),val["NOM"],val["PRENOM"],val["DATE_AJD"],val["NOM_MISSION"],PAYS,val["FRAIS"],val["D_DEPART"],val["D_RETOUR"],val["TRANSPORT"],val["LIEU"],val["CODE_PTL"],val["VILLE"],val["HOTEL"],val["PTDEJ"],'BOBO'))
        statu_crea = 0
        cur.execute("INSERT INTO mission.suivi_mission(ID,ID_USER,DATE_CREA,STATUE) VALUES (?,?,?,?)",(ID.__repr__(),"Bob",val["DATE_AJD"],statu_crea))
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
                            database="mission")
        print(DB)
    except mariadb.Error as e:
        print(f"Error connecting to the database: {e}")
    return "<html><body> <h1>  DB  </h1></body></html>"

def new_ID():
    import uuid
    ID = uuid.uuid4()
    return ID
# Running the API
if __name__ == "__main__":
    with app.app_context():
        for rule in app.url_map.iter_rules():
    	    print(f"{rule.endpoint}: {rule.methods} - {rule}")
        app.run(port=6969,debug=True)
