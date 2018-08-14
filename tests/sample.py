import os
import sys
import json
import socket
import traceback


from rkpylib.rkhttp import RKHTTP

from urllib import parse

ok_response_text = 'HTTP/1.1 200 OK\n\n'


@RKHTTP.route('/hello')
def hello(globals, request, response):
    response.send_response(200)
    response.send_header('Content-Type', 'text/html')            
    response.end_headers()            
    response.wfile.write(ok_response_text.encode("utf-8"))
    
    
    
@RKHTTP.route('/sample')
def sample(globals, request, response):    
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
    """


    globals.inc("counter")
    response.send_response(200)
    response.send_header('Content-Type', 'application/json')            
    response.end_headers()            

    post_data = None
    if request.command == "POST":
        try: 
            # post_data = parse.parse_qs(post_data)  //Can be used to parse other formats like form-data
            
            #print(f'Content Length = {int(request.headers["Content-Length"])}')
            post_data = request.post_data
            if not globals._config['parse_post_data']:
                ctype = request.headers['content-type']
                if ctype:
                    if ctype == 'application/json':
                        content_length = int(request.headers['Content-Length']) # <--- Gets the size of data
                        post_data = request.rfile.read(content_length) # <--- Gets the data itself
                        post_data = json.loads(post_data.decode('utf-8'))
                    elif ctype.startswith('multipart/form-data'):
                         # boundary data needs to be encoded in a binary format
                        ctype, pdict = cgi.parse_header(request.headers['content-type'])
                        pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
                        post_data = cgi.parse_multipart(request.rfile, pdict)            
                    elif ctype == 'application/x-www-form-urlencoded':
                        content_length = int(request.headers['Content-Length']) # <--- Gets the size of data
                        post_data = request.rfile.read(content_length) # <--- Gets the data itself
                        post_data = parse.parse_qs(post_data.decode('utf-8'))
                        

                   
        except json.decoder.JSONDecodeError as je:
            response.send_error(500, str(je), traceback.format_exc())
            return
        except Exception as e:
            response.send_error(500, 'Internal Server Error - ' + str(e))
            return


    
    resp_json = dict()
    resp_json['code'] = 200
    resp_json['data'] = dict()
    resp_json['data']['os.getpid()'] = os.getpid()
    resp_json['data']['request.parsed_path.path'] = request.parsed_path.path
    resp_json['data']['request.parsed_path.query'] = request.parsed_path.query
    resp_json['data']['request.url_params'] = request.url_params
    resp_json['data']['request.url_paramsd'] = request.url_paramsd
    resp_json['data']['request.url_paramsl'] = request.url_paramsl
    resp_json['data']['request.headers'] = str(request.headers)
    resp_json['data']['command'] = request.command
    resp_json['data']['request.post_data'] = post_data
    resp_json['data']['globals._nof-request'] = globals._nof_requests
    resp_json['data']['globals.get("counter")'] = globals.get("counter")
    
    response_text = json.dumps(resp_json) 
    response.wfile.write(response_text.encode("utf-8"))


if __name__ == '__main__':    

    ipaddr = socket.gethostname()
    port = 8282
        
    server = RKHTTP.server((ipaddr, port), "sample_app", "/var/log/rkhttp.log")
    server.globals.register('counter', 0)
    print (f'listening on address {ipaddr} and port {port}')
    server.serve_forever()
    
