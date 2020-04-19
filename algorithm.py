import pymongo
from pymongo import MongoClient
import numpy as np
import requests
import json

#things to do:
#add headers for buy and sell --> make functions POST methods
#get account balances
#get access token and account id

#user-input
symb = ['AAPL','NFLX','GOOG','HFC']
frequency = 1 #minutes
track = 60 #minutes tracking
change_min = 0.1 #minimum percentage drop to initiate sequence
wait_time = 7 #minutes to wait if drop is found
account_id = "2010359101" #your account number
access_token = 21924124 #need to get access token

#accessing database
cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["test"]

#initializing values in database
for i in range(len(symb)):
	post = {"_id":symb[i],"vals":[],"slopes":[],"infl":[],"dir":0,"wait":0}
	collection.insert_one(post)

key = 'QMXVMOERHQTU1ISEK7PY0S9JYCZNPLMJ'

def sell(sym):

    # Define endpoint URL
    url = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_id)

    # Create parameters, update api key.
    params = {
		"orderType": "MARKET",
		"session": "NORMAL",
		"duration": "DAY",
		"orderStrategyType": "SINGLE",
		"orderLegCollection": [
			{
				"instruction": "Sell",
				"quantityType": 'ALL_SHARES',
				"quantity":1,
				"instrument": {
					"symbol": sym,
					"assetType": "EQUITY"
				}
			}
		]
	}

    # Create request, with URL and parameters
    return requests.get(url, params=params)

def buy(obj,val):
	# Define endpoint URL
	url = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_id)

	# Create parameters, update api key.
	params = {
		"orderType": "MARKET",
		"session": "NORMAL",
		"duration": "DAY",
		"orderStrategyType": "SINGLE",
		"orderLegCollection": [
			{
				"instruction": "Buy",
				"quantityType": 'DOLLARS',
				"quantity": val,
				"instrument": {
					"symbol": sym,
					"assetType": "EQUITY"
				}
			}
		]
	}

	return requests.get(url,params=params)

def getBalance():
	return 1

def get_quotes(**kwargs):

	# Define endpoint URL
	url = 'https://api.tdameritrade.com/v1/marketdata/quotes'

	# Create parameters, update api key.
	params = {}
	params.update({'apikey': key})

	# Create and fill the symbol_list list with symbols from argument
	symbol_list = [symbol for symbol in kwargs.get('symbol')]
	params.update({'symbol': symbol_list})

	# Create request, with URL and parameters
	return requests.get(url, params=params).json()

def get_price(**kwargs):
	data = get_quotes(symbol=kwargs.get('symbol'))
	for symbol in kwargs.get('symbol'):
		print(symbol)
		print(data[symbol]['lastPrice'])

def update_vals(old):
	vals = old["vals"]
	slopes = old["slopes"]
	infl = old["infl"]

	new_val = get_price(symbol=sym)
	vals.append(new_val)
	new_slope = (vals[len(vals)-1] - vals[len(vals)-2])/vals[len(vals)-2]*100 #percent change in new minute
	slopes.append(new_slope)
	new_infl = (slopes[len(slopes)-1]-slopes[len(slopes)-2])/slopes[len(slopes)-2]*100 #percent change of slopes in new minute
	infl.append(new_infl)
	direct = np.mean(slopes)

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
	direct = obj["dir"]
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

	if(abs(rise)>change_min and direct>0):
		if(wait>=wait_time):
			if(np.mean(slopes[len(slopes)-wait_time:])>0):
				collections.update_one({"_id":obj['_id'],"wait":0})
			else:
				return([rise,'sell'])
		else:
			new_wait = wait+1
			collections.update_one({"_id":obj['_id'],"wait":new_wait})

#run regularly on minute-by-minute interval

sell_matrix = []
buy_matrix = []

for i in range(len(symb)):
	obj = update_vals(collection.find("_id":sym))
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
balance = getBalance()

while len(buy_matrix)>0 and balance>0:
	buy(buy_matrix[len(buy_matrix)-1][1])
	buy_matrix.pop(len(buy_matrix)-1)