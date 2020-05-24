import os
import requests
import time
from twilio.rest import Client

account_id = os.getenv("TD_ID") # 454685471" #your account number
key = os.getenv("TD_KEY") # 'QMXVMOERHQTU1ISEK7PY0S9JYCZNPLMJ'

#twilio
twilio_ID = os.getenv("TWIL_ID") # 'AC5af8facef33613c1aa4444e1d2685283'
twilio_auth_token = os.getenv("TWIL_TOKEN") # '94a1997923f36296861a16944a47c1f8'
client = Client(twilio_ID,twilio_auth_token)


def getToken(key):
	url = r"https://api.tdameritrade.com/v1/oauth2/token"
	headers = {
		'Content-Type': 'application/x-www-form-urlencoded',
		'cache-control': 'no-cache'
	}
	params = {
		"grant_type":'refresh_token',
		"refresh_token":'UNG9qUd148KVE+eUwqTUr221/BlFritvVlYKpuPhkuu0hYQ5YkdmKhsz+Znnx7ttvEBskgBVRrM7K8GXk+GOdGDQELfNPXcdW+ij1TZJXNuRLJhOted9qQY2qFpWQB8YV7V98rE/xb74bEv5xIOkQJKL6PzzKUVgnK8oolAD5ohnlArGRNz5Ubp3x9nPgWIJxio4biKDwoWvtWDClPQW4GA8YHmG92EpCWmT12WGxbt7jGkQeOp3nGVU+ZgsvXgoBMn/ZvWQ/kSA8lvZhxW4Qnymt8cnoRseA5315lF6We01kys/YN8DEPIAQRjRfYJjUv4arw3nQqQslIKhVg+g3aZzANDQx0xCpI/SEAbGtPquaJDX5wv6V8EMyZHYksg3obOjjYAcz9sLWq040wmmIknQRfVJDTgDxf7BY5ItJCC2YbHksPNgg/pwVSD100MQuG4LYrgoVi/JHHvl0W57fDOmbQYAuZAumAzaRQtA/9M2uaoi9hIxFUdoysP3yar3D4E+9UPRv5fNXRSULTLDv5nlCROeS6opfSCuADa71ziNsNCjDP7ZpRiKquSRuH+sD/jCystklI2PLc3auOZzCaTNapVwxhovbwOJxEgfGQJ9x7LVgzdZLAYz6mitGdpHc3HTLTTfJkA8h/Bi+Hk5n9Rbg5bLPH+5BFtozfDTXnAFclvz3DQiUia1WF19tEoMd9TZvtC9VMrT8Nb3F7SV3eQd/aF0FFjylhZqANb4IHa16d0/OYMIsPFJkcYnQpmxSya2vfAOKHGamor1YjG2HPp2yMSlTMl33Tc6xUUBsdxhRNtCH01u7vW9OoCfzJhsj8FNKdcy8qtDJ6qN47UkOmH/5XrHc5fToXeajCLwhKwuzCix8Q+/LwO9QzYCVRkmxPEwpLm2OcE=212FD3x19z9sWBHDJACbC00B75E',
		"client_id": key
	}
	obj = requests.post(url,data = params, headers=headers).json()
	if 'access_token' in obj.keys():
		return obj['access_token']
	else:
		time.sleep(3)
		return getToken(key)

access_token = getToken(key)

def resetToken():
	global access_token
	access_token = getToken(key)

def createParams(instruction, symbol, quantity): #update quantities
	params = {
		"orderType": "MARKET",
		"session": "NORMAL",
		"duration": "DAY",
		"orderStrategyType": "SINGLE",
		"orderLegCollection": [
			{
				"instruction": instruction,
				"quantity": quantity,
				"instrument": {
					"symbol": symbol,
					"assetType": "EQUITY"
				}
			}
		]
	}
	return params

def getReturn():
	url = r"https://api.tdameritrade.com/v1/accounts/{}".format(account_id)
	headers = {
		"Authorization":"Bearer {}".format(access_token)
	}
	obj = requests.get(url,headers=headers).json()['securitiesAccount']

	liquidation = obj['currentBalances']['liquidationValue']
	initial = obj['initialBalances']['accountValue']
	change = liquidation / initial * 100
	dollars = liquidation - initial

	return (dollars,change)

