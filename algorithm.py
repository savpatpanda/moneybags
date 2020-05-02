import math
import numpy as np
from api import buy, sell, get_quotes, getBalance, resetToken
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
unsettled_today = 0
unsettled_yday = 0

#user-input - 'SSL','VG''WTI',,'SFNC','NGHC'
symb = ['SSL','VG','WTI','SFNC','NGHC','CALM','PBH','HASI','PING','ENSG','SAIA','EVR','PACW','DORM','BAND','PSMT','HFC']
change_min_buy = 3 #minimum percentage drop to initiate buy sequence
change_min_sell = 3 #minimum percentage increase from buy point to initiate sell sequence
drop_percent = 3 #percentage drop before dropping investment in stock
wait_time_buy = 50
wait_time_sell = 70
set_back = 0
SIM = False
active_trading = False
counter_close = 0
max_proportion = 0.6 #maximum proportion a given equity can occupy in brokerage account
allow_factor = 2 #override factor to buy stock even if max positions is held (e.g. 2x size drop)
max_spend = 0.4 #maximum amount of balance to spend in given trading minute in dollars

#accessing database
collection = getCollection()
currentFile = None
db = None

#sim date initialization - optional
startOfSIMInit = 1587988800000
endOfSIMInit = 1588032000000
startOfSIMPeriod = 1588075200000
endOfSIMPeriod = 1588276800000

def update_vals(symbol,new_val):
	global active_trading, counter_close
	bid, ask, bidSlope, askSlope = db[symbol]["bidPrice"], db[symbol]["askPrice"], db[symbol]["bidSlope"], db[symbol]["askSlope"]

	if not SIM and new_val is None:
		currentFile.write("get_quotes returned null for %s\n" % symbol)
		return new_val

	if SIM and new_val == None:
		return None
	elif SIM and new_val[0] =="Null":
		return None
	elif SIM and new_val[0] =="OPEN":
		active_trading = True
		return None
	elif SIM and new_val[0] =="CLOSE":
		active_trading = False
		counter_close = counter_close + 1
		return None

	bid.append(new_val[0])
	newBidSlope = (bid[-1] - bid[-2])/bid[-2]*100
	bidSlope.append(newBidSlope)

	ask.append(new_val[1])
	newAskSlope = (ask[-1] - ask[-2])/ask[-2]*100
	askSlope.append(newAskSlope)

	bid.pop(0)
	ask.pop(0)
	bidSlope.pop(0)
	askSlope.pop(0)

	return db[symbol]

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
	ask, askSlope, waitB = db[symbol]["askPrice"], db[symbol]["askSlope"], db[symbol]["wait_buy"]

	buyThreshold, waitThreshold = change_min_buy, wait_time_buy
	if policy:
		buyThreshold = policy["buy"] if "buy" in policy else buyThreshold
		waitThreshold = policy["bwait"] if "bwait" in policy else waitThreshold

	high = max(ask[:-30])
	drop = (ask[-1] - high) / high*100

	if(drop < -buyThreshold):
		if(waitB>=waitThreshold):
			if(np.mean(askSlope[-waitThreshold:])<0):
				db[symbol]["wait_buy"] -= set_back
				return (0,0,0)
			else:
				numberShares = float(round((buy_sub_decision(symbol,drop) / ask[-1]),5))
				if(numberShares>0):
					db[symbol]["wait_buy"] = 0
					hldr = "high : %d, drop %f" % (high, drop)
					currentFile.write("[BUY ALERT] : \nCurrent Time: %s\nEquity: %s\nBuy Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
						(datetime.datetime.now().strftime("%H %M %S"), symbol, ask[-1], hldr, ask[-10:], askSlope[-10:]))
					return(drop,'buy',numberShares,ask[-1])
				else:
					db[symbol]["wait_buy"] = 0
					return (0,0,0)
		else:
			#print("increasing wait")
			db[symbol]["wait_buy"] += 1
			return (0,0,0)
	else:
		return (0,0,0)

def sellDecision(obj,symbol, policy):
	bid, bidSlope, waitS, existing, readySell = db[symbol]["bidPrice"], db[symbol]["bidSlope"], db[symbol]["wait_sell"], db[symbol]["pos"], db[symbol]["readySell"]
	sellThreshold, waitThreshold, dropThreshold = change_min_sell, wait_time_sell, drop_percent
	if policy:
		sellThreshold = policy["sell"] if "sell" in policy else sellThreshold
		waitThreshold = policy["swait"] if "swait" in policy else waitThreshold
		dropThreshold = policy["dropsell"] if "dropsell" in policy else dropThreshold

	if(existing[1]>0):
		numberShares = existing[0]
		avgPrice = existing[1]
		rise = (bid[-1] - avgPrice) / avgPrice * 100
		if(rise < - dropThreshold):
			db[symbol]["wait_sell"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[FORCED SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, bid[-1], hldr, bid[-10:], bidSlope[-10:]))
			return(rise,'sell',numberShares,bid[-1])
		elif(rise > sellThreshold):
			db[symbol]["readySell"] = True
			if(waitS>= waitThreshold):
				if(np.mean(bidSlope[-waitThreshold:])>0):
					db[symbol]["wait_sell"] -= set_back
					return (0,0,0)
				else:
					db[symbol]["wait_sell"] = 0
					hldr = "rise %f" % (rise)
					currentFile.write("[SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
						(datetime.datetime.now().strftime("%H %M %S"), symbol, bid[-1], hldr, bid[-10:], bidSlope[-10:]))
					db[symbol]["readySell"] = False
					return(rise,'sell',numberShares,bid[-1])
			else:
				#print("increasing wait")
				db[symbol]["wait_sell"] += 1
				return (0, 0,0)
		elif(readySell):
			db[symbol]["wait_sell"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, bid[-1], hldr, bid[-10:], bidSlope[-10:]))
			readySell = False
			return(rise,'sell',numberShares,bid[-1])
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
		buy_matrix[i].append(int(min(round(prop*max_spend*balance*totalRelative/buy_matrix[i][3],4),buy_matrix[i][2])))
	
	return buy_matrix

