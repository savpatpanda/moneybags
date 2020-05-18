from dotenv import load_dotenv
load_dotenv()
import math
import os
import numpy as np
from api import buy, sell, get_quotes, getBalance, resetToken, checkPosition
import datetime
import time
import graphing
import sys
import traceback
import sim
import itertools
from db import getCollection, initializeDB, dbLoad, dbPut, logEOD, cleanup

#things to do:
#fix initialization to revert to commented out get_price_historyc call
#fix pinging and token requests

#user-input 
symb = ['AA', 'AAL', 'AAN', 'ABB', 'ABR', 'ACBI', 'ACHC', 'ACIU', 'ADES', 'ADTN', 'ADVM', 'AFIN', 'AFL', 'AGI', 'AGNC', 'AM', 'ANAB', 'APA', 'AZUL', 'BAND', 'BCRX', 'BEN', 'BSX', 'BXC', 'CAL', 'CALM', 'CCL', 'CLF', 'CLI', 'CLR', 'CMCSA', 'CNP', 'CSCO', 'CVM', 'CYTK', 'DBVT', 'DDS', 'DEI', 'DFIN', 'DFS', 'DORM', 'DVN', 'ENSG', 'EVR', 'F', 'FCX', 'FITB', 'FOLD', 'FRO', 'GDOT', 'GDV', 'GE', 'GFF', 'GGAL', 'GLAD', 'GLDD', 'GLOP', 'GLPI', 'GM', 'GPS', 'HAL', 'HASI', 'HBAN', 'HFC', 'HPQ', 'HST', 'IBN', 'IGA', 'IMO', 'IVZ', 'KGC', 'KIM', 'LUV', 'M', 'MD', 'MEET', 'MRO', 'MYL', 'NG', 'NGHC', 'NLY', 'OFC', 'OFG', 'OI', 'OLP', 'OMF', 'ONEM', 'OPRA', 'OR', 'OSPN', 'OSTK', 'OUT', 'OVV', 'OXY', 'PAAS', 'PACW', 'PBH', 'PCG', 'PENN', 'PFE', 'PING', 'PPL', 'PSMT', 'PW', 'RA', 'SAIA', 'SFNC', 'SIRI', 'SLB', 'SM', 'SSL', 'SSP', 'TBI', 'TEAF', 'TFC', 'THC', 'UE', 'UFI', 'USFD', 'VG', 'VHC', 'VIAC', 'WFC', 'WMB', 'WTI', 'WU', 'XOM']
wait_time_volumes = 20
set_back = 0
SIM, REF = False, False
active_trading = False
counter_close = 0
max_proportion = 0.3 #maximum proportion a given equity can occupy in brokerage account
max_spend = 0.2 #maximum amount of balance to spend in given trading minute in dollars
max_spend_rolling = max_spend
max_daily_spend = 0.75
allow_factor = 2 #override factor to buy stock even if max positions is held (e.g. 2x size drop)
declineSell = 0.75
defaultParams = {"buy": 5, "bwait": 20, "sell": 5, "swait": 20, "dropsell": 4, "mspend": 0.2, "mprop": 0.3}

#balance init
balance = getBalance()
initialBalance = balance
spent_today = 0
unsettled_today = 0
unsettled_yday = 0

#accessing database
collection = getCollection()
currentFile = None
db = None

def tradingDay(back):
	midnight = datetime.datetime.combine(datetime.datetime.today(), datetime.time.min) - datetime.timedelta(days = 0)
	if datetime.datetime.now().hour >= 16:
		midnight = midnight + datetime.timedelta(days = 1)
	timeBegin, timeEnd = midnight - datetime.timedelta(hours = 17+24*(back-1)), midnight - datetime.timedelta(hours = 4+24*(back-1))
	bdelta = [timeBegin, timeEnd] 
	if timeBegin.weekday() == 6:
		return tradingDay(back+2)
	elif timeBegin.weekday() == 5:
		return tradingDay(back+1)
	for i in range(len(bdelta)):
		bdelta[i] = int(time.mktime(bdelta[i].timetuple()) * 1e3)
	return bdelta 

starting = 2 #days ago to start SIM
startOfSIMPeriod = tradingDay(starting-1)[0]
endOfSIMPeriod = tradingDay(1)[1]
startOfSIMInit, endOfSIMInit = tradingDay(starting)