def textMessage():
	balance = getReturn()
	if balance[0]!=0:
		output = "Daily Change: $" + str(balance[0]) + " or " + str(balance[1]) + "%" + "."
	else:
		output = "NO CHANGE"

	message = client.messages \
                .create(
                     body=output,
                     from_='+15169167871',
                     to='+17322660834'
                 )

def getBalance():
	url = r"https://api.tdameritrade.com/v1/accounts/{}".format(account_id)
	headers = {
		"Authorization":"Bearer {}".format(access_token)
	}
	obj = requests.get(url,headers=headers).json()['securitiesAccount']['currentBalances']
	if 'cashAvailableForTrading' in obj.keys():
		return obj['cashAvailableForTrading']
	elif 'availableFunds' in obj.keys():
		return obj['availableFunds']
	else:
		return 0

def checkPosition(sym): 
	url = r"https://api.tdameritrade.com/v1/accounts/{}".format(account_id)
	params = {
		"fields":'positions'
	}
	headers = {
		"Authorization":"Bearer {}".format(access_token)
	}
	obj = requests.get(url,params=params, headers=headers).json()
	while 'securitiesAccount' not in obj.keys():
		time.sleep(5)
		datetime.datetime.now().time() <= datetime.time(16,00)
	obj = obj['securitiesAccount']
	if 'positions' in obj:
		obj = obj['positions']
		for i in range(len(obj)):
			if(obj[i]["instrument"]["symbol"]==sym):
				quantity = obj[i]["shortQuantity"] + obj[i]["longQuantity"]
				return(quantity,obj[i]["averagePrice"])
		return (0,0)
	else:
		return (0,0)

def execAPI(params):
	url = r"https://api.tdameritrade.com/v1/accounts/{}/orders".format(account_id) #orders / savedorders
	headers = {'Authorization':'Bearer {}'.format(access_token),
				'Content-Type':'application/json'
			}
	obj = requests.post(url,headers=headers,json=params)
	return obj

def sell(sym,val):
	return execAPI(createParams("Sell", sym,val))

def buy(sym,val):
	return execAPI(createParams("Buy", sym, val))

def get_quotes(**kwargs):
	# Define endpoint URL
	url = 'https://api.tdameritrade.com/v1/marketdata/quotes'

	# Create parameters, update api key.
	params = {}
	params.update({'apikey': key})
	# Create and fill the symbol_list list with symbols from argument
	params.update({'symbol': kwargs.get('symbol')})

	# Create request, with URL and parameters
	obj = requests.get(url, params=params).json()

	requested_stocks = kwargs.get('symbol').split(',')
	premarket = kwargs.get('premarket')
	quotes = []
	for i in range(len(requested_stocks)):
		if premarket:
			quotes.append((float(obj[requested_stocks[i]]['lastPrice']),float(obj[requested_stocks[i]]['lastPrice']),int(obj[requested_stocks[i]]['totalVolume']))) if requested_stocks[i] in obj else quotes.append(None)
		else:
			quotes.append((float(obj[requested_stocks[i]]['bidPrice']),float(obj[requested_stocks[i]]['askPrice']),int(obj[requested_stocks[i]]['totalVolume']))) if requested_stocks[i] in obj else quotes.append(None)
	return quotes

def get_price_history(**kwargs):

	url = 'https://api.tdameritrade.com/v1/marketdata/{}/pricehistory'.format(kwargs.get('symbol'))

	params = {}
	params.update({'apikey': key})

	for arg in kwargs:
		parameter = {arg: kwargs.get(arg)}
		params.update(parameter)

	obj = requests.get(url, params=params).json()
	if 'candles' in obj:
		return obj['candles']
	else:
		print("FAILED TO GET CANDLES, RETRYING...")
		time.sleep(3)
		resetToken()
		return get_price_history(**kwargs)
