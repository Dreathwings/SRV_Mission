from flask import Flask, render_template
app = Flask('mission',static_folder='/mission/static')
app.config.update(
                  TEMPLATES_AUTO_RELOAD=True)


@app.route("/")
def ordre():
    return render_template('new_order.html')

# Running the API
if __name__ == "__main__":
    app.run(port="6969",debug=True)