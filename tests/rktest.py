import os
import sys
import json
import time
import datetime
import random

from bson import json_util
from rkpylib.rkdatasource import RKDataSource
from rkpylib.rkhttp import RKHttp

import pymongo

@RKHttp.route('/hello')
def hello(globals, request, response):

    response.send_response(200)
    response.send_header('Content-Type', 'application/json')            
    response.end_headers()            
    
    resp_json = dict()
    resp_json['code'] = 200
    resp_json['data'] = "Hi There!!!"
    response_text = json.dumps(resp_json) 
    response.wfile.write(response_text.encode("utf-8"))
    
    
@RKHttp.route('/sample')
def sample(globals, request, response):
    
    '''
    globals.register(self, var_name, var_value, reload_interval = None, reload_func = None): Registers a new variable in the global scope, this variable is accessible and shares the same value across all threads within the RKHttp scope.  reload_interval is the number of seconds after which a reload needs to be trigged and reload_func is the reload action that gets trigged.  reload_func is expected to return a value that is updated against the variable at every reload_interval.  This can majorly be used to synchronize the global variable data at certain time intervals.   If a variable does not need to be reloaded, its reload_interval must be passed as None (default).  If either reload_interval or reload_func is passed as None the variable is not reloaded.
    globals.get(var_name): Returns the values for a global variable, example usage globals("var_name")
    globals.set(var_name, var_value): Updates value of a global variabled.  To de-register a variable update its value with None.  

    request.parsed_path: Contains ParseResult object which is retrieved after processing the url through the parse.urlparse(path) function
    request.url_params: Url query params processed into a dictionary for ready to access
    request.headers: Extends access to the request headers dictionary
    request.command: Contains the command (request type). For example, 'GET' or 'POST'.  All other types are unsupported
    request.post_data: Request data received in POST method
    request.rfile: Reference to io.BufferedIOBase input stream of BaseHTTPHandler , ready to read from the start of the optional input data.  This should ideally be not required as all the data is already read and processed in easily readable variables 
    
    response.wfile: Reference to the io.BufferedIOBase output stream of BaseHTTPHandler for writing a response back to the client. Proper adherence to the HTTP protocol must be used when writing to this stream in order to achieve successful interoperation with HTTP clients
    response.send_response(code, message=None): Reference to the send_response function of BaseHTTPHandler. Adds a response header to the headers buffer and logs the accepted request. The HTTP response line is written to the internal buffer, followed by Server and Date headers. The values for these two headers are picked up from the version_string() and date_time_string() methods, respectively. If the server does not intend to send any other headers using the send_header() method, then send_response() should be followed by an end_headers() call.
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
            post_params = json.loads(self.request.post_data)
        except json.decoder.JSONDecodeError as je:
            self.send_error(500, str(je))
            return
        except Exception as e:
            self.send_error(500, 'Internal Server Error - ' + str(e))
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
    
    
@RKHttp.route('/pool')
def pool_example(globals, request, response):
    #ds = RKDataSource(server='13.251.32.176', port=27017, database='testgl')
    #ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
    resp_json = dict()
    response.send_response(200)
    response.send_header('Content-Type', 'application/json')            
    response.end_headers()            
    
    total_requests = globals.get('total_requests') + 1
    globals.set('total_requests',  total_requests)

    resp_json['total_requests'] = total_requests                            
    
    dspool = globals.get("dspool")
    dspool_lock = globals.get("dspool_lock")
    dspool_func = globals.get("dspool_func")

    if not dspool or not dspool_lock or not dspool_func:
        print("Creating new DataSource")
        ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
        data = ds.collection('restaurants').find({'cuisine': 'American'})            

    else:
        ds_obj = dspool_func(dspool, dspool_lock)

        if not ds_obj:
            print("All DataSource inuse - Creating new DataSource")
            ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
            data = ds.collection('restaurants').find({'cuisine': 'American'}).limit(1,5)            
        else:
            print("Data Source Found")
            data = ds_obj['ds'].db.restaurants.find_one({'cuisine': 'American'})
            #data = ds_obj['ds'].collection('restaurants').find({'cuisine': 'American'})            
            ds_obj['lock'].release()


    if data:
        resp_json['code'] = 'success'
        if isinstance(data, pymongo.cursor.Cursor):
            resp_json['data'] = [row for row in data]
        else:
            resp_json['data'] = data            
    else:
        resp_json['code'] = 'not_found'
        resp_json['data'] = "No records found"

    response_text = json.dumps(resp_json, default=json_util.default)
    response.wfile.write(response_text.encode("utf-8"))
    
@RKHttp.route('/table')
def table_example(globals, request, response):

    def date_range(start, end):
        for n in range(int((end-start).days)+1):
            yield start + datetime.timedelta(n)
            
            
    def fill_up_rest(start, end):
        print(f"fill_up_rest {start}, {end}")
        html = ""
        for dt in date_range(start, end):
            html += '<td style="width:100px;border-right:1px solid black">0</td>'
        return html
        
    def process_row(start, end):
        print(f"process_row {start}, {end}")
        html = ""
        for dt in date_range(start, end):
            if dt == end:
                html += '<td style="width:100px;border-right:1px solid black">1</td>'
            else:
                html += '<td style="width:100px;border-right:1px solid black">0</td>'
        
        return html
    
    start_date = datetime.date(2018, 4, 15)
    end_date = datetime.date(2018, 5, 1)

    arr = list()
    for i in range(1,100):
        rand = random.sample(list(date_range(start_date, end_date)), 10)
        rand.sort()
        for dt in rand:
            obj = dict()
            obj["usrid"] = i
            obj["date"] = dt.strftime('%Y-%m-%d')
            arr.append(obj)
    
    html = '<table><thead><td style="width:100px;border-right:1px solid black">UserID</td>'
    for dt in date_range(start_date, end_date):
        html += f'<td style="width:100px;border-right:1px solid black">{dt.strftime("%Y-%m-%d")}</td>'
    
    act_usrid = 0
    last_date = start_date
            
    for r in arr:
        if act_usrid == r["usrid"]:
            dt = datetime.datetime.strptime(r["date"], "%Y-%m-%d").date()
            html += process_row(last_date, dt)
            last_date = dt + datetime.timedelta(days = 1)
        else:
            if act_usrid > 0:
                # fill up all rest
                html += fill_up_rest(last_date, end_date)
                html += '</tr>'
                last_date = start_date
                
            act_usrid = r["usrid"]
            dt = datetime.datetime.strptime(r["date"], "%Y-%m-%d").date()
            html += f'<tr><td style="width:100px;border-right:1px solid black">{act_usrid}</td>'
            html += process_row(last_date, dt)
            last_date = dt + datetime.timedelta(days = 1)
                    
    if len(arr) > 0:
        html += fill_up_rest(last_date, end_date)
        html += '</tr>'
    
    html += '</thead></table>'

    response.send_response(200)
    response.send_header('Content-Type', 'text/html')            
    response.end_headers()            
    
    response_text = html
    response.wfile.write(response_text.encode("utf-8"))
    
    
