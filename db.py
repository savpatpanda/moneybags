import pymongo
import collections
import numpy as np
from pymongo import MongoClient
from api import checkPosition, get_price_history
import time

cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["Savan"]
track = 300 #minutes tracking
frequency = 1

def getCollection():
	return collection

def initializeDB(symb, startOfSIMInit=0, endOfSIMInit=0, SIM=False):
	#initializing values in database
	for i in range(len(symb)):
		if not SIM:
			obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=frequency,periodType='day',period=1)
		else:
			obj = get_price_history(symbol = symb[i],frequencyType='minute',frequency=frequency,endDate=endOfSIMInit,startDate=startOfSIMInit)
		time.sleep(1)
		max_length = len(obj)
		v = []
		for j in range(track):
			v.append(float(obj[max_length-track+j]['close']))

		s = []
		for j in range(len(v)-1):
			slope = (v[j+1]-v[j])/v[j]*100
			s.append(slope)

		pos = checkPosition(symb[i])

		post = {"_id":symb[i],"bidPrice":v, "askPrice":v, "bidSlope":s, "askSlope":s, "wait_buy":0,"wait_sell":0,"pos":pos,"readySell":False}
		collection.insert_one(post)

def dbLoad() -> collections.defaultdict:
	m = collections.defaultdict(lambda: {})
	cursor = collection.find({})
	for doc in cursor:
		equity = doc['_id']
		for key, value in doc.items():
			if key != '_id':
				m[equity][key] = value
	return m

def dbPut(db):
	for key, value in db.items():
		collection.update_one({"_id": key}, {"$set": value})

def logEOD(): 
	cluster.close()
	with open('DATABASE_LOG_END_OF_DAY.txt','w') as f:
		items = collection.find({})
		for element in items:
			f.write(str(element))