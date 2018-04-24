from .rkdatasource import RKDataSource
from .rkutils import RKDict

from threading import Lock


def __init_globals__(globals):
    globals.register('counter', 0)

    dspool = list()
    dspool_lock = list()
    
    for i in range(5):
        ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
        lck = Lock()
        dspool.append(ds)
        dspool_lock.append(lck)
        
    globals.register('dspool', dspool)
    globals.register('dspool_lock', dspool_lock)
    globals.register('dspool_func', dspool_func)    
    globals.register('total_requests', 0)


def dspool_func(pool, pool_lock):
    for idx, ds in enumerate(pool):
        if pool_lock[idx].acquire(False):
            print(f"Found dspool_item at index {idx}")
            ds_obj = dict()
            ds_obj['lock'] = pool_lock[idx]
            ds_obj['ds'] = ds
            return ds_obj
        else:
            continue
    return None
