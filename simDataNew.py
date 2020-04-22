from api import get_price_history

def newSIMData(symb,starter,endofweek):
	for i in range(len(symb)):
		filename = './sim/'+symb[i]+'.txt'
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,startDate=starter)
		with open(filename,'w') as f:
			for i in range(len(obj)):
				if(starter<=obj[i]['datetime']):
					f.write(str(obj[i]['close']))
					f.write('\n')