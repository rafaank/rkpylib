import errno
import importlib
import socket
import sys
import time
import traceback

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
from socketserver import ThreadingMixIn
from threading import Thread, Lock


from .rkutils import *
from .rklogger import RKLogger

import json
from bson import json_util

# import importlib
# import importlib.util


global server


class RKHTTPGlobals():
        
    def __init__(self):        
        "Create a new instance of RKHTTPGlobals object that will be used to bind with RKHTTPServer instance"

        self._nof_requests = 0
        self._variables = dict()
        self._lock = Lock()
        self._error = None

    
    def __del__(self):
        "Destructor to destroy the RKHTTPGlobals object instance and all child objects"
 
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
    
    
    def register(self, var_name, var_value):
        "Register a new global variable"

        RKLogger.debug(f'Registered new variable {var_name}')
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    # Variable already exists
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
    
    
    def unregister(self, var_name):
        "Unregister a global variable"

        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    del self._variables[var_name]
                    return True
                else:
                    RKLogger.debug(f"Variable {var_name} not found in globals")
                    return False
            except Exception as e:
                RKLogger.exception(str(e))
                return False
            finally:
                self._lock.release()    
         


    def get(self, var_name):
        "Get value of a registered global variable, returns variable value if the variable exists and value is successfully fetched else returns None"
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    return self._variables[var_name]
                else:
                    RKLogger.debug(f"Variable {var_name} not found in globals")
                    return None
            except Exception as e:
                RKLogger.exception(str(e))
                return None
            finally:
                self._lock.release()
        else:
            RKLogger.debug("Failed to get lock in globals.get")
            return None

    
    def set(self, var_name, var_value):
        "Set value of a registered global variable, return True if variable value is set else returns False if the variable does not exists or if failed to set the value"
        if self._lock.acquire(True, 1):
            try:
                if not var_name in self._variables:
                    RKLogger.debug(f"Variable {var_name} not found in globals")
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
            RKLogger.debug("Failed to get lock in globals.set")
            return False
        


    def inc(self, var_name, inc_val = 1):
        "Increments a registered variables value by <inc_val>, returns True if value is incremented sucessfully else returns False if failed to set the value"
        
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
  

def RKHTTPHandlerClassFactory(globals):
    "Class factory to customize the initialization of RKHTTPRequestHandler object with additional global parameter"
    class RKHTTPRequestHandler(BaseHTTPRequestHandler):
        "Class RKHTTPRequestHandler derived from BaseHTTPRequestHandler, a subclass to handle all HTTP requests"
        
        def __init__(self, *args, **kwargs):
            "Constructor of RKHTTPRequestHandler, initializes the handler and binds the HTTPGlobals object to the handler"
            self.globals = globals
            self.globals._nof_requests += 1
            super(RKHTTPRequestHandler, self).__init__(*args, **kwargs)
      
      
        def __del__(self):
            "Destructor for the RKHTTPRequestHandler object"
            #super(RKHTTPRequestHandler, self).__del__()
            pass
                                                      
        def do_preprocess(self):
            "Preprocess a request by initializing all request and response parameters that can be used to do the processing of a GET or POST request"
            err = self.globals._error
            if isinstance(err, Exception) :
                #self.send_error(200, str(err), traceback.print_tb(err.__traceback__))
                self.send_exception(500, str(err), err)
                return False
            
            try:
                self.request = RKDict()
                self.request.client_address = self.client_address
                self.request.server = self.server
                self.request.close_connection = self.close_connection
                self.request.requestline = self.requestline
                self.request.command = self.command
                self.request.path = self.path
                self.request.request_version = self.request_version

                self.request.parsed_path = parse.urlparse(self.path)
                self.request.url_paramsl = parse.parse_qsl(self.request.parsed_path.query)
                self.request.url_paramsd = parse.parse_qs(self.request.parsed_path.query)
                self.request.url_params = dict(parse.parse_qsl(self.request.parsed_path.query))
    
                self.request.headers = self.headers
                self.request.rfile = self.rfile
                self.request.post_data = ""
        
                self.response = RKDict()
                self.response.wfile = self.wfile
                self.response.send_response = self.send_response
                self.response.send_error = self.send_error
                self.response.send_header = self.send_header
                self.response.end_headers = self.end_headers
                self.response.send_exception = self.send_exception
                
                
                self.function = RKHTTP._route_function(self.request.parsed_path.path)
                if not self.function:
                    self.send_error(404, 'Not Found - ' + self.request.parsed_path.path )
                    return False
                    
                return True
            except Exception as e:
                #self.send_error(500, str(e), traceback.format_exc())
                self.send_exception(500, str(e), e)
                return False
            
    
        def send_exception(self, code, message=None, exception=None):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')            
            self.end_headers()            
            resp_json = dict()
            resp_json['code'] = code
            resp_json['message'] = message
            if isinstance(exception, Exception):
                #exc_type, exc_value, exc_traceback = sys.exc_info()
                #trace_list = traceback.extract_tb(exc_traceback)
                trace_list = traceback.extract_tb(exception.__traceback__)
                new_trace_list = list()
                for idx, val in enumerate(trace_list):
                    new_trace_list.append(repr(val).replace('<FrameSummary ', '', 1)[:-1])    
                
                resp_json['exception'] = new_trace_list
            else:
                resp_json['exception'] = exception
            
            response_text = json.dumps(resp_json, default=json_util.default)
            self.wfile.write(response_text.encode("utf-8"))
            
            
            
            
        def do_GET(self):
            "GET request handler, calls the route_path attached function"
            
            if self.do_preprocess():
                try:
                    RKLogger.debug(f'Executing function {self.request.parsed_path.path}')
                    self.function(self.globals, self.request, self.response)
                    RKLogger.debug(f'Completed function {self.request.parsed_path.path}')                
                except BrokenPipeError as bpe:
                    RKLogger.exception(str(bpe))
                except Exception as e:
                    try:
                        #self.send_error(500, str(e), traceback.format_exc())
                        self.send_exception(500, str(e), e)
                    except Exception as e:                        
                        RKLogger.exception(str(e))

    
        def do_POST(self):
            "GET request handler, initalizes the post data and makes it available as a request variable. Later calls the route_path attached function"
            
            if self.do_preprocess(): 
                
                '''
                try:
                    content_length = int(self.headers['Content-Length'])
                    self.request.post_data = self.rfile.read(content_length)            
                except Exception as e:
                    self.send_error(500, str(e), traceback.format_exc())
                    return
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
   
    
        def log_message(self, format, *args):
            "Override to the default log_message to write all logs to RKLogger"
            RKLogger.debug(format, *args)
    
        
        def log_error(self, format, *args):
            "Override to the default log_message to write all logs to RKLogger"
            RKLogger.exception(format, *args)
    
    
        def log_response_text(self, format, *args):
            "Override to the default log_message to write all logs to RKLogger"
            RKLogger.debug(format, *args)
    
    
        def handle_default(self, request, response):
            "Function to handle all default treated requests, will be deprecated in future"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')            
            self.end_headers()
            self.wfile.write('RKHTTP is active...'.encode('utf-8'))                        
                               
    return RKHTTPRequestHandler

   
class RKHTTPServer(ThreadingMixIn, HTTPServer):
    pass
    


class RKHTTP():
    "Wrapper class to initialize a RKHTTPServer instance.  Also manages all route_paths and route_functions"
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
        s = RKHTTPServer(ip_port, RKHTTPHandlerClassFactory(globals))
        return s

