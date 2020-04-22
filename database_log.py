import pymongo
from pymongo import MongoClient
import collections

#accessing database
cluster = MongoClient("mongodb+srv://savanpatel1232:Winter35@cluster0-tprlj.mongodb.net/test?retryWrites=true&w=majority")
db = cluster["test"]
collection = db["test"]

with open('DATABASE_LOG_END_OF_DAY.txt','w') as f:
	items = collection.find({})
	for element in items:
		f.write(str(element))