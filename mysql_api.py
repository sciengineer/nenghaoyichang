import json
from datetime import datetime

import pymysql
from flask import Flask
from flask_cors import CORS
from gevent import pywsgi
from conf import config


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


# 模拟时，获取mysql表power_consumption中的第time个数据
# 真实需求是从当前系统时间的前240个小时开始，从前到后，每次取一个
def sql_result(time,id):
    conn = pymysql.connect(**config)
    conn.autocommit(1)
    conn.select_db('test')
    cursor = conn.cursor()
    cur_time = datetime.now()
    cur_hour = cur_time.replace(minute=0, second=0, microsecond=0)
    sql = 'SELECT * FROM power_consumption_0526 where id = {id} limit {time},1 '.format(time=time,id=id)
    cursor.execute(sql)
    result = cursor.fetchall()
    conn.close()
    return result


app = Flask(__name__)
CORS(app)


# 每次获取mysql表power_consumption中的1个小时数据,达到240个训练数据后，中值滤波得到120个数据，作为初始训练数据(当前时间点前240个小时的实际耗电数据)
@app.route("/tiansu/api/v1.0/power_consumption/mysql_one_hour/<int:id>/", methods=['GET', 'POST'])
def init(id):
    # f_out = open('num'+str(id)+'.txt', 'r+')
    try:
        with open('mysql' + str(id) + '.txt', 'r+') as f_out:
            count = int(f_out.read())
    except FileNotFoundError:

        with open('mysql' + str(id) + '.txt', 'w') as f_out:
            f_out.write("1")
            count = 1
    # with open('mysql' + str(id) + '.txt', 'w') as f_out:
    #     f_out.write("1")
    # count = f_out.read()
    return_dict = sql_result(count,id)
    count = int(count) + 1
    # f_out.seek(0)  # 清除内容
    # f_out.truncate()
    with open('mysql' + str(id) + '.txt', 'w') as f_out:
        f_out.write(str(count))

    # f_out.write(str(a))
    # f_out.close()
    print('count:', count)
    print('return_dict:', return_dict)
    return json.dumps(return_dict, cls=DateEncoder, ensure_ascii=False)


# running REST interface, port=3001 for direct test
if __name__ == "__main__":

    # app.debug = True
    server = pywsgi.WSGIServer(('0.0.0.0', 3001), app,log=None)
    server.serve_forever()

