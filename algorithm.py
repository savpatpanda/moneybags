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
		d = np.mean(v)

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

	# new_val = get_quotes(symbol=old['_id'])
	print("%s, last slopes: %s, last vals: %s" % (old["_id"], old["slopes"][-5:], old["vals"][-5:]))
	print("\nprint new value:\n")
	new_val = int(input())
	vals.append(new_val)
	new_slope = (vals[-1] - vals[-2])/vals[-2]*100 #percent change in new minute
	slopes.append(new_slope)
	new_infl = (slopes[-1]-slopes[-2]) * 100 #percent change of slopes in new minute
	new_infl /= slopes[-2] if slopes[-2] != 0 else 0.00001
	infl.append(new_infl)
	direct = np.mean(slopes[-direction_check:])

	vals.pop(0)
	slopes.pop(0)
	infl.pop(0)

	obj = {"_id":old['_id'], "vals":vals,"slopes":slopes,"infl":infl,"dir":direct, "wait": 0}
	collection.update_one({"_id": old["_id"]}, {"$set": {"vals":vals,"slopes":slopes,"infl":infl,"dir":direct}})
	return obj

def decision(obj):
	vals =  obj["vals"]
	slopes =  obj["slopes"]
	infl =  obj["infl"]
	direct =  obj["dir"] #buy or sell
	wait = obj["wait"]
	wait_time = 7

	high = max(vals)
	drop = (high - vals[-1]) / high*100

	low = min(vals)
	rise = (low - vals[-1])/low*100

	if(abs(drop)>change_min and direct<0):
		if(wait>=wait_time):
			if(np.mean(slopes[-wait_time:])<0):
				collection.update_one({"_id":obj['_id']},{"$set":{"wait":0}})
			else:
				return([drop,'buy'])
		else:
			new_wait = wait+1
			collection.update_one({"_id":obj['_id']},{"$set":{"wait":new_wait}})
			return ([0, 0])
	elif(abs(rise)>change_min and direct>0):
		if(wait>=wait_time):
			if(np.mean(slopes[-wait_time:])>0):
				collection.update_one({"_id":obj['_id']},{"$set":{"wait":0}})
				return ([0, 0])
			else:
				return([rise,'sell'])
		else:
			new_wait = wait+1
			collection.update_one({"_id":obj['_id']},{"$set":{"wait":new_wait}})
			return ([0, 0])
def update():
	# run regularly on minute-by-minute interval
	sell_matrix = []
	buy_matrix = []

	for i in range(len(symb)):
		obj = update_vals(collection.find_one({"_id":symb[i]}))
		dec = decision(obj)
		if(dec[1] == 'sell'):
			sell_matrix.append(dec[0],obj["_id"])
		if(dec[1] == 'buy'):
			buy_matrix.append(dec[0],obj["_id"])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)

	while len(sell_matrix)>0:
		sell(sell_matrix[-1][1])
		print("Selling: %s" % sell_matrix[-1][1])
		sell_matrix.pop()

	#retrieve balances after sell-offs
	balance = 100

	while len(buy_matrix)>0 and balance>0:
		buy(buy_matrix[-1][1])
		print("Buying: %s" % buy_matrix[-1][1])
		buy_matrix.pop()


def loop():
	while(1):
		print('in loop')
		time.sleep(2)
		print('yello')
		if datetime.time(2, 30) <= datetime.datetime.now().time() <= datetime.time(16,30):
			update()
		else:
			print("helo")
if __name__ == "__main__":
	print("moneybags v1")
	loop()
