"""RKHTTPServer
A single-core multi-threaded HTTPServer that enables sharing of data
and information amongst http requests using a global instance of type RKHTTPGlobals.

RKHTTPGlobals
A thread-safe storage class, that makes it easy to store and retrieve variables
that can be shared amongst requests within a process

Global Functions
    globals.register(self, var_name, var_value):
            Registers a new variable in the global scope, this variable is accessible
            and shares the same value across all threads within the RKHttp instance scope.  
    
    globals.unregister(self, var_name):
            Unregisters a variable from the global scope
    
    globals.get(var_name):
            Returns the values for a global variable
    
    globals.set(var_name, var_value):
            Updates value of a global variable.
    
    globals.inc(self, var_name, inc_val = 1):
            Increments the value of a global variable with inc_val.  You can use negative integers to decrement a value.


Request Variables    
    request.client_address:
            Contains a tuple of the form (host, port) referring to the client’s address.
    
    request.server:
            Contains the server instance
    
    request.close_connection:
            Boolean that should be set before handle_one_request() returns,
            indicating if another request may be expected, or if the connection should be shut down.
    
    request.requestline:
            Contains the string representation of the HTTP request line. The terminating CRLF is stripped.
            This attribute should be set by handle_one_request(). If no valid request line was processed,
            it should be set to the empty string
    
    request.command:
            Contains the command (request type). For example, 'GET'
    
    request.path:
            Contains the request path
    
    request.request_version:
            Contains the version string from the request. For example, 'HTTP/1.0'.    
    
    request.parsed_path:
            Contains ParseResult object which is retrieved after processing the url through the parse.urlparse(path) function
    
    request.url_params:
            Url query params processed into a dictionary for ready to access
    
    request.url_paramsl:
            Url query params parsed as a list, Data are returned as a list of name, value pairs
    
    request.url_paramsd:
            Url query params processed into a dictionary, The dictionary keys are the unique
            query variable names and the values are lists of values for each name.    
    
    request.post_data:
            Post request data,
    
    
    request.headers:
            Extends access to the request headers dictionary. 
    
    request.command:
            Contains the command (request type). For example, 'GET' or 'POST'.  All other types are unsupported
    
    request.rfile:
            Reference to io.BufferedIOBase input stream of BaseHTTPHandler, ready to read from
            the start of the optional input data.  This should ideally be not required as all
            the data is already read and processed in easily readable variables
            
    response.wfile:
            Reference to the io.BufferedIOBase output stream of BaseHTTPHandler for writing a
            response back to the client. Proper adherence to the HTTP protocol must be used
            when writing to this stream in order to achieve successful interoperation with HTTP clients


Response Functions
    response.send_response(code, message=None):
            Reference to the send_response function of BaseHTTPHandler. Adds a response header
            to the headers buffer and logs the accepted request. The HTTP response line is
            written to the internal buffer, followed by Server and Date headers. The values for
            these two headers are picked up from the version_string() and date_time_string() methods,
            respectively. If the server does not intend to send any other headers using the
            send_header() method, then send_response() should be followed by an end_headers() call.
            
    response.send_error(code, message=None):
            Reference to the send_error function of BaseHTTPHandler. Adds a response header
            to the headers buffer and logs the accepted request. The HTTP response line is written
            to the internal buffer, followed by Server and Date headers. The values for these
            two headers are picked up from the version_string() and date_time_string() methods,
            respectively. If the server does not intend to send any other headers using the send_header()
            method, then send_response() should be followed by an end_headers() call.
            
    response.send_header(keyword, value):
            Reference to the send_header function of BaseHTTPHandler. Adds the HTTP header to an internal
            buffer which will be written to the output stream when either end_headers() or flush_headers()
            is invoked. keyword should specify the header keyword, with value specifying its value. Note that,
            after the send_header calls are done, end_headers() MUST BE called in order to complete the operation
    
    response.end_headers():
            Reference to the end_headers function of BaseHTTPHandler. Adds a blank line (indicating the end
            of the HTTP headers in the response) to the headers buffer and calls flush_headers().

    response.send_exception(code, message=None, exception=None):
            Function to send exception information back to the client as a formatted JSON 


    response.send_json_response(self, code, resp_json):
            Function to send JSON response back to the client, this is a wrapper function which wraps the below commonly used code
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response_text = json.dumps(resp_json, default=json_util.default) 
                self.wfile.write(response_text.encode("utf-8"))

"""


