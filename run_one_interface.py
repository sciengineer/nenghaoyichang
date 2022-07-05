import time
from urllib.parse import urljoin
from multiprocessing import Pool
import requests
import multiprocessing



# 调用获取mysql数据的接口的接口call_mysql_one_hour
def get_data_call_mysql_one_hour(floor_id):
    BASE_URL = 'http://192.168.70.241:3002'
    init_data = requests.get(urljoin(BASE_URL, "/tiansu/api/v1.0/power_consumption/call_mysql_one_hour/%d/" % floor_id))
    return init_data


# 将每个小时的能耗数据传参到算法程序中
def post_one_hour_data(floor_id):
    BASE_URL = 'http://192.168.70.241:3003'
    one_hour_data = get_data_call_mysql_one_hour(floor_id).text
    print('init_data:', one_hour_data)
    post_one_hour_data = {"power_consumption": one_hour_data}
    response = requests.post(url=urljoin(BASE_URL, "/tiansu/api/v1.0/power_consumption/one_hour_data/%d/" % floor_id), data=post_one_hour_data)
    return response

# for id in range(4):
def func(floor_id):
# 推送数据未满240个时，result为字符'a'，循环推送
    result = 'a'
    while (result == 'a'):
        print(str(multiprocessing.current_process())+str(floor_id))
        response = post_one_hour_data(floor_id)
        result = response.text
        print("result:",result)


    # 达到240个数据后，返回当前小时的用电量predict_value，每隔一个小时推送实际用电量给算法模型，返回得到的是否异常的布尔值flag，偏差值error
    while True:
        # 应该是每到一个整点实际耗电量出来后，开始循环
        time.sleep(5)
        # time.sleep(3600)
        # for i in range
        response = post_one_hour_data(floor_id)
        result = eval(response.text)
        print(result)

if __name__ == '__main__':
    ids = [i for i in range(1)]

    pool = Pool(processes=1)

    pool.map(func, ids)
    pool.terminate()
