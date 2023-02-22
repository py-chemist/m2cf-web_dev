from flask import Flask, jsonify, request
from flask_cors import CORS

from m2cf import m2cf


app = Flask(__name__)
app.register_blueprint(m2cf)

cors = CORS(app, resources={r"*": {"origins": "*"}})



if __name__ == '__main__':
   app.run(debug=True, host='0.0.0.0')