import errno
import importlib
import socket
import sys
import time
import traceback
import cgi

from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie as cookie 
from urllib import parse
from socketserver import ThreadingMixIn
from threading import Thread, Lock
from .rkutils import RKDict

import logging 
import json
import jwt

from bson import json_util
from uuid import uuid1
from time import time

# import importlib
# import importlib.util


global server


class RKHTTPGlobals():
    def __init__(self):        
        """Creates a new instance of RKHTTPGlobals object that will be used to bind with RKHTTPServer instance."""

        self._nof_requests = 0
        self._variables = dict()
        self._lock = Lock()
        self._error = None
        self._config = dict()
        self._config['parse_post_data'] = False
        self._logger = None

    
    def __del__(self):
        """Destructor to destroy the RKHTTPGlobals object instance and all child objects."""
 
        if self._lock.acquire(True, 10):
            try:
                for key in self._variables:
                    del self._variables[key]
            except:
                return False                
            finally:
                self._lock.release()

        del self._variables
        del self._lock
    
        
    def register(self, var_name, var_value):
        """Registers a new global variable."""
            
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    # Variable already exists
                    return False
                else:
                    self._variables[var_name] = var_value
                    self._logger.debug(f'Registered new variable {var_name}')
                    return True
            except Exception as e:
                self._logger.exception(str(e))
                return False            
            finally:
                self._lock.release()
        else:
            # failed to get lock
            return False
    
    
    def unregister(self, var_name):
        """Unregisters a global variable."""

        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    del self._variables[var_name]
                    return True
                else:
                    self._logger.debug(f"Variable {var_name} not found in globals")
                    return False
            except Exception as e:
                self._logger.exception(str(e))
                return False
            finally:
                self._lock.release()    
         
    #def __getattr__(self, attr):
    #    return self.get(var_name)
    

    def get(self, var_name):
        """Gets value of a registered global variable, returns variable value if the variable exists and value is successfully fetched else returns None."""
        if self._lock.acquire(True, 1):
            try:
                if var_name in self._variables:
                    return self._variables[var_name]
                else:
                    self._logger.debug(f"Variable {var_name} not found in globals")
                    return None
            except Exception as e:
                self._logger.exception(str(e))
                return None
            finally:
                self._lock.release()
        else:
            self._logger.debug("Failed to get lock in globals.get")
            return None

    
    def set(self, var_name, var_value):
        """Sets value of a registered global variable, returns True if variable value is set else returns False if the variable does not exists or if failed to set the value."""
        if self._lock.acquire(True, 1):
            try:
                if not var_name in self._variables:
                    self._logger.debug(f"Variable {var_name} not found in globals")
                    return False
                else:
                    self._variables[var_name] = var_value
                    return True
            except Exception as e:
                self._logger.exception(str(e))
                return False                
            finally:
                self._lock.release()
        else:
            # failed to get lock
            self._logger.debug("Failed to get lock in globals.set")
            return False
        


    def inc(self, var_name, inc_val = 1):
        """Increments a registered variables value by <inc_val>, returns True if value is incremented sucessfully else returns False if failed to set the value."""
        
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
                self._logger.exception(str(e))
                return False
            finally:
                self._lock.release()
        else:
            return False
  

