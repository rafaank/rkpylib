from rkpylib.rkhttp import *
from rktest import *

import traceback
import gc
import tracemalloc
import pprint


if __name__ == '__main__':    

    def dspool_func(pool, pool_lock):
        for idx, ds in enumerate(pool):
            if pool_lock[idx].acquire(False):
                ds_obj = dict()
                ds_obj['lock'] = pool_lock[idx]
                ds_obj['ds'] = ds
                return ds_obj
            else:
                continue
        return None

    tracemalloc.start()
    try:
        #gc.set_debug(gc.DEBUG_LEAK)
        ipaddr = socket.gethostname()
        port = 8282
        RKLogger.initialize('rkhttp', 'rkhttp.log', RKLogger.DEBUG)
        g = RKHttpGlobals(debug_mode=False)

        g.register('counter', 0)
    
        dspool = list()
        dspool_lock = list()
        
        for i in range(5):
            ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
            lck = Lock()
            dspool.append(ds)
            dspool_lock.append(lck)
            
        g.register('dspool', dspool)
        g.register('dspool_lock', dspool_lock)
        g.register('dspool_func', dspool_func)    
        g.register('total_requests', 0)        


        server = RKHTTPServer((ipaddr, port), RKHandlerClassFactory(g))
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