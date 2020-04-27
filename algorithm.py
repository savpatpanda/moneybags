import math
import numpy as np
from api import buy, sell, get_quotes, getBalance
import datetime
import time
import sys
import traceback
import sim
import itertools
from db import getCollection, initializeDB, dbLoad, dbPut, logEOD

#things to do:
#fix initialization to revert to commented out get_price_historyc call
#fix pinging and token requests

#balance init
balance = getBalance()
initialBalance = balance

#user-input - 'SSL','VG''WTI',,'SFNC','NGHC'
symb = ['SSL','VG','WTI','SFNC','NGHC','CALM','PBH','HASI','PING','ENSG','SAIA','EVR','PACW','DORM','BAND','PSMT','HFC']
frequency = 1 #minutes
direction_check = 15 #minutes for direction calculator
change_min_buy = 2.5 #minimum percentage drop to initiate buy sequence
change_min_sell = 0.75 #minimum percentage increase from buy point to initiate sell sequence
drop_percent = 0.5 #percentage drop before dropping investment in stock
wait_time_buy = 1
wait_time_sell = 6
SIM = False
active_trading = False
max_proportion = 0.5 #maximum proportion a given equity can occupy in brokerage account
allow_factor = 3 #override factor to buy stock even if max positions is held (e.g. 2x size drop)
max_spend = 0.4*balance #maximum amount of balance to spend in given trading minute in dollars

#accessing database
collection = getCollection()
currentFile = None
db = None

#sim date initialization - optional
#i=13
#startOfSIMInit =int(time.mktime((2020, 4, i, 8, 30, 00, 0, 0, 0))*1000)
#endOfSIMInit = int(time.mktime((2020, 4, i, 21,00, 00, 0, 0, 0))*1000)
#startOfSIMPeriod = int(time.mktime((2020, 4,i+1 , 8, 30, 00, 0, 0, 0))*1000)
#endOfSIMPeriod = int(time.mktime((2020, 4,i+4, 15, 00, 00, 0, 0, 0))*1000)

startOfSIMInit = 1586174400000
endOfSIMInit = 1586217600000
startOfSIMPeriod = 1586260800000
endOfSIMPeriod = 1587758400000

def update_vals(e,new_val):
	global active_trading
	vals, slopes, infl, wait = db[e]["vals"], db[e]["slopes"], db[e]["infl"], db[e]["wait"]

	if SIM and new_val =="Null":
		return None
	elif SIM and new_val =="OPEN":
		active_trading = True
		return None
	elif SIM and new_val =="CLOSE":
		active_trading = False
		return None
	elif SIM:
		new_val = float(new_val)

	if not SIM and new_val is None:
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

def buyDecision(obj,symbol, policy):
	vals, slopes, infl, direct =  obj["vals"], obj["slopes"], obj["infl"], obj["dir"]

	buyThreshold, waitThreshold = change_min_buy, wait_time_buy
	if policy:
		buyThreshold = policy["buy"] if "buy" in policy else buyThreshold
		waitThreshold = policy["bwait"] if "bwait" in policy else waitThreshold


	high = max(vals[:-30]) #maybe incorporate mean - high = max(vals[:-60])
	drop = (vals[-1] - high) / high*100

	if(drop < -buyThreshold):
		if(obj["wait"]>=waitThreshold):
			if(np.mean(slopes[-waitThreshold:])<0):
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

def sellDecision(obj,symbol, policy):
	vals, slopes, infl, direct, existing =  obj["vals"], obj["slopes"], obj["infl"], obj["dir"], db[symbol]["pos"]
	sellThreshold, waitThreshold, dropThreshold = change_min_sell, wait_time_sell, drop_percent
	if policy:
		sellThreshold = policy["sell"] if "sell" in policy else sellThreshold
		waitThreshold = policy["swait"] if "swait" in policy else waitThreshold
		dropThreshold = policy["dropsell"] if "dropsell" in policy else dropThreshold

	if(existing[1]>0):
		numberShares = existing[0]
		avgPrice = existing[1]
		rise = (vals[-1] - avgPrice) / avgPrice * 100
		if(rise < - dropThreshold):
			obj["wait"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[FORCED SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, vals[-1], hldr, vals[-10:], slopes[-10:]))
			return(rise,'sell',numberShares,vals[-1])
		elif(rise > sellThreshold):
			if(obj["wait"]>= waitThreshold):
				if(np.mean(slopes[-waitThreshold:])>0):
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
		buy_matrix[i].append(int(min(round(prop*max_spend*totalRelative/buy_matrix[i][3],4),buy_matrix[i][2])))
	
	return buy_matrix

def updateBalanceAndPosition(symbol,action,quant,price):
	global balance

	if symbol not in db:
		print(symbol)
	elif "pos" not in db[symbol]:
		print(symbol)

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

