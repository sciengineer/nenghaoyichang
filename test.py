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

df_training = pd.read_csv(r"C:\Users\qlvzy\PycharmProjects\nenghaoyichang\result\df_1_weeks\df_1_weeks0.csv",header=0)
test_days = 1
# df = df[0:len(df)-test_days]#取前面为训练数据，后test_days个为测试数据
#按照prophet格式更改数据名称
# df = df.rename(columns={"power_consumption":"y", "timestamp":"ds"})
model = Prophet(weekly_seasonality=True)

# model = Prophet(weekly_seasonality=True)
# model = Prophet(mcmc_samples=100)
# model.add_country_holidays('CN')
model.fit(df_training)
# print(model.predictive_samples(future))
#预测的数据
future = model.make_future_dataframe(periods = test_days, freq = "1h")
forecast = model.predict(future)

predict_value = forecast.yhat[-test_days:].values[0]
yhat_upper = forecast.yhat_upper[-test_days:].values[0]
yhat_lower = forecast.yhat_lower[-test_days:].values[0]
print(predict_value)
print(yhat_upper)
print(yhat_lower)