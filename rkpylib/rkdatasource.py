from pymongo import MongoClient
from threading import Lock 
from .rklogger import RKLogger


class RKDataSource:
    def __init__(self, **kwargs):
        self.database = kwargs['database']
        self.client = MongoClient(kwargs['server'], kwargs['port'])
        self.db = self.client[self.database]
        self.lock = Lock()


'''            
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
'''