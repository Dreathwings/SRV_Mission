from flask import Flask, render_template, request
#app = Flask('mission')
app = Flask('mission',static_url_path='/mission/static/')
app.config.update(
                  TEMPLATES_AUTO_RELOAD=True)


@app.route("/mission", methods=['GET'])
def ordre():
    return render_template('new_order.html')

@app.route("/create_mission", methods=['GET'])
def create_new_mission():
    print("POST NEW FORM")
    print(request.values)
    return "<html><body> <h1>NEW MISSION ORDER</h1></body></html>"

# Running the API
if __name__ == "__main__":
    with app.app_context():
        for rule in app.url_map.iter_rules():
    	    print(f"{rule.endpoint}: {rule.methods} - {rule}")
app.run(port="6969",debug=True)
