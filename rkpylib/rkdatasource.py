from pymongo import MongoClient
from threading import Lock 
from .rklogger import RKLogger


class RKDataSource:
    "Wrapper class to connect to MongoDB, also implements a lock that can be used to thread-safe if the connection is used in a pool for reusability"
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