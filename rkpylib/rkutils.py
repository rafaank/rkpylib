import threading
import linecache
import os
import tracemalloc

class RKDict(dict):
    """Simple dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class Map(dict):
    """
    Advanced dot.notation access to dictionary attributes
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    """
    def __init__(self, *args, **kwargs):
        # super(Map, self).__init__(*args, **kwargs)
        '''
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.iteritems():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.iteritems():
                self[k] = v
        '''
        self.update(*args, **kwargs)


    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]
        
        
    def __missing__(self, key):
        value = self[key]= type(self)();
        return value
    
    def __getstate__(self, key):
        pass

    def __setstate__(self, key):
        pass
    
    
def setInterval(interval):
    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()

            def loop(): # executed in another thread
                while not stopped.wait(interval): # until stopped
                    function(*args, **kwargs)

            t = threading.Thread(target=loop)
            t.daemon = True # stop if the program exits
            t.start()
            return stopped
        return wrapper
    return decorator

def traceback_memory_leaks(limit=50):
    snapshot = tracemalloc.take_snapshot()
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(True, "fkhttp.py"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
        tracemalloc.Filter(False, threading.__file__),
        tracemalloc.Filter(False, "<unknown>"),
    ))

    top_stats = snapshot.statistics('traceback')
    for index, stat in enumerate(top_stats[:limit], 1):
        print("#%s: %s memory blocks: %.1f KiB" % (index, stat.count, stat.size / 1024))

        for line in stat.traceback.format():
            print(line)   



def trace_memory_leaks(key_type='lineno', limit=50):
    snapshot = tracemalloc.take_snapshot()
    snapshot = snapshot.filter_traces((
        # tracemalloc.Filter(True, "fkhttp.py"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
        tracemalloc.Filter(False, threading.__file__),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    total_leak_size = sum(stat.size for stat in top_stats)
    
    print("Total Leak size: %.1f KiB" % ( total_leak_size / 1024))

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print(frame.filename)
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))

        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))

    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))