def update_vals(symbol,new_val):
	global active_trading, counter_close
	bid, ask, bidSlope, askSlope = db[symbol]["bidPrice"], db[symbol]["askPrice"], db[symbol]["bidSlope"], db[symbol]["askSlope"]
	volume, moving, volumeSlope = db[symbol]["volume"], db[symbol]["moving"], db[symbol]["volumeSlope"]

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

	volume.append(new_val[2])
	moving.append(np.mean(volume[-5:]))
	if moving[-2] ==0:
		newVolSlope = (moving[-1] - moving[-2])/0.000001*100
	else:
		newVolSlope = (moving[-1] - moving[-2])/moving[-2]*100
	volumeSlope.append(newVolSlope)
	
	bid.pop(0)
	ask.pop(0)
	bidSlope.pop(0)
	askSlope.pop(0)
	volume.pop(0)
	moving.pop(0)
	volumeSlope.pop(0)		

	return db[symbol]

def buy_sub_decision(symbol,drop, policy=None):
	mp = max_proportion
	if policy:
		mp = policy["mprop"] if "mprop" in policy else mp
	existing = db[symbol]["pos"]
	cost_basis = existing[0]*existing[1]
	max_buy_dollars = balance*mp - cost_basis
	if(cost_basis>=balance*mp):		
		if(drop < -allow_factor*policy["buy"]):
			return max_buy_dollars
		else:
			return 0
	else:
		return max_buy_dollars

def buyDecision(obj,symbol,policy):
	ask, askSlope, waitB, vol = db[symbol]["askPrice"], db[symbol]["askSlope"], db[symbol]["wait_buy"], db[symbol]["moving"]
	buyThreshold = policy["buy"] 
	waitThreshold = policy["bwait"] 

	high = max(ask[:-30])
	drop = (ask[-1] - high) / high*100
	halfmax = max(vol) * 0.5

	if(drop < -buyThreshold and vol[-1]>halfmax): #
		if(waitB>=waitThreshold):
			if(np.mean(askSlope[-waitThreshold:])<0): 
				db[symbol]["wait_buy"] -= set_back
				return (0,0,0)
			else:
				numberShares = float(round((buy_sub_decision(symbol,drop,policy) / ask[-1]),5))
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
	sellThreshold = policy["sell"] 
	waitThreshold = policy["swait"] 
	dropThreshold = policy["dropsell"] 

	if(existing[1]>0):
		numberShares = existing[0]
		avgPrice = existing[1]
		rise = (bid[-1] - avgPrice) / avgPrice * 100
		if(rise > sellThreshold * declineSell):
			db[symbol]["readySell"] = True

		if(rise < - dropThreshold):
			db[symbol]["wait_sell"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[FORCED SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, bid[-1], hldr, bid[-10:], bidSlope[-10:]))
			return(rise,'sell',numberShares,bid[-1])
		elif(rise > sellThreshold):
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
		elif(readySell and rise < sellThreshold * declineSell):
			db[symbol]["wait_sell"] = 0
			hldr = "rise %f" % (rise)
			currentFile.write("[SELL ALERT] : \nCurrent Time: %s\nEquity: %s\nSell Price: %f\nStats:\n\t%s\n\t%s\n\t%s\n" % 
				(datetime.datetime.now().strftime("%H %M %S"), symbol, bid[-1], hldr, bid[-10:], bidSlope[-10:]))
			db[symbol]["readySell"] = False
			return(rise,'sell',numberShares,bid[-1])
		else:
			return (0,0,0)
	else:
		return (0,0,0)

def buyAmounts(buy_matrix, policy=None):
	# do the same check for symb
	# symb = buy_matrix[1]
	# if not REF and ("policy" in db[symb] and db[symb]["policy"] is not None):
	# 	policy = db[symb]["policy"] # this probably won't be relevant, mspend and mprop will have to be uniform.
	ms = max_spend
	if policy:
		ms = policy["mspend"] if "mspend" in policy else ms
	sum_drops = 0
	for i in range(len(buy_matrix)):
		sum_drops = sum_drops + buy_matrix[i][0]
	if sum_drops >0:
		totalRelative = 1 - (defaultParams["buy"]/sum_drops)
	else:
		totalRelative = 1
	for i in range(len(buy_matrix)):
		prop = buy_matrix[i][0] / sum_drops
		buy_matrix[i].append(int(min(round(prop*ms*balance*totalRelative/buy_matrix[i][3],4),buy_matrix[i][2])))
	
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
				# tc = report()[1]
				# graphing.app(tc)
				dump()
		else:
			balance = balance + unsettled_today + unsettled_yday
			unsettled_today = 0
			unsettled_yday = 0