def RKHTTPHandlerClassFactory(globals):
    """Class factory to customize the initialization of RKHTTPRequestHandler object with additional global parameter."""

    class RKHTTPRequestHandler(BaseHTTPRequestHandler):
        """Class RKHTTPRequestHandler derived from BaseHTTPRequestHandler, a subclass to handle all HTTP requests."""
        
        sessioncookies = dict()


        def __init__(self, *args, **kwargs):
            """Constructor of RKHTTPRequestHandler, initializes the handler and binds the HTTPGlobals object to the handler."""
            self.globals = globals
            self.globals._nof_requests += 1
            self.sessionidmorsel = None
            super(RKHTTPRequestHandler, self).__init__(*args, **kwargs)
      
      
        def __del__(self):
            """Destructor for the RKHTTPRequestHandler object."""
            #super(RKHTTPRequestHandler, self).__del__()
            pass

        def _session_cookie(self, forcenew=False):
            cookiestring = "\n".join(self.headers.get_all('Cookie',failobj=[]))
            c = cookie()
            c.load(cookiestring)

            try:  
                if forcenew or self.sessioncookies[c['session_id'].value]-time() > 3600:  
                    raise ValueError('new cookie needed')  
            except:  
                c['session_id']=uuid1().hex  

            for m in c:  
                if m=='session_id':  
                    self.sessioncookies[c[m].value] = time()  
                    c[m]["httponly"] = True  
                    c[m]["max-age"] = 3600  
                    c[m]["expires"] = self.date_time_string(time()+3600)  
                    self.sessionidmorsel = c[m]  
                    break
    

        def do_preprocess(self):
            """Preprocess a request by initializing all request and response parameters that can be used to do the processing of a GET or POST request."""
            err = self.globals._error
            if isinstance(err, Exception) :
                #self.send_error(200, str(err), traceback.print_tb(err.__traceback__))
                self.send_exception(500, str(err), err)
                return False
          
            self._session_cookie()

            if not (self.sessionidmorsel is None):  
                self.send_header('Set-Cookie',self.sessionidmorsel.OutputString())

            try:
                
                self.request = RKDict()
                self.request.client_address = self.client_address
                self.request.server = self.server
                self.request.close_connection = self.close_connection
                self.request.requestline = self.requestline
                self.request.command = self.command
                self.request.path = self.path
                self.request.content_type = None
                self.request.request_version = self.request_version
    
                self.request.parsed_path = parse.urlparse(self.path)
                self.request.url_paramsl = parse.parse_qsl(self.request.parsed_path.query)
                self.request.url_paramsd = parse.parse_qs(self.request.parsed_path.query)
                self.request.url_params = dict(parse.parse_qsl(self.request.parsed_path.query))
    
                self.request.headers = self.headers
                self.request.rfile = self.rfile
                self.request.post_data = None
        
                self.response = RKDict()
                self.response.wfile = self.wfile
                self.response.send_response = self.send_response
                self.response.send_error = self.send_error
                self.response.send_header = self.send_header
                self.response.end_headers = self.end_headers
                self.response.send_exception = self.send_exception
                self.response.send_json_response = self.send_json_response
    
                self.function = RKHTTP._route_function(self.request.parsed_path.path)
                if not self.function:
                    self.send_error(404, 'Not Found - ' + self.request.parsed_path.path )
                    return False
                    
                return True
            except Exception as e:
                #self.send_error(500, str(e), traceback.format_exc())
                self.send_exception(500, str(e), e)
                return False
                        
            
        def do_GET(self):
            """GET request handler, calls the route function attached to the url_path."""
            if self.do_preprocess():
                try:
                    self.globals._logger.debug(f'Executing function {self.request.parsed_path.path}')
                    self.function(self.globals, self.request, self.response)
                    self.globals._logger.debug(f'Completed function {self.request.parsed_path.path}')                
                except BrokenPipeError as bpe:
                    self.globals._logger.exception(str(bpe))
                except Exception as e:
                    try:
                        #self.send_error(500, str(e), traceback.format_exc())
                        self.send_exception(500, str(e), e)
                    except Exception as e:                        
                        self.globals._logger.exception(str(e))

    
        def do_POST(self):
            """GET request handler, initalizes the post data and makes it available as a request variable. Later calls the route function attached to the url_path."""
            if self.do_preprocess(): 
                try:   
                    if (self.globals._config['parse_post_data']):                        
                        post_data = None
                        ctype = self.headers['content-type']
                        if ctype: 
                            if ctype == 'application/json':
                                content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
                                post_data = self.rfile.read(content_length) # <--- Gets the data itself
                                if post_data:
                                    post_data = json.loads(post_data.decode('utf-8'))
                            elif ctype.startswith('multipart/form-data'):
                                 # boundary data needs to be encoded in a binary format
                                ctype, pdict = cgi.parse_header(self.headers['content-type'])
                                pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                                post_data = cgi.parse_multipart(self.rfile, pdict)            
                            elif ctype == 'application/x-www-form-urlencoded':
                                content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
                                post_data = self.rfile.read(content_length) # <--- Gets the data itself
                                post_data = parse.parse_qs(post_data.decode('utf-8'))
                    
                        self.request.post_data = post_data
                        self.request.content_type = ctype
                except Exception as e:
                    self.send_exception(500, f"{str(e)} - An Exception occured trying to read post_data, if you think your post data is correct, then try reading it directly from rfile by setting the global._config['parse_post_data']=False", e)
                
                try:
                    self.globals._logger.debug(f'Executing function {self.request.parsed_path.path}')
                    self.function(self.globals, self.request, self.response)
                    self.globals._logger.debug(f'Completed function {self.request.parsed_path.path}')                
                except BrokenPipeError as bpe:
                    self.globals._logger.exception(str(bpe))
                except Exception as e:
                    #self.send_error(500, str(e), traceback.format_exc())
                    self.send_exception(500, str(e), e)
   
    
        def log_message(self, format, *args):
            """Override to the default log_message to write all logs to our logger"""
            self.globals._logger.debug(format, *args)
    
        
        def log_error(self, format, *args):
            """Override to the default log_message to write all logs to our logger"""
            self.globals._logger.exception(format, *args)
    
    
        def log_response_text(self, format, *args):
            """Override to the default log_message to write all logs to our logger"""
            self.globals._logger.debug(format, *args)
    
    
        def handle_default(self, request, response):
            """Function to handle all default treated requests, will be deprecated in future"""
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')            
            self.end_headers()
            self.wfile.write('RKHTTP is active...'.encode('utf-8'))                        
                               
    
        def send_exception(self, code, message=None, exception=None):
            """ Returns a json formatted and easy readable exception information with traceback information."""
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
            try:
                self.wfile.write(response_text.encode("utf-8"))
            except Exception as e:
                self.globals._logger.exception(str(e))


        def send_json_response(self, code, resp_json):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response_text = json.dumps(resp_json, default=json_util.default) 
            self.wfile.write(response_text.encode("utf-8"))

            

    return RKHTTPRequestHandler

   
