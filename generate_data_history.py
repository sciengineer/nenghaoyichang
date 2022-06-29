#encoding:utf-8
import pandas as pd
import numpy as np
import time
import random

from sqlalchemy import create_engine

engine = create_engine('mysql+pymysql://root:123456@localhost:3306/test?charset=utf8')

# 使用 execute() 方法执行 SQL，如果表存在则删除
engine.execute("DROP TABLE IF EXISTS POWER_CONSUMPTION_0526")

# 使用预处理语句创建表
sql = """CREATE TABLE POWER_CONSUMPTION_0526 (
           id int,
           datetime  datetime NOT NULL,
           power_consumption FLOAT )"""

engine.execute(sql)


# df = pd.read_csv("mianyang_id_1_power_consumption_5.1_5.23_hourly.csv", header=0)
df = pd.read_excel("miangyang_aircon_June.xlsx", header=0)
# df = df.reset_index()
df = df.rename(columns={"timestamp":"datetime"})
df.replace('--',0,inplace=True)

df['id'] = 0

print(df)
df_use = df[(df.datetime>='2022-06-01 14:00')]
# df_use = df.loc[203:]
print(df.columns)
print(df_use)
df_use.to_sql('POWER_CONSUMPTION_0526'.lower(), engine, if_exists='append', index=False)

# days = 26
# hours = days*24
#
# n_id  = 2
# for i in range(n_id):
#
#     power_consumption = 100 + 20 * np.random.randn(hours)
#     # power_consumption = np.zeros(hours)
#     index = pd.date_range(start='2022-05-01', periods=hours, freq='H')
#
#     index = pd.date_range(start='2021-06-01',end='2022-06-01',freq='H')
#     df = pd.DataFrame(data=power_consumption, index=index)
#     df = df.reset_index()
#     col = ['datetime', 'power_consumption']
#     df.columns = col
#     df['id'] = i
#
#     print(df)
#
#     df.to_sql('POWER_CONSUMPTION_0526'.lower(), engine, if_exists='append', index=False)
    # index = pd.date_range(start='2022-05-01',end='2022-05-26',freq='H')
    # df = pd.DataFrame(data=power_consumption, index=index)





    # engine = create_engine('mysql+pymysql://root:123456@localhost:3306/test?charset=utf8')
    #
    # # 使用 execute() 方法执行 SQL，如果表存在则删除
    # engine.execute("DROP TABLE IF EXISTS POWER_CONSUMPTION")
    #
    # # 使用预处理语句创建表
    # sql = """CREATE TABLE POWER_CONSUMPTION (
    #          datetime  datetime NOT NULL,
    #        power_consumption FLOAT )"""
    #
    # engine.execute(sql)







