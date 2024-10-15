from flask import Flask, render_template, request
import mariadb
import sys
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.config.update(
                  TEMPLATES_AUTO_RELOAD=True)


@app.route("/mission", methods=['GET'])
def ordre():
    return render_template('new_order.html')

@app.route("/mission/create_mission", methods=['GET'])
def create_new_mission():
    print("POST NEW FORM")
    print(request.values)
    return "<html><body> <h1>NEW MISSION ORDER</h1></body></html>"
@app.route("/mission/DB")
def DBConnect():
    try:
        import mysql.connector

        mydb = mysql.connector.connect(
        host="localhost",
        user="mission",
        password="zB1Bm]8rnIMk4MD-"
        )

        print(mydb) 
        """DB = mariadb.connect(host="localhost",
                             port=3306,
                            user="mission",
                            password="zB1Bm]8rnIMk4MD-",
                            database="mission")"""
    except mysql.Error as e:
        print(f"Error connecting to the database: {e}")
        sys.exit(1)
    return "<html><body> <h1>  DB  </h1></body></html>"
# Running the API
if __name__ == "__main__":
    with app.app_context():
        for rule in app.url_map.iter_rules():
    	    print(f"{rule.endpoint}: {rule.methods} - {rule}")
app.run(port="6969",debug=True)
