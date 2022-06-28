import logging
import os
from datetime import datetime
import multiprocessing
import numpy as np
import pandas as pd
from fbprophet import Prophet
from flask import Flask, request
from flask_cors import CORS
from gevent import pywsgi
import csv
from retry import retry
import threading
# from gevent import monkey, sleep
# monkey.patch_all()
from geventwebsocket.handler import WebSocketHandler

logging.getLogger('fbprophet').setLevel(logging.ERROR)

df = pd.DataFrame(
    columns=['floor_id', 'datetime', 'power_consumption', 'power_consumption_ori', 'predict_value', 'error', 'flag'])
dict_of_list = {}




def make_multi_dirs(sub_path):
    path_1 = './result'
    path = os.path.join(path_1,sub_path)
    os.makedirs(path,exist_ok=True)
    return path

path_df_json = make_multi_dirs('df_json')
path_df_240 =  make_multi_dirs('df_240')
path_df_120 =  make_multi_dirs('df_120')
path_y_meadian_log =  make_multi_dirs('y_meadian_log')
path_log =  make_multi_dirs('log')
path_num =  make_multi_dirs('num')
path_predict_value =  make_multi_dirs('predict_value')
path_anomaly_detection = make_multi_dirs('anomaly_detection')


# Prophet模型训练与预测代码
def run_Prophet(floor_id):
    with open(os.path.join(path_df_json,'df' + str(floor_id) + '.json')) as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    df.reset_index(drop=True)
    df = df.rename(columns={"power_consumption": "y", "datetime": "ds"})

    m = Prophet()
    m.fit(df)

    # 预测的数据
    predict_hours = 1
    future = m.make_future_dataframe(periods=predict_hours, freq="1h")
    forecast = m.predict(future)
    predict_value = str(forecast.yhat[-predict_hours:].values[0])
    # print('predict_value:',predict_value)
    df.to_json(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), orient='index', date_format="epoch", date_unit="s")
    return predict_value


# 检测能耗是否异常，有异常值的话，需要用预测值替代后加入训练数据中
def anomaly_detection(floor_id):
    # 计算error
    def mean_absolute_percentage_error(y_true, y_pred):
        if (y_pred == y_true == 0):
            return 0
        else:
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
    with open(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), 'r+') as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    with open(os.path.join(path_predict_value,'predict_value' + str(floor_id) + '.txt'), 'r+') as f_predict:
        predict_value = float(f_predict.read())
    error = mean_absolute_percentage_error(real_value, predict_value)

    # timestamp = df_real.iloc[0].ds
    # # real_value = float(df_real.iloc[0].y)
    # # predict_value = forecast.yhat[-test_days:].values[0]
    # # error = mean_absolute_percentage_error(real_value, predict_value)
    # list_timestamp.append(timestamp)
    # list_real.append(real_value)
    # list_predict.append(predict_value)
    # list_error.append(error)

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
    df.to_json(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), orient='index', date_format="epoch", date_unit="s")
    dict = {'floor_id': df.iat[-1, 0], 'datetime': df.iat[-1, 1], 'power_consumption': df.iat[-1, 2],
            'power_consumption_ori': df.iat[-1, 3], 'predict_value': predict_value, 'error': error, 'flag': flag}

    # 在整点过15分前（对比+预测）时不小心打开csv查看结果后没有及时关闭csv，导致报错，程序停止执行。加上retry后可以多次重试，在5分钟左右关上即可。
    @retry( delay=1, backoff=2, max_delay=10, tries=30)
    def write_anomaly_detection_to_csv():

        with open(os.path.join(path_anomaly_detection,'anomaly_detection'+str(floor_id)+'.csv'), 'a') as f:
            w = csv.DictWriter(f, dict.keys())
            # w.writeheader()
            w.writerow(dict)

    write_anomaly_detection_to_csv()
    return dict


def init_data(floor_id):
    with open(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), 'r+') as json_file:
        df = pd.read_json(json_file, orient='index', date_unit="s")
    # 按照prophet格式更改数据名称
    df_240_hours = df.rename(columns={"power_consumption": "y", "datetime": "ds"})
    df_240_hours['time'] = [pd.to_datetime(d).time() for d in df_240_hours['ds']]
    df_240_hours.to_csv(os.path.join(path_df_240,'df_240_hours'+str(floor_id)+'.csv'), mode='a', header=True)
    s_clock = datetime.now().hour
    # s_clock = 0
    grouped = df_240_hours.groupby("time")
    y_median = grouped['y'].agg('median')

    y_median_log = open(os.path.join(path_y_meadian_log, 'y_meadian_log' + str(floor_id) + '.txt'), mode='a', encoding='utf-8')

    print('y_median:',y_median,file=y_median_log)
    y_median_log.close()
    df_120_hours = df_240_hours[-120:]
    df_120_hours = df_120_hours.reset_index(drop=True)

    # 判断120小时内的某小时用电量明显异常的数值，替换为10天中该小时的用电量的中位数（超过30%，粗略判定为异常值）
    def is_abnormal(y, x):
        if (y == x == 0):
            return 0
        else:
            return abs(y - x) / max(x, y) > 0.3
    log = open(os.path.join(path_log,'log'+str(floor_id)+'.txt'),mode='a',encoding='utf-8')
    for i in range(120):
        if is_abnormal(float(df_120_hours.iloc[i]['y']), y_median[(s_clock + i) % 24]):
            print('{0}节点{1}的用电量{2}需要更新为中位值：{3}'.format(floor_id, df_120_hours.iloc[i]['ds'], df_120_hours.iloc[i]['y'],
                                                       y_median[(s_clock + i) % 24]),file=log)
            df_120_hours.iat[i, 2] = y_median[(s_clock + i) % 24]
    log.close()
    df_120_hours.drop('time', axis=1, inplace=True)
    df = df_120_hours.copy()
    df.to_csv(os.path.join(path_df_120,'df_120_hours'+str(floor_id)+'.csv'), mode='a', header=True)
    # with open('test.csv', 'a') as f:
    #     for key in dict.keys():
    #         f.write("%s,%s\n" % (key, dict[key]))

    df.to_json(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), orient='index', date_format="epoch", date_unit="s")
    dict = run_Prophet(floor_id)


    return dict


