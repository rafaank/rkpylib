import os
import sys
import json
import socket
from rkpylib.rkhttp import RKHTTP, RKHTTPGlobals
from rkpylib.rklogger import RKLogger

ok_response_text = 'HTTP/1.1 200 OK\n\n'


@RKHTTP.route('/hello')
def hello(globals, request, response):
    response.send_response(200)
    response.send_header('Content-Type', 'text/html')            
    response.end_headers()            
    response.wfile.write(ok_response_text.encode("utf-8"))
    
    
    
@RKHTTP.route('/sample')
def sample(globals, request, response):    
    '''
    globals.register(self, var_name, var_value): Registers a new variable in the global scope, this variable is accessible and shares the same value across all threads within the RKHttp instance scope.  
    globals.unregister(self, var_name): Unregisters a variable from the global scope
    globals.get(var_name): Returns the values for a global variable, example usage globals("var_name")
    globals.set(var_name, var_value): Updates value of a global variable.
    globals.inc(self, var_name, inc_val = 1): Updates the value of a global variable with inc_val.  You can use negative integers to decrement a value.

    request.parsed_path: Contains ParseResult object which is retrieved after processing the url through the parse.urlparse(path) function
    request.url_params: Url query params processed into a dictionary for ready to access
    request.headers: Extends access to the request headers dictionary
    request.command: Contains the command (request type). For example, 'GET' or 'POST'.  All other types are unsupported
    request.post_data: Request data received in POST method
    request.rfile: Reference to io.BufferedIOBase input stream of BaseHTTPHandler , ready to read from the start of the optional input data.  This should ideally be not required as all the data is already read and processed in easily readable variables 
    
    response.wfile: Reference to the io.BufferedIOBase output stream of BaseHTTPHandler for writing a response back to the client. Proper adherence to the HTTP protocol must be used when writing to this stream in order to achieve successful interoperation with HTTP clients
    response.send_response(code, message=None): Reference to the send_response function of BaseHTTPHandler. Adds a response header to the headers buffer and logs the accepted request. The HTTP response line is written to the internal buffer, followed by Server and Date headers. The values for these two headers are picked up from the version_string() and date_time_string() methods, respectively. If the server does not intend to send any other headers using the send_header() method, then send_response() should be followed by an end_headers() call.
    response.send_error(code, message=None): Reference to the send_error function of BaseHTTPHandler. Adds a response header to the headers buffer and logs the accepted request. The HTTP response line is written to the internal buffer, followed by Server and Date headers. The values for these two headers are picked up from the version_string() and date_time_string() methods, respectively. If the server does not intend to send any other headers using the send_header() method, then send_response() should be followed by an end_headers() call.
    response.send_header(keyword, value): Reference to the send_header function of BaseHTTPHandler. Adds the HTTP header to an internal buffer which will be written to the output stream when either end_headers() or flush_headers() is invoked. keyword should specify the header keyword, with value specifying its value. Note that, after the send_header calls are done, end_headers() MUST BE called in order to complete the operation
    response.end_headers(): Reference to the end_headers function of BaseHTTPHandler. Adds a blank line (indicating the end of the HTTP headers in the response) to the headers buffer and calls flush_headers().
    '''

    globals.inc("counter")
    response.send_response(200)
    response.send_header('Content-Type', 'application/json')            
    response.end_headers()            


    if request.command == "POST":
        try: 
            # post_params = parse.parse_qs(post_data)  //Can be used to parse other formats like form-data
            post_params = json.loads(request.post_data)
        except json.decoder.JSONDecodeError as je:
            response.send_error(500, str(je))
            return
        except Exception as e:
            response.send_error(500, 'Internal Server Error - ' + str(e))
            return

    resp_json = dict()
    resp_json['code'] = 200
    resp_json['data'] = dict()
    resp_json['data']['process_id'] = os.getpid()
    resp_json['data']['path'] = request.parsed_path.path
    resp_json['data']['query'] = request.parsed_path.query
    resp_json['data']['urlparams'] = request.url_params
    resp_json['data']['x-nof-request'] = globals._nof_requests
    resp_json['data']['x-counter'] = globals.get("counter")
    
    response_text = json.dumps(resp_json) 
    # print(response_text)
    response.wfile.write(response_text.encode("utf-8"))


if __name__ == '__main__':    

    ipaddr = socket.gethostname()
    port = 8282
    
    RKLogger.initialize('rkhttp', 'rkhttp.log', RKLogger.DEBUG)
    
    g = RKHTTPGlobals(debug_mode=True)
    g.register('counter', 0)
    
    server = RKHTTP.server((ipaddr, port), g)
    print (f'listening on address {ipaddr} and port {port}')
    server.serve_forever()
    
