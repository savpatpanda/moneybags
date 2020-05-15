import collections
import os
from datetime import datetime
from api import get_price_history

ed = collections.defaultdict(list)

# Gets equity by filename in /sim, returns a loaded object with prices in reverse chronological order
def loadFile(directory):
	if not os.path.isdir(directory):
		print("not a valid directory. recheck sim files.")
		exit(1)
	maxTimeStep = 0
	for (root, dirs, files) in os.walk(directory):
		#print("Found %d files.\n" % len(files))
		for file in files:
			equity = file.split('.')[0]
			with open(directory + file) as f:
				ed[equity] = [x for x in reversed(f.read().split())]
				maxTimeStep = max(len(ed[equity]), maxTimeStep)
	return maxTimeStep

# Returns and shortens the list corresponding to equity
def get_quotes(equity):
	if equity in ed and len(ed[equity]) > 1:
		new = ed[equity].pop()
		if new in ['OPEN','Null','CLOSE']:
			output = (new,new,new)
		else:
			separate = new.split(',')
			output = (float(separate[0]),float(separate[0]),int(separate[1]))
		return output
	else:
		return None

# Generate SIM Data
def generateSim(symb,starter,endofweek):
	for i in range(len(symb)):
		filename = './sim/'+symb[i]+'.txt'
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,startDate=starter,endDate=endofweek)
		initial = int(starter / 60000)
		final = int(endofweek / 60000)
		print(symb[i], end = " ", flush = True)
		with open(filename,'w') as f:
			current_index = 0
			for j in range(initial,final+1,1):
				current = datetime.fromtimestamp(j*60) 
				if current.weekday() <=4:
					if current.hour==9 and current.minute == 30:
						f.write("OPEN\n")
					elif current.hour==4 and current.minute == 0:
						f.write("CLOSE\n")
				if(current_index >= len(obj)):
					break
				if(current.hour < 7 or current.hour > 20 or current.weekday() > 4):
					continue
				elif(int(obj[current_index]['datetime']/60000)>j):
					f.write("Null\n")
					continue
				else:
					output = str(obj[current_index]['close']) + ','+str(obj[current_index]['volume']) + '\n'
					f.write(output)
					current_index = current_index + 1
	print('\n')

# Initializes global ed object, returns maximum time steps needed.
def initializeSim(directory = "./sim/"):
	#print("Loading sim...")
	return loadFile(directory)
