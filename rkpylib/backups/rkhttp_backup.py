import time
import os
import sys
import errno
from multiprocessing import Process
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
from socketserver import ForkingMixIn, ThreadingMixIn

ok_message = 'HTTP/1.0 200 OK\n\n'
nok_message = 'HTTP/1.0 404 NotFound\n\n'

class MyClass():
    def __init__(self, args):
        self.ctr = 0
        self.name = args

def RKHandlerClassFactory(myargs):
    class RKHTTPRequestHandler(BaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            self.variable = myargs
            self.variable.ctr += 1
            super(RKHTTPRequestHandler, self).__init__(*args, **kwargs)

        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            message = f'process_id={os.getpid()} and Variable = {self.variable.name} and Counter = {self.variable.ctr}\r\n'
            self.wfile.write(message.encode('utf-8'))            

    return RKHTTPRequestHandler


class RKHTTPRequestHandler1(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        request = [
            f'client_address={self.client_address} ({self.address_string()})',
            f'command={self.command}',
            f'path={self.path}',
            f'real_path={parsed_path.path}',
            f'query_params={parsed_path.query}',
            f'request_version={self.request_version}'            
        ]

        server = [
            f'server_version={self.server_version}',
            f'sys_version={self.sys_version}',
            f'protocol_version={self.protocol_version}',
            f'process_id={os.getpid()}'
        ]
        headers = []

        for name, value in sorted(self.headers.items()):
            headers.append(f'{name}={value.rstrip}')

        self.send_response(200)
        self.send_header('Content-Type', 'text/plain; charset=utf-8')
        self.end_headers()
        message = '\r\n'.join(request) + '\r\n' + '\r\n'.join(server)
        self.wfile.write(message.encode('utf-8'))

   
class RKHTTPServer(ForkingMixIn, HTTPServer):
    pass
    
if __name__ == '__main__':
    ipaddr = socket.gethostname()
    port = 8282
    cls = MyClass("Fazal Khan")
    server = RKHTTPServer((ipaddr, port), RKHandlerClassFactory(cls))
    print (f'listening on address {ipaddr} and port {port}')
    server.serve_forever()



                
                
'''
list = [1, 2, 3]
dictionary = {1: "one", 2: "two", 3: "three"}
tuple = (1, 2, 3)
set = {1, 2, 3}
'''