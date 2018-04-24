import errno
import socket
import time
import traceback

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
from socketserver import ThreadingMixIn
from threading import Thread, Lock

from .rkutils import *
from .rklogger import RKLogger

# import json
# import importlib
# import importlib.util


global server


class RKHttpGlobals():
        
    def __init__(self, debug_mode = True):
        self._nof_requests = 0
        self._variables = dict()
        self._debug_mode = debug_mode
        self._lock = Lock()

    
    def __del__(self):
        if self._lock.acquire(True, 10):
            try:
                for name, value in self._variables.items():
                    del self._variables[name]
            except:
                return False                
            finally:
                self._lock.release()

        del self._variables
        del self._lock
        print("Destroying Globals")
    
    
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
                    self._variables[var_name] = var_value
                    return True
            except Exception as e:
                RKLogger.exception(str(e))
                return False            
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False
    

    def get(self, var_name):
        RKLogger.debug(f'get requested for {var_name}')        
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    return self._variables[var_name]
                else:
                   return None
            except Exception as e:
                RKLogger.exception(str(e))
                return None
            finally:
                self._lock.release()
        else:
            return None

    
    def set(self, var_name, var_value):
        RKLogger.debug(f'set requested for {var_name}')
        if self._lock.acquire(True, 1):
            try:
                if not var_name in self._variables:
                    return False
                elif var_name in self._variables and var_value is None:
                    del self._variables[var_name]
                else:
                    self._variables[var_name] = var_value
                    return True
            except Exception as e:
                RKLogger.exception(str(e))
                return False                
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False


    def inc(self, var_name, inc_val = 1):
        RKLogger.debug(f'inc requested for {var_name}')        
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    if type(self._variables[var_name]) is int:
                        self._variables[var_name] += inc_val
                        return True
                    else:
                        return False
                else:
                   return False
            except Exception as e:
                RKLogger.exception(str(e))
                return False
            finally:
                self._lock.release()
        else:
            return False
  

def RKHttpHandlerClassFactory(globals):
    class RKHTTPRequestHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.globals = globals
            self.globals._nof_requests += 1
            super(RKHTTPRequestHandler, self).__init__(*args, **kwargs)
      
      
        def __del__(self):
            del self.request
            del self.response            
            del self.globals
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
            self.response.send_error = self.send_error
            self.response.send_header = self.send_header
            self.response.end_headers = self.end_headers
            
            self.function = RKHttp._route_function(self.request.parsed_path.path)
            if not self.function:
                self.send_error(404, 'Not Found - ' + self.request.parsed_path.path )
                return False
            
            return True
    
            
        def do_GET(self):
            
            if self.do_preprocess():
                '''
                RKLogger.debug(f'Executing function {self.request.parsed_path.path}')
                self.function(self.globals, self.request, self.response)
                RKLogger.debug(f'Completed function {self.request.parsed_path.path}')                
                '''                
                try:
                    RKLogger.debug(f'Executing function {self.request.parsed_path.path}')
                    self.function(self.globals, self.request, self.response)
                    RKLogger.debug(f'Completed function {self.request.parsed_path.path}')                
                except BrokenPipeError as bpe:
                    RKLogger.exception(str(bpe))
                except Exception as e:
                    try:
                        self.send_error(500, str(e), traceback.format_exc())
                    except Exception as e:
                        RKLogger.exception(str(e))

    
        def do_POST(self):
            
            if self.do_preprocess(): 
                try:
                    content_length = int(self.headers['Content-Length'])             
                    self.request.post_data = self.rfile.read(content_length)            
                except Exception as e:
                    self.send_error(500, str(e), traceback.format_exc())
                    return
                
                try:
                    RKLogger.debug(f'Executing function {self.request.parsed_path.path}')
                    self.function(self.globals, self.request, self.response)
                    RKLogger.debug(f'Completed function {self.request.parsed_path.path}')                
                except BrokenPipeError as bpe:
                    RKLogger.exception(str(bpe))
                except Exception as e:
                    try:
                        self.send_error(500, str(e), traceback.format_exc())
                    except Exception as e:
                        RKLogger.exception(str(e))
   
    
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
    


class RKHttp():
    _routes = dict()
    
    @classmethod    
    def route(cls, route_str):
        def decorator(f):
            cls._routes[route_str] = f
            return f
        
        return decorator
    
    
    @classmethod
    def _route_function(cls, path):
        rfunc = cls._routes.get(path)
        return rfunc

    
    @classmethod
    def server(cls, ip_port, globals):
        s = RKHTTPServer(ip_port, RKHttpHandlerClassFactory(globals))
        return s