def insert(floor_id):
    list_1 = []
    # 将外部调用这个api获取到的datetime和power_consumption传入li
    li = request.form['power_consumption']
    li = eval(li)

    list_1.append(floor_id)
    list_1.append(li[0]['datetime'])
    list_1.append(li[0]['power_consumption'])
    list_1.append(li[0]['power_consumption'])
    None_tuple = (None,) * 3
    list_1.extend(None_tuple)

    return list_1


app = Flask(__name__)
CORS(app)


# 每次调用只给一个数据的api: init
@app.route("/tiansu/api/v1.0/power_consumption/one_hour_data/<int:floor_id>/", methods=['POST'])
def one_hour_date(floor_id):

    try:
        with open(os.path.join(path_num,'num' + str(floor_id) + '.txt'), 'r+') as f_out:
            a = int(f_out.read())
    except FileNotFoundError:

        with open(os.path.join(path_num,'num' + str(floor_id) + '.txt'), 'w') as f_out:
            f_out.write("1")
            a = 1
    if a < 240:
        # logging.info("You can see me now...")
        if floor_id not in dict_of_list:
            dict_of_list[floor_id] = []
        # 将外部调用这个api获取到的datetime和power_consumption传入li
        dict_of_list[floor_id].append(insert(floor_id))
        num = a + 1
        with open(os.path.join(path_num, 'num' + str(floor_id) + '.txt'), 'w') as f_out:
            f_out.write(str(num))
        return 'a'

    elif a == 240:
        # 将外部调用这个api获取到的datetime和power_consumption传入li
        dict_of_list[floor_id].append(insert(floor_id))
        df = pd.DataFrame(dict_of_list[floor_id],
                          columns=['floor_id', 'datetime', 'power_consumption', 'power_consumption_ori',
                                   'predict_value', 'error',
                                   'flag'])

        df.to_json(os.path.join(path_df_json,'df' + str(floor_id) + '.json'), orient='index', date_format="epoch", date_unit="s")
        predict_value = init_data(floor_id)
        num = a + 1
        with open(os.path.join(path_num,'num' + str(floor_id) + '.txt'), 'w') as f_out:
            f_out.write(str(num))
        with open(os.path.join(path_predict_value,'predict_value' + str(floor_id) + '.txt'), 'w+') as f_predict:
            f_predict.write(predict_value)
        return predict_value
    else:
        dict = anomaly_detection(floor_id)
        predict_value = run_Prophet(floor_id)
        num = a + 1
        with open(os.path.join(path_num, 'num' + str(floor_id) + '.txt'), 'w') as f_out:
            f_out.write(str(num))
        with open(os.path.join(path_predict_value, 'predict_value' + str(floor_id) + '.txt'), 'w+') as f_predict:
            f_predict.write(predict_value)
        return dict

# # run the application
# server=  wsgi.WSGIServer(('0.0.0.0', 8080), app, log=logger)
# server.serve_forever()

# running REST interface, port=3003 for direct test
if __name__ == "__main__":
    # logging.info("You can see me now...")
    # logger = logging.getLogger('MainProgram')
    # logger.setLevel(10)
    # logHandler = handlers.RotatingFileHandler('log.log', maxBytes=1000000, backupCount=1)
    # logger.addHandler(logHandler)
    # logger.info("Logging configuration done")
    # app.debug = True
    # logging.basicConfig(level=logging.DEBUG  # 控制台打印的日志级别
    #                     # filename='log.log',  # 将日志写入log_new.log文件中
    #                     # filemode='w',  # 模式，有w和a，w就是写模式，每次都会重新写日志，覆盖之前的日志 a是追加模式，默认如果不写的话，就是追加模式
    #                     # format="%(asctime)s:%(levelname)s:%(name)s -- %(message)s", datefmt="%Y/%m/%d %H:%M:%S"  # 日志格式
    #                     )
    # server = pywsgi.WSGIServer(('0.0.0.0', 3003), app, log=None)
    # def start_server():
    #     print('Starting wsgi server...')
    #     server = pywsgi.WSGIServer(('0.0.0.0', 3003), app)
    # # server = pywsgi.WSGIServer(('0.0.0.0', 3003), app,handler_class=WebSocketHandler)
    #     app.debug = True
    #     # server.serve_forever()
    #     thread = threading.Thread(target=server.serve_forever)
    #     try:
    #         thread.start()
    #     except Exception as e:
    #         print("Exception Handled in Main, Details of the Exception:", e)
    # try:
    #     start_server()
    # except Exception as e:
    #     print(Exception,":",e)
    # else:
    #     print('Wsgi server was started successfully!')
    # print('started successfully')
    print('Starting wsgi server...')
    server = pywsgi.WSGIServer(('0.0.0.0', 3003), app)
    # try:
    server.serve_forever()
    # except Exception as e:
    #     print(Exception,":",e)
    # else:
    #     print('Wsgi server was started successfully!')
