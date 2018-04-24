from pymongo import MongoClient
from .rklogger import RKLogger

class RKDataSource:
    global logger
    def __init__(self, **kwargs):
        self._database = kwargs['database']
        self._client = MongoClient(kwargs['server'], kwargs['port'])
        self.db = self._client[self._database]
        #self.db = self._client.test
        #self._collection = self._db.users
            
    def client(self):
        return self._client
    
    def collection(self, col=None):
        if col:
            self._collection = self.db[col]
        return self._collection

    def find(self, json):
        return self._collection.find(json)        

    def find_one(self, json):
        return self._collection.find_one(json)        
