import sys
import json
import time
import datetime
import random

from bson import json_util

from rkpylib.rkdatasource import RKDataSource
from rkpylib.rkhttp import RKHttp

import pymongo    
    
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
    dspool_func = globals.get("dspool_func")

    ds = dspool_func(dspool) if dspool or dspool_func() else None

    if not ds:
        print("All DataSource inuse - Creating new DataSource")
        ds = RKDataSource(server='127.0.0.1', port=27017, database='test')
        data = ds.db['restaurants'].find({'cuisine': 'American'}).limit(1,5)
        ds.client.close()
    else:
        print("Data Source Found")
        data = ds.db.restaurants.find_one({'cuisine': 'American'})
        ds.lock.release()


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
    
    