def updateBalanceAndPosition(symbol,action,quant,price):
	global balance, unsettled_today, unsettled_yday, spent_today

	pos = db[symbol]["pos"]
	old_quant = pos[0]
	old_price = pos[1]
	if(action=='buy'):
		balance = balance - quant*price
		new_quant = old_quant + quant
		new_price = (old_quant*old_price+quant*price) / new_quant
		spent_today += new_quant*new_price
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
	global balance, SIM, max_spend_rolling
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
		defPolicy = withPolicy
		# check if optimal policy exists, otherwise use default
		if not REF and ("policy" in db[symb[e]] and db[symb[e]]["policy"] is not None):
			defPolicy = db[symb[e]]["policy"]
		elif defPolicy is None: #defPolicy must be populated
			defPolicy = defaultParams

		if active_trading or not SIM:
			buyDec = buyDecision(obj,symb[e], defPolicy)
			sellDec = sellDecision(obj,symb[e], defPolicy)
			if(sellDec[1] == 'sell'):
				sell_matrix.append([sellDec[0],symb[e],sellDec[2],sellDec[3]])
			if(buyDec[1] == 'buy'):
				buy_matrix.append([buyDec[0],symb[e],buyDec[2],buyDec[3]])

	sell_matrix = sorted(sell_matrix)
	buy_matrix = sorted(buy_matrix)
	buy_matrix = buy_matrix[0:2]

	while len(sell_matrix)>0:
		if(sell_matrix[-1][2]>0.001):
			updateBalanceAndPosition(sell_matrix[-1][1],'sell',0,sell_matrix[-1][3])
			if not SIM:
				resetToken()
				token_change = True
				time.sleep(1)
				sell(sell_matrix[-1][1],sell_matrix[-1][2])
		sell_matrix.pop()

	if not SIM and len(buy_matrix)>0:
		if not token_change:
			resetToken()
		balance = getBalance()

	#retrieve buy amounts for each listed stock after sell-offs
	buy_matrix = buyAmounts(buy_matrix, withPolicy)

	if len(buy_matrix)>0:
		max_spend_rolling -= 0.1

	while len(buy_matrix)>0 and balance>0:
		if(buy_matrix[-1][4]>0.001):
			if spent_today < max_daily_spend * initialBalance:
				updateBalanceAndPosition(buy_matrix[-1][1],'buy',buy_matrix[-1][4],buy_matrix[-1][3])
				if not SIM: 
					time.sleep(1)
					buy(buy_matrix[-1][1],buy_matrix[-1][4])
		buy_matrix.pop()

def dump():
	resetToken()
	for sym in symb:
		position = checkPosition(sym)
		lastBid = db[sym]['bidPrice'][-1]
		if position[0] > 0:
			if not SIM: 
				time.sleep(1)
				sell(sym,position[0])
			updateBalanceAndPosition(sym, 'sell', position[0], lastBid)
	
def report():
	total_value = balance
	deltas = []
	for e in symb:	
		lastBid = db[e]["bidPrice"][-1] # Error Check this <--, got null sometimes
		secondPos = db[e]['pos'][1]
		firstPos = db[e]['pos'][0]
		if secondPos !=0:
			delta = (lastBid - secondPos) / secondPos *100
		else:
			delta = 0
		total_value = total_value + firstPos * lastBid #get_quotes(symbol=symb[i])
	total_value = total_value + unsettled_yday +unsettled_today
	totalChange = (total_value - initialBalance) / total_value *100
	if not REF:
		print("Available Funds: $" + str(balance) + "\nTotal Value: $"+str(total_value) + "\nDaily Change: "+str(totalChange)+"%")
	return (totalChange, total_value)

def loop(maxTimeStep = 1e9, withPolicy = None):
	# open today's file
	global currentFile
	global SIM
	global active_trading
	global max_spend_rolling
	currentFile = open(datetime.datetime.now().strftime("%m-%d-%Y.log"), "w")
	i = 1
	while(0 < i < maxTimeStep):
		if not SIM: time.sleep(60)
		if datetime.time(9, 30) <= datetime.datetime.now().time() <= datetime.time(15,57) or SIM:
			try:
				balanceUpdater()
				update(withPolicy)
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
		elif datetime.time(7, 00) <= datetime.datetime.now().time() < datetime.time(9,30):
			try:
				updatePreMarket()
			except Exception as e:
				currentFile.write("\n\nReceived Exception at %s\n:%s\n" % (datetime.datetime.now().strftime("%H %M %S"), traceback.format_exc()))
		elif datetime.time(15,57) <= datetime.datetime.now().time() < datetime.time(16,30):
			dump()
			dbPut(db)
			# refreshPolicies()
			cleanup()
			currentFile.close()
			logEOD()
			max_spend_rolling = max_spend
			exit(1)
		i += 1
		if i % 20 == 0 and not SIM:
			resetToken()
			currentFile.write("[20 min check in] Current Time: %s\n" % datetime.datetime.now().strftime("%H %M %S"))
			dbPut(db)

	if SIM :
		currentFile.close()
		balanceUpdater(endofterm = True)
		ret = report()[0]
		#if ret > -2:
		#graphing.graph(withPolicy)
		return ret