class RKHTTPServer(ThreadingMixIn, HTTPServer):
    globals = None
    


class RKHTTP():
    """Wrapper class to initialize a RKHTTPServer instance.  Also manages all route_paths and route_functions"""
    _routes = dict()
    
    @classmethod    
    def route(cls, route_str):
        """ Decorator to bind url path to a function """
        def decorator(f):
            cls._routes[route_str] = f
            return f
        
        return decorator
    
    
    @classmethod
    def _route_function(cls, url_path):
        """ Returns the function associated with the given url_path  """
        rfunc = cls._routes.get(url_path)
        return rfunc

    
    @classmethod
    def server(cls, ip_port, app_name, log_file):
        """ Returns a new instance of a single core multi-threaded HTTP Server. """        
        logger = logging.getLogger(app_name)
        logger.setLevel(logging.DEBUG) # logging.ERROR
        
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)        
        log_format = '%(asctime)-15s - %(name)s - %(levelname)-8s - %(message)s'
        formatter = logging.Formatter(log_format)
        fh.setFormatter(formatter)        
        logger.addHandler(fh)

        globals = RKHTTPGlobals()
        globals._logger = logger

        s = RKHTTPServer(ip_port, RKHTTPHandlerClassFactory(globals))
        s.globals = globals
        return s

if __name__ == "__main__":
    @RKHTTP.route('/rkhttp.test')
    def rkhttp_test_function(globals, request, response):
        resp_json = dict()
        resp_json['code'] = 200
        resp_json['total_requests'] = globals._nof_requests
        resp_json['data'] = dict()
        resp_json['data']['value'] = 'RKHTTP is running'

        response.send_json_response(200, resp_json)

    port = 9786
    ipaddr = '0.0.0.0'
    server = RKHTTP.server((ipaddr, port), "rkhttp", "/var/log/rkhttp.log")
    server.globals._config['parse_post_data'] = True

    server.serve_forever()