def update(withPolicy = None):
	global balance
	# run regularly on minute-by-minute interval
	sell_matrix = []
	buy_matrix = []

	stringOfStocks = ','.join(symb)
	quotes = []
	if not SIM:
		quotes = get_quotes(symbol=stringOfStocks)

	for e in range(len(symb)):
		if not SIM: 
			obj = update_vals(symb[e],quotes[e])
		else: 
			obj = update_vals(symb[e],sim.get_quotes(symb[e]))

		if obj is None:
			continue

		if active_trading:
			buyDec = buyDecision(obj,symb[e], withPolicy)
			sellDec = sellDecision(obj,symb[e], withPolicy)
			if(sellDec[1] == 'sell'):
				sell_matrix.append([sellDec[0],symb[e],sellDec[2],sellDec[3]])
			if(buyDec[1] == 'buy'):
				buy_matrix.append([buyDec[0],symb[e],buyDec[2],buyDec[3]])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)
	#buy_matrix = buy_matrix[0:2]

	while len(sell_matrix)>0:
		if(sell_matrix[-1][2]>0.001):
			#sell(sell_matrix[-1][1],sell_matrix[-1][2])
			updateBalanceAndPosition(sell_matrix[-1][1],'sell',0,sell_matrix[-1][3])
			#time.sleep(1)
		sell_matrix.pop()

	if not SIM:
		balance = getBalance()

	#retrieve buy amounts for each listed stock after sell-offs
	buy_matrix = buyAmounts(buy_matrix)

	while len(buy_matrix)>0 and balance>0:
		if(buy_matrix[-1][4]>0.001):
			updateBalanceAndPosition(buy_matrix[-1][1],'buy',buy_matrix[-1][4],buy_matrix[-1][3])
			#buy(buy_matrix[-1][1],buy_matrix[-1][4])
			#time.sleep(1)
		buy_matrix.pop()

def report():
	total_value = balance
	deltas = []
	for i in range(len(symb)):	
		if db[symb[i]]['pos'][1]!=0:
			delta = (db[symb[i]]["vals"][-1]-db[symb[i]]['pos'][1]) / db[symb[i]]['pos'][1] *100
		else:
			delta = 0
		#print(symb[i]+": "+str(delta)+"%")
		total_value = total_value + db[symb[i]]['pos'][0]* db[symb[i]]["vals"][-1] #get_quotes(symbol=symb[i])
	totalChange = (total_value - initialBalance) / total_value *100
	print("Available Funds: $" + str(balance) + "\nTotal Value: $"+str(total_value) + "\nDaily Change: "+str(totalChange)+"%")
	return totalChange

def loop(maxTimeStep = 1e9, withPolicy = None):
	# open today's file
	global currentFile
	global SIM
	currentFile = open(datetime.datetime.now().strftime("%m-%d-%Y.log"), "w")
	i = 1
	while(0 < i < maxTimeStep):
		#if not SIM: time.sleep(60)
		#else: print("at sim time step: %d" % i)
		if datetime.time(9, 30) <= datetime.datetime.now().time() <= datetime.time(16,00) or SIM:
			try:
				update(withPolicy)
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
			i += 1
			if i % 30 == 0 and not SIM:
				currentFile.write("[15 min check in] Current Time: %s\n" % datetime.datetime.now().strftime("%H %M %S"))
				dbPut(db)
		elif datetime.time(16,30) >= datetime.datetime.now().time() > datetime.time(16,00):
			dbPut(db)
			cluster.close()
			currentFile.close()
			exit(1)
	if SIM :
		return report()

def getPolicyScore(policy):
	global db
	global balance
	db = dbLoad()
	balance = initialBalance
	print("EVALUATING: %s" % policy)
	return loop(maxTimeStep = sim.initializeSim(), withPolicy = policy)

def optimizeParams():
	global SIM
	SIM = True
	# buy, bwait
	# sell, swait, dropsell
	
	pb, pbwait = [1.5, 2, 2.5, 3], [1,3,5,7]
	ps, pswait, pds = [0.5, 0.75, 1], [4,6,8], [0.5,1,1.5]

	combinations = itertools.product(pb, pbwait, ps, pswait, pds)
	topPolicy = None
	topScore = 0
	minScore = 1e9
	minPolicy = None

	combinations_store = 'combinations_store.log'

	with open(combinations_store,'w') as f:

		for buy, bwait, sell, swait, dropsell in combinations:
			print("TOP POLICY: %s\nTOP SCORE: %s" % (topPolicy, topScore))
			m = {"buy": buy, "bwait": bwait, "sell": sell, "swait": swait, "dropsell": dropsell}
			currentScore = getPolicyScore(m)
			print(m)
			print("score output: %s" % currentScore)
			if (currentScore > topScore):
				topPolicy = m
				topScore = currentScore
			if (currentScore < minScore):
				minPolicy = m
				minScore = currentScore
			f.write("\nPolicy: %s\nscore: %s\n" % (m, currentScore))

		f.write("\nfound top policy: %s\nscore: %s\n" % (topPolicy, topScore))
		f.write("\nfound min policy: %s\nmin score: %s" % (minPolicy, minScore))
		f.close()

if __name__ == "__main__":
	collection.delete_many({})
	print("moneybags v1")
	if len(sys.argv) > 1:
		SIM = True
		initializeDB(symb, startOfSIMInit, endOfSIMInit, SIM)
		sim.generateSim(symb,startOfSIMPeriod,endOfSIMPeriod)
		db = dbLoad()
		if sys.argv[1] == 'sim':
			loop(maxTimeStep = sim.initializeSim())
		elif sys.argv[1] == 'opt':
			#firstStrat = {"buy": 3, "bwait": 7, "sell":1, "swait":7, "dropsell":0.8}
			#newStrat = {"buy": 2.5, "bwait": 5, "sell": 1, "swait": 6, "dropsell":0.8}
			optimizeParams()
	else:
		initializeDB(symb)
		db = dbLoad()
		loop()
			
