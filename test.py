import requests
import matplotlib.pyplot as plt

def get_price_history(**kwargs):

	url = 'https://api.tdameritrade.com/v1/marketdata/{}/pricehistory'.format(kwargs.get('symbol'))

	params = {}
	params.update({'apikey': key})

	for arg in kwargs:
		parameter = {arg: kwargs.get(arg)}
		params.update(parameter)

	obj = requests.get(url, params=params).json()['candles']
	return obj

obj = get_price_history("WTI")

time = []
volumes = []
closes = []

for item in obj:
	volumes.append(int(item["volume"]))
	closes.append(float(item["close"]))
	time.append(int(item["datetime"]))

plt.plot(time,volumes)
plt.plot(time,closes)
plt.show()