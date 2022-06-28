import logging
import pickle
from datetime import datetime
import multiprocessing
import numpy as np
import pandas as pd
from fbprophet import Prophet
from flask import Flask, request
from flask_cors import CORS
import time
import os
import sys
import json
from gevent import pywsgi

logging.getLogger('fbprophet').setLevel(logging.ERROR)


# from https://stackoverflow.com/questions/11130156/suppress-stdout-stderr-print-from-python-functions
class suppress_stdout_stderr(object):
    '''
    A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.
       This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).

    '''

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])


df = pd.DataFrame(
    columns=['floor_id', 'datetime', 'power_consumption', 'power_consumption_ori', 'predict_value', 'error', 'flag'])
dict_of_list = {}
n_id = 10
for floor_id in range(n_id):
    dict_of_list[floor_id] = []


# Prophet模型训练与预测代码
def run_Prophet(floor_id):
    with open('df' + str(floor_id) + '.json') as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    df.reset_index(drop=True)
    df = df.rename(columns={"power_consumption": "y", "datetime": "ds"})

    m = Prophet()
    with suppress_stdout_stderr():
        m.fit(df)

    # 预测的数据
    predict_hours = 1
    future = m.make_future_dataframe(periods=predict_hours, freq="1h")
    forecast = m.predict(future)
    predict_value = str(forecast.yhat[-predict_hours:].values[0])
    df.to_json('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # jsonfile = open('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # df.to_json(jsonfile)
    # jsonfile.close()
    # jsonfile = open('df' + str(floor_id) + '.json')
    # df.to_json(jsonfile, orient='index', date_format="epoch", date_unit="s")
    # jsonfile.close()
    return predict_value


# 检测能耗是否异常，有异常值的话，需要用预测值替代后加入训练数据中
def anomaly_detection(a, df, floor_id):
    # 计算error
    def mean_absolute_percentage_error(y_true, y_pred):
        return np.mean(np.abs((y_true - y_pred) / max(y_true, y_pred))) * 100

    # 获取一个小时的实际能耗数据
    list = insert(floor_id)
    real_value = float(list[2])
    list = np.array(list).reshape(1, 7)
    df_real = pd.DataFrame(list,
                           columns=['floor_id', 'datetime', 'power_consumption', 'power_consumption_ori',
                                    'predict_value', 'error',
                                    'flag'])
    df_real = df_real.rename(columns={"power_consumption": "y", "datetime": "ds"})
    with open('df' + str(floor_id) + '.json', 'r+') as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    with open('predict_value' + str(floor_id) + '.txt', 'r+') as f_predict:
        predict_value = float(f_predict.read())
    error = mean_absolute_percentage_error(real_value, predict_value)

    df = pd.concat([df.iloc[1:], df_real.iloc[:1]], axis=0)
    df = df.reset_index(drop=True)
    flag = 'False'
    if error > 30:
        flag = 'True'
        error = '{:.2f}'.format(error)
        predict_value_str = '{:.2f}'.format(predict_value)
        print('Warning！{0}节点能耗异常：{1}的用电量真实值{2}与模型预测值{3}的偏差为{4}%，使用预测值作为训练数据'.format(floor_id, df_real.iloc[0].ds,
                                                                                    df_real.iloc[0].y,
                                                                                    predict_value_str, error))

        df.iat[-1, 2] = predict_value
    else:
        error = '{:.2f}'.format(error)
        predict_value_str = '{:.2f}'.format(predict_value)
        print('{0}节点{1}的用电量真实值{2}与模型预测值{3}的偏差为{4}%,能耗正常。'.format(floor_id, df_real.iloc[0].ds, df_real.iloc[0].y,
                                                                 predict_value_str,
                                                                 error))

    df = df.reset_index(drop=True)
    df.iat[-1, 4] = predict_value
    df.iat[-1, 5] = error
    df.iat[-1, 6] = flag
    df.to_json('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # jsonfile = open('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # df.to_json(jsonfile)
    # jsonfile.close()
    # jsonfile = open('df' + str(floor_id) + '.json')
    # df.to_json(jsonfile, orient='index', date_format="epoch", date_unit="s")
    # jsonfile.close()
    dict = {'floor_id': df.iat[-1, 0], 'datetime': df.iat[-1, 1], 'power_consumption': df.iat[-1, 2],
            'power_consumption_ori': df.iat[-1, 3], 'predict_value': predict_value, 'error': error, 'flag': flag}
    return dict


def init_data(floor_id):
    with open('df' + str(floor_id) + '.json', 'r+') as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    dict_240_hours = request.form['power_consumption']
    dict_240_hours = eval(dict_240_hours)
    df_240_hours = pd.DataFrame(dict_240_hours)
    # 按照prophet格式更改数据名称
    df_240_hours = df.rename(columns={"power_consumption": "y", "datetime": "ds"})
    df_240_hours['time'] = [pd.to_datetime(d).time() for d in df_240_hours['ds']]
    s_clock = datetime.now().hour
    # s_clock = 1
    grouped = df_240_hours.groupby("time")
    y_median = grouped['y'].agg('median')
    # print('y_median:', y_median)
    df_120_hours = df_240_hours[-120:]

    # 判断120小时内的某小时用电量明显异常的数值，替换为10天中该小时的用电量的中位数（超过30%，粗略判定为异常值）
    def is_abnormal(y, x):
        return abs(y - x) / max(x, y) > 0.3

    for i in range(120):
        if is_abnormal(float(df_120_hours.iloc[i]['y']), y_median[(s_clock + i) % 24]):
            print('{0}节点{1}的用电量{2}需要更新为中位值：{3}'.format(floor_id, df_120_hours.iloc[i]['ds'], df_120_hours.iloc[i]['y'],
                                                       y_median[(s_clock + i) % 24]))
            df_120_hours.iat[i, 2] = y_median[(s_clock + i) % 24]
    df_120_hours.drop('time', axis=1, inplace=True)
    df = df_120_hours.copy()
    df.to_json('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # jsonfile = open('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
    # df.to_json(jsonfile)
    # jsonfile.close()
    # jsonfile = open('df' + str(floor_id) + '.json')
    # df.to_json(jsonfile, orient='index', date_format="epoch", date_unit="s")
    # jsonfile.close()
    dict = run_Prophet(floor_id)

    return dict


def insert(floor_id):
    list = []
    # 将外部调用这个api获取到的datetime和power_consumption传入li
    li = request.form['power_consumption']
    li = eval(li)
    # li = json.loads(li)
    list.append(floor_id)
    list.append(li[0]['datetime'])
    list.append(li[0]['power_consumption'])
    list.append(li[0]['power_consumption'])

    None_tuple = (None,) * 3
    list.extend(None_tuple)

    return list


app = Flask(__name__)
CORS(app)


# 每次调用只给一个数据的api: init
@app.route("/tiansu/api/v1.0/power_consumption/one_hour_data/<int:floor_id>/", methods=['POST'])
def one_hour_date(floor_id):
    try:
        with open('num' + str(floor_id) + '.txt', 'r+') as f_out:
            a = int(f_out.read()) - 1
    except FileNotFoundError:
        with open('num' + str(floor_id) + '.txt', 'w') as f_out:
            f_out.write("1")
            a = 0
    if a < 240:
        # 将外部调用这个api获取到的datetime和power_consumption传入li
        dict_of_list[floor_id].append(insert(floor_id))
        num = a + 2
        with open('num' + str(floor_id) + '.txt', 'w') as f_out:
            f_out.write(str(num))
        print('*********************a + floor_id + current_process():',
              str(a) + ' ' + str(floor_id) + str(multiprocessing.current_process()))
        return 'a'

    elif a == 240:
        # 将外部调用这个api获取到的datetime和power_consumption传入li
        dict_of_list[floor_id].append(insert(floor_id))
        df = pd.DataFrame(dict_of_list[floor_id],
                          columns=['floor_id', 'datetime', 'power_consumption', 'power_consumption_ori',
                                   'predict_value', 'error',
                                   'flag'])

        df.to_json('df' + str(floor_id) + '.json', orient='index', date_format="epoch", date_unit="s")
        # jsonfile = open('df'+str(floor_id)+'.json', orient='index', date_format="epoch", date_unit="s")
        # jsonfile =  open('df'+str(floor_id)+'.json')
        # df.to_json(jsonfile,orient='index', date_format="epoch", date_unit="s")
        # jsonfile.close()
        predict_value = init_data(floor_id)

        with open('predict_value' + str(floor_id) + '.txt', 'w+') as f_predict:
            f_predict.write(predict_value)
        return predict_value
    else:
        with open('df' + str(floor_id) + '.json', mode='w') as json_file:
            df = pd.read_json(json_file, orient='index', date_unit="s")
        dict = anomaly_detection(a, df, floor_id)

        predict_value = run_Prophet(floor_id)

        with open('predict_value' + str(floor_id) + '.txt', 'w+') as f_predict:
            f_predict.write(predict_value)
        return dict


# running REST interface, port=3003 for direct test
if __name__ == "__main__":
    # app.debug = True
    server = pywsgi.WSGIServer(('0.0.0.0', 3003), app, log=None)
    server.serve_forever()
