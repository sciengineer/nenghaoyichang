from urllib.parse import urljoin

import requests
from flask import Flask
from flask_cors import CORS
from gevent import pywsgi

app = Flask(__name__)
CORS(app)


@app.route("/tiansu/api/v1.0/power_consumption/call_mysql_one_hour/<int:id>/", methods=['GET', 'POST'])
def get_mysql_data_one_hour(id):
    BASE_URL = 'http://192.168.70.241:3001'
    response = requests.get(urljoin(BASE_URL, "/tiansu/api/v1.0/power_consumption/mysql_one_hour/%d/" % id))
    print('response:', response)
    one_hour_data = response.text
    print('one_hour_data:', one_hour_data)
    return one_hour_data


# running REST interface, port=3002 for direct test
if __name__ == "__main__":

    # app.debug = True
    server = pywsgi.WSGIServer(('0.0.0.0', 3002), app,log=None)
    server.serve_forever()
