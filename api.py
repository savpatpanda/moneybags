import requests
import json

account_id = "2010359101" #your account number
access_token = 21924124 #need to get access token
key = 'QMXVMOERHQTU1ISEK7PY0S9JYCZNPLMJ'

def createParams(instruction, symbol, quantityType, quantity = 1):
	params = {
		"orderType": "MARKET",
		"session": "NORMAL",
		"duration": "DAY",
		"orderStrategyType": "SINGLE",
		"orderLegCollection": [
			{
				"instruction": instruction,
				"quantityType": quantityType,
				"quantity": quantity,
				"instrument": {
					"symbol": symbol,
					"assetType": "EQUITY"
				}
			}
		]
	}
	return params

def execAPI(instruction):
	url = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_id)
	return requests.get(url, params = params)

def sell(sym):
	return execAPI(createParams("Sell", sym, "ALL_SHARES"))

def buy(sym,val):
	# Define endpoint URL
	return execAPI(createParams("Buy", sym, "DOLLARS", val))

def get_quotes(**kwargs):
	# Define endpoint URL
	url = 'https://api.tdameritrade.com/v1/marketdata/quotes'

	# Create parameters, update api key.
	params = {}
	params.update({'apikey': key})
	# Create and fill the symbol_list list with symbols from argument
	params.update({'symbol': [symbol for symbol in kwargs.get('symbol')]})

	# Create request, with URL and parameters
	return requests.get(url, params=params).json()