def getPolicyScore(policy):
	global db
	global balance, counter_close, active_trading, unsettled_today, unsettled_yday, max_spend_rolling
	dbCopy = db.copy()
	balance = initialBalance
	unsettled_yday = 0
	unsettled_today = 0
	counter_close = 0
	max_spend_rolling = policy['mspend']
	active_trading = False
	#print("EVALUATING: %s" % policy)
	ret = loop(maxTimeStep = sim.initializeSim(), withPolicy = policy)
	db = dbCopy
	return ret

def optimizeParams() -> map:
	global SIM
	SIM = True
	# buy, bwait
	# sell, swait, dropsell
	# maxspend, maxproportion

	pb, pbwait = [3,5,7], [20]
	ps, pswait, pds = [3,5,7], [20], [4]
	pms, pmp = [0.2], [0.3]

	combinations = itertools.product(pb, pbwait, ps, pswait, pds, pms, pmp)
	topPolicy = None
	topScore = -1e9 # needs floor
	minScore = 1e9 # needs ceiling
	minPolicy = None

	combinations_store = 'combinations_store.log'

	with open(combinations_store,'w') as f:

		for buy, bwait, sell, swait, dropsell, ms, mp in combinations:
			#print("TOP POLICY: %s\nTOP SCORE: %s" % (topPolicy, topScore))
			m = {"buy": buy, "bwait": bwait, "sell": sell, "swait": swait, "dropsell": dropsell, "mspend": ms, "mprop": mp}
			currentScore = getPolicyScore(m)
			# print(m)
			# print("score output: %s" % currentScore)
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

		if topScore <= 0: 
			return defaultParams
		else:
			return topPolicy

def optimizeEquity(symbol) -> map:
	global symb
	symb = [symbol]
	return optimizeParams()

# time in epoch
def refreshPolicies():
	global SIM, symb
	cp = symb.copy()
	SIM = True
	m = {}
	with open('refreshedPolicies.log', 'w') as f:
		for sym in cp:
			res = optimizeEquity(sym)
			f.write("%s: %s\n" % (sym, res))
			print("%s: %s\n" % (sym, res))
			m[sym] = { "policy": res }
			dbPut(m)
			m = {}
		f.close()
	symb = cp

def prepareSim(initStart=startOfSIMInit, initEnd=endOfSIMInit, timeStart = startOfSIMPeriod, timeEnd = endOfSIMPeriod):
	global SIM, db, balance, initialBalance
	balance = 300
	initialBalance = 300
	SIM = True
	print("Preparing with init: %d-%d, sim: %d-%d" % (initStart, initEnd, timeStart, timeEnd))
	initializeDB(symb, initStart, initEnd, SIM)
	time.sleep(1)
	sim.generateSim(symb, timeStart, timeEnd)
	db = dbLoad()

if __name__ == "__main__":
	print("moneybags v1")
	if len(sys.argv) > 1:
		if sys.argv[1] == 'sim':
			prepareSim()
			loop(maxTimeStep = sim.initializeSim())
		elif sys.argv[1] == 'opt':
			prepareSim()
			optimizeParams()
		elif sys.argv[1] == 'ref':
			REF = True
			backtrack = 3
			endOfREFPeriod = tradingDay(1)[1]
			startOfREFPeriod = endOfREFPeriod - 46800000 - (backtrack-1)*86400000
			startOfREFInit = startOfSIMPeriod - 86400000
			endOfREFInit = startOfREFInit + 46800000
			collection.delete_many({})
			prepareSim(initStart = startOfREFInit, initEnd = endOfREFInit, timeStart = startOfREFPeriod, timeEnd = endOfREFPeriod)
			refreshPolicies()
	else:
		twoDayStart, twoDayEnd = tradingDay(2)
		prevDayStart, prevDayEnd = tradingDay(1)
		initializeDB(symb,start=twoDayStart,end=prevDayEnd)
		db = dbLoad()
		loop()
