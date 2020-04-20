import pymongo
from pymongo import MongoClient
import numpy as np
from api import buy, sell, get_quotes, getBalance, checkPosition, get_price_history
import datetime
import time

#things to do:
#implement checkBalances method in api.py and integrate into sell and buy
#update balance in update() when money enters account
#fix pinging and token requests

#user-input
symb = ['AAPL','NFLX','GOOG','HFC','GS','WTI','AMZN','UAL','XOM','IBM']
frequency = 1 #minutes
track = 240 #minutes tracking
direction_check = 15 #minutes for direction calculator
change_min = 1 #minimum percentage drop to initiate sequence

#accessing database
cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["test"]

def initializeDB():
	#initializing values in database
	start = int(time.time())-259200000
	for i in range(len(symb)):
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,startDate=start)
		max_length = len(obj)

		v = []
		for j in range(track):
			v.append(float(obj[max_length-track+j]['close']))

		s = []
		inflections = []
		d = np.mean(s)

		for j in range(len(v)-1):
			slope = (v[j+1]-v[j])/v[j]*100
			s.append(slope)

		for j in range(len(s)-1):
			if(s[j]==0):
				inf = (s[j+1]-s[j])/0.000001*100
			else:
				inf = (s[j+1]-s[j])/s[j]*100
			inflections.append(inf)

		post = {"_id":symb[i],"vals":v,"slopes":s,"infl":inflections,"dir":d,"wait":0}
		collection.insert_one(post)

def getBalance():
	return 1

def update_vals(old):
	vals = old["vals"]
	slopes = old["slopes"]
	infl = old["infl"]

	new_val = get_quotes(symbol=old['_id'])
	vals.append(new_val)
	new_slope = (vals[len(vals)-1] - vals[len(vals)-2])/vals[len(vals)-2]*100 #percent change in new minute
	slopes.append(new_slope)
	new_infl = (slopes[len(slopes)-1]-slopes[len(slopes)-2])/slopes[len(slopes)-2]*100 #percent change of slopes in new minute
	infl.append(new_infl)
	direct = np.mean(slopes[len(slopes)-direction_check:])

	vals.pop(0)
	slopes.pop(0)
	infl.pop(0)

	obj = {"_id":sym,"vals":vals,"slopes":slopes,"infl":infl,"dir":direct}
	collection.update(obj)
	return obj

def decision(obj):
	vals = obj["vals"]
	slopes = obj["slopes"]
	infl = obj["infl"]
	direct = obj["dir"] #buy or sell
	wait = obj["wait"]

	high = max(vals)
	drop = (high - vals[len(vals)-1]) / high*100

	low = min(vals)
	rise = (low - vals[len(vals)-1])/low*100

	if(abs(drop)>change_min and direct<0):
		if(wait>=wait_time):
			if(np.mean(slopes[len(slopes)-wait_time:])<0):
				collections.update_one({"_id":obj['_id'],"wait":0})
			else:
				return([drop,'buy'])
		else:
			new_wait = wait+1
			collections.update_one({"_id":obj['_id'],"wait":new_wait})
	elif(abs(rise)>change_min and direct>0):
		if(wait>=wait_time):
			if(np.mean(slopes[len(slopes)-wait_time:])>0):
				collections.update_one({"_id":obj['_id'],"wait":0})
			else:
				return([rise,'sell'])
		else:
			new_wait = wait+1
			collections.update_one({"_id":obj['_id'],"wait":new_wait})

def update():
	# run regularly on minute-by-minute interval
	sell_matrix = []
	buy_matrix = []

	for i in range(len(symb)):
		obj = update_vals(collection.find({"_id":sym}))
		dec = decision(obj)
		if(dec[1]=='sell'):
			sell_matrix.append(dec[0],obj["_id"])
		if(dec[0]=='buy'):
			buy_matrix.append(dec[0],obj["_id"])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)

	while len(sell_matrix)>0:
		sell(sell_matrix[len(sell_matrix)-1][1])
		sell_matrix.pop(len(buy_matrix)-1)

	#retrieve balances after sell-offs
	balance = 100

	while len(buy_matrix)>0 and balance>0:
		buy(buy_matrix[len(buy_matrix)-1][1])
		buy_matrix.pop(len(buy_matrix)-1)

if __name__ == "__main__":
	while(1):
		time.sleep(1)
		if datetime.time(9, 30) <= datetime.datetime.now().time() <= datetime.time(16,30):
			update()
	print("moneybags v1")
