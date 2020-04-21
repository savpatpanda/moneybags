import collections
import os

ed = collections.defaultdict(list)

# Gets equity by filename in /sim, returns a loaded object with prices in reverse chronological order
def loadFile(directory):
	if not os.path.isdir(directory):
		print("not a valid directory. recheck sim files.")
		exit(1)
	for (root, dirs, files) in os.walk(directory):
		print("Found %d files.\n" % len(files))
		for file in files:
			equity = file.split('.')[0]
			with open(directory + file) as f:
				ed[equity] = [float(x) for x in reversed(f.read().split())]

# Returns and shortens the list corresponding to equity
def get_quotes(equity):
	if equity in ed and len(ed[equity]) > 1:
		return ed[equity].pop()
	else:
		return None

# Initializes global ed object
def initializeSim(directory = "./sim/"):
	print("Loading sim...")
	loadFile(directory)
