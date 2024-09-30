from flask import Flask, render_template
app = Flask(__name__)


@app.route("/")
def hello():
    return 'Hello, World!'

@app.route("/ordre")
def ordre():
    return render_template('new_order.html')

# Running the API
if __name__ == "__main__":
    app.run(port="6969",debug=False)