import errno
import socket
import time
from rkutils import RKDict, setInterval, trace_memory_leaks
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
from socketserver import ThreadingMixIn
from threading import Thread, Lock
from rklogger import RKLogger

import json
import traceback
import importlib
import importlib.util
import rkhttp_globals
import gc
import tracemalloc


ok_response_text = 'HTTP/1.0 200 OK\n\n'
nok_response_text = 'HTTP/1.0 404 NotFound\n\n'


class RKHttpGlobals():
        
    def __init__(self, debug_mode = True):
        self._nof_requests = 0
        self._variables = dict()
        self._debug_mode = debug_mode
        self._lock = Lock()
        rkhttp_globals.__init_globals__(self)
        # self._refresh_stop = self.__refresh_globals__()         
    
    
    def __del__(self):
        if self._lock.acquire(True, 10):
            try:
                for i, var in self._variables.items():
                    return False
                elif var_name in self._variables and var_value is None:
                    del self._variables[var_name]
                else:
                    self._variables[var_name]['value'] = var_value
                    self._variables[var_name]['last_reload'] = time.time()
                    return True
            except:
                return False                
            finally:
                self._lock.release()

        self._variables = None
    
    def register(self, var_name, var_value) : #, reload_interval = None, reload_func = None):
        RKLogger.debug(f'Register requested for {var_name}')
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    # Variable already exists
                    return False
                elif var_value is None:
                    # Variable value cannot be None
                    return False
                else:
                    self._variables[var_name] = dict()
                    self._variables[var_name]['name'] = var_name
                    self._variables[var_name]['value'] = var_value
                    # self._variables[var_name]['reload_interval'] = reload_interval
                    # self._variables[var_name]['reload_func'] = reload_func
                    # self._variables[var_name]['last_reload'] = time.time()
                    return True
            except:
                return False            
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False
    
    
    def update(self, var_name, var_value):
        RKLogger.debug(f'Update requested for {var_name}')
        if self._lock.acquire(True, 1):
            try:
                if not var_name in self._variables:
                    return False
                elif var_name in self._variables and var_value is None:
                    del self._variables[var_name]
                else:
                    self._variables[var_name]['value'] = var_value
                    self._variables[var_name]['last_reload'] = time.time()
                    return True
            except:
                return False                
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False


    def get(self, var_name):
        RKLogger.debug(f'Get requested for {var_name}')        
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    return self._variables[var_name]['value']
                else:
                   return None                
            finally:
                self._lock.release()
        else:
            return None


    '''
    def stop_reload(self, var_name):
        RKLogger.debug(f'Stop reload requested for {var_name}')
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    self._variables[var_name]['reload_interval'] = None
                    self._variables[var_name]['reload_func'] = None
                else:
                    return False
            except:
                return False                
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False

         
    def stop_all_reload(self):
        RKLogger.debug('Stopping all reload globals')
        self._refresh_stop.set()

    def __async__(self, function, *args, **kwargs):
        def thread_run(globals): # executed in another thread
            try:
                RKLogger.debug(f'Executing variable reload function for {args[0]}')
                new_value = function(*args, **kwargs)
            except Exception as e:
                RKLogger.exception('Variable deleted due to exception: {str(e)}')                        
                globals.update(args[0], None)
            else:
                globals.update(args[0], new_value)

        t = Thread(target=thread_run, args=(self,))
        t.daemon = True # stop if the program exits
        t.start()

    @setInterval(300)
    def __refresh_globals__(self):
        RKLogger.debug('Refreshing globals')
        # gc.collect()
        for i, var in self._variables.items():
            if var['reload_interval'] and var['reload_func']:
                RKLogger.debug(f' variable {var["name"]}, reload_interval {var["reload_interval"]}, last_reload {var["last_reload"]}, time {time.time()} ')
                if time.time() - var['last_reload'] > var['reload_interval']:
                    reload_func = var['reload_func']
                    self.__async__(reload_func, var['name'], var['value'])

    '''        