def balanceUpdater(endofterm = False):
	global balance, unsettled_today, unsettled_yday, counter_close
	if SIM:
		if not endofterm:
			if not active_trading and counter_close == len(symb):
				balance = balance + unsettled_yday
				unsettled_yday = unsettled_today
				unsettled_today = 0
				counter_close = 0
				report()
		else:
			balance = balance + unsettled_today + unsettled_yday
			unsettled_today = 0
			unsettled_yday = 0

def updateBalanceAndPosition(symbol,action,quant,price):
	global balance, unsettled_today, unsettled_yday

	pos = db[symbol]["pos"]
	old_quant = pos[0]
	old_price = pos[1]
	if(action=='buy'):
		balance = balance - quant*price
		new_quant = old_quant + quant
		new_price = (old_quant*old_price+quant*price) / new_quant
		db[symbol]["pos"] = (new_quant,new_price)
	else:
		if SIM:
			unsettled_today = unsettled_today + old_quant*price
		else:
			balance = balance + old_quant*price
		db[symbol]["pos"] = (0,0)

def updatePreMarket():
	stringOfStocks = ','.join(symb)
	quotes = []
	quotes = get_quotes(symbol=stringOfStocks)

	for e in range(len(symb)):
		obj = update_vals(symb[e],quotes[e])

		if obj is None:
			continue

def update(withPolicy = None):
	global balance
	token_change = False
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

		if active_trading or not SIM:
			buyDec = buyDecision(obj,symb[e], withPolicy)
			sellDec = sellDecision(obj,symb[e], withPolicy)
			if(sellDec[1] == 'sell'):
				sell_matrix.append([sellDec[0],symb[e],sellDec[2],sellDec[3]])
			if(buyDec[1] == 'buy'):
				buy_matrix.append([buyDec[0],symb[e],buyDec[2],buyDec[3]])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)
	buy_matrix = buy_matrix[0:1]

	while len(sell_matrix)>0:
		if(sell_matrix[-1][2]>0.001):
			resetToken()
			token_change = True
			sell(sell_matrix[-1][1],sell_matrix[-1][2])
			updateBalanceAndPosition(sell_matrix[-1][1],'sell',0,sell_matrix[-1][3])
			time.sleep(1)
		sell_matrix.pop()

	if not SIM and len(buy_matrix)>0:
		if not token_change:
			resetToken()
		balance = getBalance()

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
			delta = (db[symb[i]]["bidPrice"][-1]-db[symb[i]]['pos'][1]) / db[symb[i]]['pos'][1] *100
		else:
			delta = 0
		total_value = total_value + db[symb[i]]['pos'][0]* db[symb[i]]["bidPrice"][-1] #get_quotes(symbol=symb[i])
	total_value = total_value + unsettled_yday +unsettled_today
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
		if not SIM: time.sleep(60)
		else: print("at sim time step: %d" % i)
		if datetime.time(9, 30) <= datetime.datetime.now().time() <= datetime.time(16,00) or SIM:
			try:
				balanceUpdater()
				update(withPolicy)
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
			i += 1
			if i % 20 == 0 and not SIM:
				currentFile.write("[20 min check in] Current Time: %s\n" % datetime.datetime.now().strftime("%H %M %S"))
				dbPut(db)
		elif datetime.time(7, 00) <= datetime.datetime.now().time() < datetime.time(9,30):
			try:
				updatePreMarket()
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
			i += 1
			if i % 20 == 0:
				resetToken()
				currentFile.write("[20 min check in] Current Time: %s\n" % datetime.datetime.now().strftime("%H %M %S"))
				dbPut(db)
		elif datetime.time(16,30) >= datetime.datetime.now().time() > datetime.time(16,00):
			dbPut(db)
			currentFile.close()
			logEOD()
			exit(1)
	if SIM :
		balanceUpdater(endofterm = True)
		return report()

def getPolicyScore(policy):
	global db
	global balance, counter_close, active_trading
	db = dbLoad()
	balance = initialBalance
	counter_close = 0
	active_trading = False
	print("EVALUATING: %s" % policy)
	return loop(maxTimeStep = sim.initializeSim(), withPolicy = policy)

def optimizeParams():
	global SIM
	SIM = True
	# buy, bwait
	# sell, swait, dropsell
	
	pb, pbwait = [1,2,3], [10,20,30]
	ps, pswait, pds = [2,3], [30,40,50], [2,3]

	#pb, pbwait = [1.5, 2, 2.5, 3], [1,3,5,7]
	#ps, pswait, pds = [0.5, 0.75, 1], [4,6,8], [0.5,1,1.5]

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