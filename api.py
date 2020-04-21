import requests
import matplotlib.pyplot as plt

def getToken(key):
	url = r"https://api.tdameritrade.com/v1/oauth2/token"
	headers = {
		'Content-Type': 'application/x-www-form-urlencoded',
		'cache-control': 'no-cache'
	}
	params = {
		"grant_type":'refresh_token',
		"refresh_token":'UNG9qUd148KVE+eUwqTUr221/BlFritvVlYKpuPhkuu0hYQ5YkdmKhsz+Znnx7ttvEBskgBVRrM7K8GXk+GOdGDQELfNPXcdW+ij1TZJXNuRLJhOted9qQY2qFpWQB8YV7V98rE/xb74bEv5xIOkQJKL6PzzKUVgnK8oolAD5ohnlArGRNz5Ubp3x9nPgWIJxio4biKDwoWvtWDClPQW4GA8YHmG92EpCWmT12WGxbt7jGkQeOp3nGVU+ZgsvXgoBMn/ZvWQ/kSA8lvZhxW4Qnymt8cnoRseA5315lF6We01kys/YN8DEPIAQRjRfYJjUv4arw3nQqQslIKhVg+g3aZzANDQx0xCpI/SEAbGtPquaJDX5wv6V8EMyZHYksg3obOjjYAcz9sLWq040wmmIknQRfVJDTgDxf7BY5ItJCC2YbHksPNgg/pwVSD100MQuG4LYrgoVi/JHHvl0W57fDOmbQYAuZAumAzaRQtA/9M2uaoi9hIxFUdoysP3yar3D4E+9UPRv5fNXRSULTLDv5nlCROeS6opfSCuADa71ziNsNCjDP7ZpRiKquSRuH+sD/jCystklI2PLc3auOZzCaTNapVwxhovbwOJxEgfGQJ9x7LVgzdZLAYz6mitGdpHc3HTLTTfJkA8h/Bi+Hk5n9Rbg5bLPH+5BFtozfDTXnAFclvz3DQiUia1WF19tEoMd9TZvtC9VMrT8Nb3F7SV3eQd/aF0FFjylhZqANb4IHa16d0/OYMIsPFJkcYnQpmxSya2vfAOKHGamor1YjG2HPp2yMSlTMl33Tc6xUUBsdxhRNtCH01u7vW9OoCfzJhsj8FNKdcy8qtDJ6qN47UkOmH/5XrHc5fToXeajCLwhKwuzCix8Q+/LwO9QzYCVRkmxPEwpLm2OcE=212FD3x19z9sWBHDJACbC00B75E',
		"client_id": 'QMXVMOERHQTU1ISEK7PY0S9JYCZNPLMJ'
	}
	return requests.post(url,data = params, headers=headers).json()['access_token']

account_id = "454685471" #your account number
key = 'QMXVMOERHQTU1ISEK7PY0S9JYCZNPLMJ'
access_token = getToken(key)

def createParams(instruction, symbol, quantity = 1): #update quantities
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

def getBalance():
	url = r"https://api.tdameritrade.com/v1/accounts/{}".format(account_id)
	headers = {
		"Authorization":"Bearer {}".format(access_token)
	}
	return requests.get(url,headers=headers).json()['securitiesAccount']['currentBalances']['availableFunds']

def checkPosition(sym): ### need to implement this method still
	url = r"https://api.tdameritrade.com/v1/accounts/{}".format(account_id)
	params = {
		"fields":'positions'
	}
	headers = {
		"Authorization":"Bearer {}".format(access_token)
	}
	return requests.get(url,data=params, headers=headers).json()

def execAPI(params):
	url = r"https://api.tdameritrade.com/v1/accounts/{}/savedorders".format(account_id)
	headers = {'Authorization':'Bearer {}'.format(access_token),
				'Content-Type':'application/json'
			}
	return requests.post(url,headers=headers,json=params)

def sell(sym):
	return execAPI(createParams("Sell", sym))

def buy(sym,val = 1):
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
	return obj[kwargs.get('symbol')]['lastPrice']

def get_price_history(**kwargs):

	url = 'https://api.tdameritrade.com/v1/marketdata/{}/pricehistory'.format(kwargs.get('symbol'))

	params = {}
	params.update({'apikey': key})

	for arg in kwargs:
		parameter = {arg: kwargs.get(arg)}
		params.update(parameter)

	obj = requests.get(url, params=params).json()['candles']
	return(obj)