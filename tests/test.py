from rkpylib.rkhttp import RKHttp

@RKHttp.route('/hello')
def hello(globals, request, response):

    response.send_response(200)
    response.send_header('Content-Type', 'application/json')            
    response.end_headers()            
    
    resp_json = dict()
    resp_json['code'] = 200
    resp_json['data'] = "Hi There!!!  RKHttp is running..."
    response_text = json.dumps(resp_json) 
    response.wfile.write(response_text.encode("utf-8"))
    