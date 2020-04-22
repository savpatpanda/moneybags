import math
import pymongo
from pymongo import MongoClient
import numpy as np
from api import buy, sell, get_quotes, getBalance, checkPosition, get_price_history
from simDataNew import newSIMData
import datetime
import time
import sys
import traceback
import sim
import collections

#things to do:
#fix initialization to revert to commented out get_price_historyc call
#fix pinging and token requests

#user-input
symb = ['AAPL','NFLX','GOOG','GS','MSFT','FB','IBM','XOM','INTC','GE','AMZN','MRK','TRV','WTI']
frequency = 1 #minutes
track = 360 #minutes tracking
direction_check = 15 #minutes for direction calculator
change_min_buy = 3 #minimum percentage drop to initiate buy sequence
change_min_sell = 1 #minimum percentage increase from buy point to initiate sell sequence
drop_percent = 0.8 #percentage drop before dropping investment in stock
wait_time_buy = 7
wait_time_sell = 7
SIM = False
max_proportion = 0.4 #maximum proportion a given equity can occupy in brokerage account
allow_factor = 3 #override factor to buy stock even if max positions is held (e.g. 2x size drop)
balance = getBalance()
initialBalance = balance
max_spend = 0.15*balance #maximum amount of balance to spend in given trading minute in dollars

#accessing database
cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["test"]
currentFile = None
db = None

''' sim date initialization
i=20
yday =int(time.mktime((2020, 4, i, 8, 30, 00, 0, 0, 0))*1000)
yday_end = int(time.mktime((2020, 4, i, 21,00, 00, 0, 0, 0))*1000)
today = int(time.mktime((2020, 4,i+1 , 8, 30, 00, 0, 0, 0))*1000)
end_of_week = int(time.mktime((2020, 4,i+1 , 21, 00, 00, 0, 0, 0))*1000)
newSIMData(symb,today,end_of_week)
'''

def initializeDB():
	#initializing values in database
	for i in range(len(symb)):
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,periodType='day',period=1)
		#obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,endDate=yday_end,startDate=yday)
		time.sleep(1)
		max_length = len(obj)

		v = []
		for j in range(track):
			v.append(float(obj[max_length-track+j]['close']))

		s = []
		inflections = []

		for j in range(len(v)-1):
			slope = (v[j+1]-v[j])/v[j]*100
			s.append(slope)

		d = np.mean(s)

		for j in range(len(s)-1):
			if(s[j]==0):
				inf = (s[j+1]-s[j])/0.000001*100
			else:
				inf = (s[j+1]-s[j])/s[j]*100
			inflections.append(inf)
		pos = checkPosition(symb[i])

		post = {"_id":symb[i],"vals":v,"slopes":s,"infl":inflections,"dir":d,"wait":0,"wait_sell":0,"pos":pos}
		collection.insert_one(post)

def dbLoad() -> collections.defaultdict:
	m = collections.defaultdict(lambda: {})
	cursor = collection.find({})
	for doc in cursor:
		equity = doc['_id']
		for key, value in doc.items():
			if key != '_id':
				m[equity][key] = value
	return m

def dbPut(db):
	for key, value in db.items():
		collection.update_one({"_id": key}, {"$set": value})

def update_vals(e):
	vals, slopes, infl, wait = db[e]["vals"], db[e]["slopes"], db[e]["infl"], db[e]["wait"]

	new_val = get_quotes(symbol=e) if not SIM else sim.get_quotes(e)
	if new_val is None:
		currentFile.write("get_quotes returned null for %s\n" % e)
		return new_val

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

	return db[e]

def buy_sub_decision(symbol,drop):
	existing = db[symbol]["pos"]
	cost_basis = existing[0]*existing[1]
	max_buy_dollars = balance*max_proportion - cost_basis
	if(cost_basis>=balance*max_proportion):		
		if(drop < -allow_factor*change_min_buy):
			return max_buy_dollars
		else:
			return 0
	else:
		return max_buy_dollars

def buyDecision(obj,symbol):
	vals =  obj["vals"]
	slopes =  obj["slopes"]
	infl =  obj["infl"]
	direct =  obj["dir"]

	high = max(vals[:-30]) #maybe incorporate mean
	drop = (vals[-1] - high) / high*100

	if(drop < -change_min_buy):
		if(obj["wait"]>=wait_time_buy):
			if(np.mean(slopes[-wait_time_buy:])<0):
				obj["wait"] = 0
				return (0,0,0)
			else:
				numberShares = float(round((buy_sub_decision(symbol,drop) / vals[-1]),5))
				if(numberShares>0):
					obj["wait"] = 0
					hldr = "high : %d, drop %f" % (high, drop)
					currentFile.write("[BUY ALERT] : \nCurrent Time: %s\nEquity: %s\nBuy Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
						(datetime.datetime.now().strftime("%H %M %S"), symbol, vals[-1], hldr, vals[-10:], slopes[-10:]))
					return(drop,'buy',numberShares,vals[-1])
				else:
					obj["wait"] = 0
					return (0,0,0)
		else:
			#print("increasing wait")
			obj["wait"] += 1
			return (0,0,0)
	else:
		return (0,0,0)

