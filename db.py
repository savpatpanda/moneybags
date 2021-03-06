import os
import pymongo
import collections
import numpy as np
from pymongo import MongoClient
from api import checkPosition, get_price_history
import time

cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
print("DATABASE: %s" % os.getenv("DB_NAME"))
collection = db[os.getenv("DB_NAME")]
track = 300 #minutes tracking
frequency = 1
actionHold = 15

def getCollection():
	return collection

def dbPut(db):
	for key, value in db.items():
		collection.update_one({"_id": key}, {"$set": value})

def initializeDB(symb, start=0, end=0, SIM=False):
	#initializing values in database
	for i in range(len(symb)):
		print(symb[i],end=" ", flush=True)
		obj = None
		obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=frequency,endDate=end,startDate=start)
		max_length = len(obj)
		v = []
		vol = []

		if track>max_length:
			track_sub = max_length
			for j in range(track_sub):
				v.append(float(obj[max_length-track_sub+j]['close']))
				vol.append(int(obj[max_length-track_sub+j]['volume']))
		else:
			for j in range(track):
				v.append(float(obj[max_length-track+j]['close']))
				vol.append(int(obj[max_length-track+j]['volume']))

		moving = []
		for j in range(len(vol)-actionHold):
			moving.append(np.mean(vol[j:j+actionHold]))

		s = []
		for j in range(len(v)-1):
			slope = (v[j+1]-v[j])/v[j]*100
			s.append(slope)

		volS = []
		for j in range(len(moving)-1):
			slope = (moving[j+1]-moving[j])/moving[j]*100
			volS.append(slope)

		if SIM:
			pos = (0,0)
		else:
			pos = checkPosition(symb[i])

		if collection.find({"_id":symb[i]}).count() ==0:
			post = {"_id":symb[i],"bidPrice":v, "askPrice":v, "bidSlope":s, "askSlope":s, "volume": vol, "moving":moving, "volumeSlope": volS, "wait_buy":0,"wait_sell":0,"pos":pos,"readySell":False,
				"policy":None}
			collection.insert_one(post)
		else:
			post = {symb[i]:{"bidPrice":v, "askPrice":v, "bidSlope":s, "askSlope":s, "volume": vol, "moving":moving, "volumeSlope": volS, "wait_buy":0,"wait_sell":0,"pos":pos,"readySell":False}}
			dbPut(post)
	print("\n")

def dbLoad() -> collections.defaultdict:
	m = collections.defaultdict(lambda: {})
	cursor = collection.find({})
	for doc in cursor:
		equity = doc['_id']
		for key, value in doc.items():
			if key != '_id':
				m[equity][key] = value
	return m

def cleanup():
	cluster.close()

def logEOD(): 
	cluster.close()
	with open('DATABASE_LOG_END_OF_DAY.log','w') as f:
		items = collection.find({})
		for element in items:
			f.write(str(element))
