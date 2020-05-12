import pymongo
import collections
from pymongo import MongoClient
import math
import numpy as np
from forex_api import buy, sell, get_quotes, getBalance, resetToken, get_price_history
import datetime
import time
from db import getCollection

cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["Forex"]

'''
find symbol pairings

lists = ["AUD","CAD","CHF","CZK","DKK","EUR","GBP","HKD","HUF","ILS","JPY","MXN","NOK","NZD","PLN","SEK","SGD","THB","TRY","USD","ZAR"]
symbols = ""
asArray = []

for i in range(len(lists)):
	for j in range(len(lists)):
		if i==j:
			continue
		else:
			nextOne = lists[i]+"/"+lists[j]+","
			symbols = symbols + nextOne
			asArray.append(nextOne[:-1])

symbols = symbols[:-1]
obj = get_quotes(symbol=symbols)

actual = []

for i in range(len(obj)):
	if(obj[i] is None):
		continue
	elif(obj[i][0]!=0):
		actual.append(asArray[i])

print(actual)
'''

#symb = ['AUD/CAD', 'AUD/CHF', 'AUD/JPY', 'AUD/NOK', 'AUD/NZD', 'AUD/PLN', 'AUD/SGD', 'AUD/USD', 'CAD/CHF', 'CAD/JPY', 'CAD/NOK', 'CAD/PLN', 'CHF/HUF', 'CHF/JPY', 'CHF/NOK', 'CHF/PLN', 'EUR/AUD', 'EUR/CAD', 'EUR/CHF', 'EUR/CZK', 'EUR/DKK', 'EUR/GBP', 'EUR/HKD', 'EUR/HUF', 'EUR/JPY', 'EUR/MXN', 'EUR/NOK', 'EUR/NZD', 'EUR/PLN', 'EUR/SEK', 'EUR/SGD', 'EUR/TRY', 'EUR/USD', 'EUR/ZAR', 'GBP/AUD', 'GBP/CAD', 'GBP/CHF', 'GBP/DKK', 'GBP/HKD', 'GBP/JPY', 'GBP/NOK', 'GBP/NZD', 'GBP/PLN', 'GBP/SEK', 'GBP/SGD', 'GBP/USD', 'GBP/ZAR', 'HKD/JPY', 'NOK/DKK', 'NOK/JPY', 'NOK/SEK', 'NZD/CAD', 'NZD/CHF', 'NZD/JPY', 'NZD/USD', 'SGD/HKD', 'SGD/JPY', 'TRY/JPY', 'USD/CAD', 'USD/CHF', 'USD/CZK', 'USD/DKK', 'USD/HKD', 'USD/HUF', 'USD/ILS', 'USD/JPY', 'USD/MXN', 'USD/NOK', 'USD/PLN', 'USD/SEK', 'USD/SGD', 'USD/THB', 'USD/TRY', 'USD/ZAR', 'ZAR/JPY']
#symb = ['EUR/USD','GBP/USD','EUR/GBP']
#symb = ['AUD/USD','USD/JPY','AUD/JPY']
symb = ['USD/CHF','USD/PLN','CHF/PLN']
symbList = ",".join(symb)

def evaluate(obj):
	output = 1 * obj[0] / obj[1] * obj[2]
	percent = (output - 1)*100
	return percent
	
i = 1
while 0<i<1e9:
	obj = get_quotes(symbol = symbList)
	check = evaluate(obj)
	print(check)
	if check > 0.01 or check < -0.01:
		print(datetime.datetime.now().time())
		print(check)
		print(obj)
	time.sleep(2)
	i+=1