def sellDecision(obj,symbol):
	vals =  obj["vals"]
	slopes =  obj["slopes"]
	infl =  obj["infl"]
	direct =  obj["dir"]
	existing = db[symbol]["pos"]
	if(existing[1]>0):
		numberShares = existing[0]
		avgPrice = existing[1]
		rise = (vals[-1] - avgPrice) / avgPrice * 100
		if(rise < -drop_percent):
			obj["wait"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[FORCED SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, vals[-1], hldr, vals[-10:], slopes[-10:]))
			return(rise,'sell',numberShares,vals[-1])
		elif(rise > change_min_sell):
			if(obj["wait"]>=wait_time_sell):
				if(np.mean(slopes[-wait_time_sell:])>0):
					obj["wait"] = 0
					return (0,0,0)
				else:
					obj["wait"] = 0
					hldr = "rise %f" % (rise)
					currentFile.write("[SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
						(datetime.datetime.now().strftime("%H %M %S"), symbol, vals[-1], hldr, vals[-10:], slopes[-10:]))
					return(rise,'sell',numberShares,vals[-1])
			else:
				#print("increasing wait")
				obj["wait"] += 1
				return (0, 0,0)
		else:
			return (0,0,0)
	else:
		return (0,0,0)

def buyAmounts(buy_matrix):
	sum_drops = 0
	for i in range(len(buy_matrix)):
		sum_drops = sum_drops + buy_matrix[i][0]
	if sum_drops >0:
		totalRelative = 1 - (change_min_buy/sum_drops)
	else:
		totalRelative = 1
	for i in range(len(buy_matrix)):
		prop = buy_matrix[i][0] / sum_drops
		buy_matrix[i].append(min(round(prop*max_spend*totalRelative/buy_matrix[i][3],4),buy_matrix[i][2]))
	
	return buy_matrix

def updateBalanceAndPosition(symbol,action,quant,price):
	global balance
	old = db[symbol]["pos"]
	old_quant = old[0]
	old_price = old[1]
	if(action=='buy'):
		balance = balance - quant*price
		new_quant = old_quant + quant
		new_price = (old_quant*old_price+quant*price) / new_quant
		db[symbol]["pos"] = (new_quant,new_price)
	else:
		balance = balance + old_quant*price
		db[symbol]["pos"] = (0,0)

def update():
	# run regularly on minute-by-minute interval
	sell_matrix = []
	buy_matrix = []

	for e in symb:
		obj = update_vals(e)
		if obj is None:
			continue
		buyDec = buyDecision(obj,e)
		sellDec = sellDecision(obj,e)
		if(sellDec[1] == 'sell'):
			sell_matrix.append([sellDec[0],e,sellDec[2],sellDec[3]])
		if(buyDec[1] == 'buy'):
			buy_matrix.append([buyDec[0],e,buyDec[2],buyDec[3]])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)

	while len(sell_matrix)>0:
		if(sell_matrix[-1][2]>0.001):
			sell(sell_matrix[-1][1],sell_matrix[-1][2])
			updateBalanceAndPosition(sell_matrix[-1][1],'sell',0,sell_matrix[-1][3])
			time.sleep(1)
		sell_matrix.pop()

	#retrieve buy amounts for each listed stock after sell-offs
	buy_matrix = buyAmounts(buy_matrix)

	while len(buy_matrix)>0 and balance>0:
		if(buy_matrix[-1][4]>0.001):
			updateBalanceAndPosition(buy_matrix[-1][1],'buy',buy_matrix[-1][4],buy_matrix[-1][3])
			buy(buy_matrix[-1][1],buy_matrix[-1][4])
			time.sleep(1)
		buy_matrix.pop()

def report():
	total_value = balance
	deltas = []
	for i in range(len(symb)):	
		if db[symb[i]]['pos'][1]!=0:
			delta = (db[symb[i]]["vals"][-1]-db[symb[i]]['pos'][1]) / db[symb[i]]['pos'][1] *100
		else:
			delta = 0
		print(symb[i]+": "+str(delta)+"%"+"\n")
		total_value = total_value + db[symb[i]]['pos'][0]*get_quotes(symbol=symb[i])
	totalChange = (total_value - initialBalance) / total_value *100
	print("Available Funds: $" + str(balance) + "\nTotal Value: $"+str(total_value) + "\nDaily Change: "+str(totalChange)+"%")

def loop():
	# open today's file
	global currentFile
	global SIM
	currentFile = open(datetime.datetime.now().strftime("%m-%d-%Y.log"), "w")
	i = 1
	while(i > 0):
		if not SIM: time.sleep(60)
		else: print("at sim time step: %d" % i)
		print('hi')
		if datetime.time(9, 30) <= datetime.datetime.now().time() <= datetime.time(16,00) or SIM:
			try:
				update()
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
			i += 1
			if SIM and i==400:
				report()
				exit(1)
			if i % 30 == 0:
				currentFile.write("[15 min check in] Current Time: %s\n" % datetime.datetime.now().strftime("%H %M %S"))
				dbPut(db)
		elif datetime.datetime.now().time() > datetime.time(16,00):
			dbPut(db)
			cluster.close()
			currentFile.close()
			exit(1)

if __name__ == "__main__":
	collection.delete_many({})
	initializeDB()
	db = dbLoad()
	print("moneybags v1")

	if len(sys.argv) > 1:
		if sys.argv[1] == 'sim':
			sim.initializeSim()
			SIM = True

	loop()