import collections
import os
from api import get_price_history

ed = collections.defaultdict(list)

# Gets equity by filename in /sim, returns a loaded object with prices in reverse chronological order
def loadFile(directory):
	if not os.path.isdir(directory):
		print("not a valid directory. recheck sim files.")
		exit(1)
	maxTimeStep = 0
	for (root, dirs, files) in os.walk(directory):
		print("Found %d files.\n" % len(files))
		for file in files:
			equity = file.split('.')[0]
			with open(directory + file) as f:
				ed[equity] = [float(x) for x in reversed(f.read().split())]
				maxTimeStep = max(len(ed[equity]), maxTimeStep)
	return maxTimeStep

# Returns and shortens the list corresponding to equity
def get_quotes(equity):
	if equity in ed and len(ed[equity]) > 1:
		return ed[equity].pop()
	else:
		return None

# Generate SIM Data
def generateSim(symb,starter,endofweek):
	for i in range(len(symb)):
		filename = './sim/'+symb[i]+'.txt'
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=1,startDate=starter,endDate=endofweek)
		with open(filename,'w') as f:
			for i in range(len(obj)):
				if(starter<=obj[i]['datetime']<=endofweek):
					f.write(str(obj[i]['close']))
					f.write('\n')


# Initializes global ed object, returns maximum time steps needed.
def initializeSim(directory = "./sim/"):
	print("Loading sim...")
	return loadFile(directory)
