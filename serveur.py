from flask import Flask, render_template, request
import mariadb
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.config.update(
                  TEMPLATES_AUTO_RELOAD=True)

@app.route("/mission", methods=['GET'])
def index():
    return render_template('index.html')
@app.route("/mission/create_mission", methods=['GET'])
def ordre():
    return render_template('new_order.html')

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
        print(f"Ordre mission {ID} success")
    except mariadb.Error as e: 
        print(f"Error: {e}")

    return "<html><body> <h1>NEW MISSION ORDER</h1></body></html>"


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
        app.run(port="6969",debug=True)
