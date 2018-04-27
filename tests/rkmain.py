from rkpylib.rkhttp import RKHTTPGlobals, RKHTTP
from rkpylib.rkdatasource import RKDataSource
from rkpylib.rkutils import trace_memory_leaks
from rktest import *
from test import *

import gc
import tracemalloc
import pprint


if __name__ == '__main__':    

    ''' Function to get a free datasource object from pool ''' 
    def dspool_func(pool):
        for idx, ds in enumerate(pool):
            if ds.lock.acquire(False):
                return ds
            else:
                continue
        return None


    tracemalloc.start()
    try:
        #gc.set_debug(gc.DEBUG_LEAK)
        ipaddr = socket.gethostname()
        port = 8282

        RKLogger.initialize('rkhttp', 'rkhttp.log', RKLogger.DEBUG)

        g = RKHTTPGlobals(debug_mode=True)
        g.register('counter', 0)
    
        ''' Creating pool of Datasource and locks to enable thread-safe processing '''
        dspool = list()
        for i in range(5):
            ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
            dspool.append(ds)
            
        ''' Adding datasource and lock to globally accessing variables list '''
        g.register('dspool', dspool)
        g.register('dspool_func', dspool_func)    
        g.register('total_requests', 0)

        server = RKHTTP.server((ipaddr, port), g)
        print (f'listening on address {ipaddr} and port {port}')
        server.serve_forever()
    finally:
        print ("Closing Down")
        
        for i in range(2):
            print('Collecting %d ...' % i)
            n = gc.collect()
            print('Unreachable objects:', n)
            print('Remaining Garbage:', pprint.pprint(gc.garbage))
            print

        trace_memory_leaks()
        #traceback_memory_leaks()

                

                
'''
list = [1, 2, 3]
dictionary = {1: 'one', 2: 'two', 3: 'three'}
tuple = (1, 2, 3)
set = {1, 2, 3}
'''