def RKHandlerClassFactory(myargs):
    class RKHTTPRequestHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.globals = myargs
            self.globals._nof_requests += 1
            super(RKHTTPRequestHandler, self).__init__(*args, **kwargs)
      
      
        def __del__(self):
            self.request.path = None
            self.request.parsed_path = None
            self.request.url_params = None
            self.request.command = None
            self.request.headers = None
            self.request.rfile = None
            self.request = None

            self.response.wfile = None
            self.response.send_response = None
            self.response.send_header = None
            self.response.end_headers = None
            self.response = None
            
            self.globals = None
            print("Destroying RKRequestHandler")
            # super(RKHTTPRequestHandler, self).__del__()
                                                      
        def do_preprocess(self):
            
            self.request = RKDict()
            self.request.path = self.path
            self.request.parsed_path = parse.urlparse(self.path)
            self.request.url_params = parse.parse_qsl(self.request.parsed_path.query)
            self.request.command = self.command
            self.request.headers = self.headers
            self.request.rfile = self.rfile            
    
            self.response = RKDict()
            self.response.wfile = self.wfile
            self.response.send_response = self.send_response
            self.response.send_header = self.send_header
            self.response.end_headers = self.end_headers
            
            paths = self.request.parsed_path.path.split('/')
            
            if len(paths) >= 3:
                self.module_name = paths[1]
                self.function_name = paths[2]
                try:
                    #importlib.invalidate_caches()
                    # module = importlib.util.find_spec(self.module_name)
                    module = __import__(self.module_name)
                    if self.globals._debug_mode:
                        importlib.reload(module)
                        
                    self.log_message(f'Successfully Loaded module {self.module_name}')
                    self.function = getattr(module, self.function_name)
                    self.log_message(f'Successfully Loaded function {self.function_name}')
                except ModuleNotFoundError as mnfe:
                    self.send_error(400, str(mnfe))
                    return False
                except AttributeError as ae:
                    self.send_error(400, str(ae))
                except Exception as e:
                    self.send_error(500, str(e), traceback.format_exc())
                    return False
    
            else:
                self.function = self.handle_default
                self.function_name = 'Default'
            
            return True
    
            
        def do_GET(self):
            
            if self.do_preprocess():
                try:
                    RKLogger.debug(f'Executing function {self.function_name}')
                    self.function(self.globals, self.request, self.response)
                    RKLogger.debug(f'Completed function {self.function_name}')
                
                except BrokenPipeError as bpe:
                    RKLogger.exception(str(bpe))
                except Exception as e:
                    try:
                        self.send_error(500, str(e), traceback.format_exc())
                    except:
                        pass
                finally:
                    pass
                    #trace_memory_leaks()    
    
    
        def do_POST(self):
            
            if self.do_preprocess(): 
                try:
                    content_length = int(self.headers['Content-Length'])             
                    self.request.post_data = self.rfile.read(content_length)            
                except Exception as e:
                    self.send_error(500, str(e), traceback.format_exc())
                    return
                
                try:
                    RKLogger.debug(f'Executing function {self.function_name}')
                    self.function(self.request, self.response)
                    RKLogger.debug(f'Completed function {self.function_name}')
                except Exception as e:
                    self.send_error(500, str(e), traceback.format_exc())
    
    
        def log_message(self, format, *args):
            RKLogger.debug(format, *args)
    
        
        def log_error(self, format, *args):
            RKLogger.exception(format, *args)
    
    
        def log_response_text(self, format, *args):
            RKLogger.debug(format, *args)
    
    
        def handle_default(self, request, response):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')            
            self.end_headers()
            self.wfile.write('RKHttp is active...'.encode('utf-8'))                        
                           
    
    return RKHTTPRequestHandler

   
class RKHTTPServer(ThreadingMixIn, HTTPServer):
    pass
    

if __name__ == '__main__':
    tracemalloc.start()
    try:
        #gc.set_debug(gc.DEBUG_LEAK)
        ipaddr = socket.gethostname()
        port = 8282
        RKLogger.initialize('rkhttp', 'rkhttp.log', RKLogger.DEBUG)
        gl = RKHttpGlobals()
        server = RKHTTPServer((ipaddr, port), RKHandlerClassFactory(gl))
        print (f'listening on address {ipaddr} and port {port}')
        server.serve_forever()
    except Exception as e:
        print(e)
    finally:
        del(gl)
        del(server)
        gc.collect()
        trace_memory_leaks()        

            
                

                
'''
list = [1, 2, 3]
dictionary = {1: 'one', 2: 'two', 3: 'three'}
tuple = (1, 2, 3)
set = {1, 2, 3}
'''