import ssl

from socketserver import ThreadingMixIn, TCPServer, BaseRequestHandler
from threading import Lock
import socket


from rklogger import RKLogger
from rkclusterlock import RKClusterLock
import rkutils


class RKClusterNode():
    def __init__(self):
        self.lock  = Lock()
        self.data = ""


class RKClusterLockServer():
    def __init__(self):
        pass
    
    def start(self, host = 'localhost', port = 9191):
    
        def load_app_data(nodes):
            pass
        
        @rkutils.setInterval(60)
        def save_app_data(nodes):
            for app_name,node in nodes.items():
                if node.lock.acquire(True, 1):
                    try:
                        data = node.data
                    finally:
                        node.lock.release()
                    
                    with open("/home/ec2-user/rk/rkpylib/rkpylib/data/" + app_name, 'w+') as f:
                        f.write(data)
                        
                    
            
        nodes = dict()
        save_app_data(nodes)
        
        self.server = RKTCPServer((host, port), RKTCPHandlerClassFactory(nodes))
        
        self.ip, self.port = self.server.server_address
        
        RKLogger.extra = {'ip':self.ip, 'port':self.port}
        RKLogger.info('RKClusterLock server started...')
        self.server.serve_forever()
        
        
    def stop(self):
        self.server.shutdown()
        self.server.server_close()



class RKTCPServer(ThreadingMixIn, TCPServer):  # Can be derived from RKSSLTCPServer instead of TCPServer for SSL Support 
    pass


class RKSSLTCPServer(TCPServer):
    def __init__(self, server_address, RequestHandlerClass, certfile, keyfile, ssl_version=ssl.PROTOCOL_TLSv1, bind_and_activate=True ):
        TCPServer.__init__(self, server_address, RequestHandlerClass, bind_and_activate)
        self.certfile = certfile
        self.keyfile = keyfile
        self.ssl_version = ssl_version

    def get_request(self):
        newsocket, fromaddr = self.socket.accept()
        connstream = ssl.wrap_socket(newsocket, server_side=True, certfile = self.certfile, keyfile = self.keyfile, ssl_version = self.ssl_version)
        return connstream, fromaddr
    
    

def RKTCPHandlerClassFactory(nodes):    
    class RKTCPRequestHandler(BaseRequestHandler):
        def __init__(self, *args, **kwargs):
            self.nodes = nodes
            self.node = None
            super(RKTCPRequestHandler, self).__init__(*args, **kwargs)            
    
    
        def handle(self):
            clientip, port = self.request.getpeername()
            self.logger_extra = {'ip':clientip, 'port':port}

            RKLogger.info("New client connection",extra=self.logger_extra)
            while 1:
                try:
                    #self.request.setdefaulttimeout(5.0)
                    self.request.settimeout(None)
                    try:
                        data = str(self.request.recv(RKClusterLock.BUF_SIZE), 'ascii').strip()
                    except socket.timeout as to:
                        RKLogger.error("Timeout reading from client", extra=self.logger_extra)
                        continue
                        
                    RKLogger.debug(f"Got data-{data}", extra=self.logger_extra)
                    #data = data.strip()
                    if not data:
                        RKLogger.debug("Client disconnected", extra=self.logger_extra)
                        break
                    
                    data_arr = data.split(RKClusterLock.SEPARATOR)
                    print(data_arr)
 
                    if data_arr[0] == RKClusterLock.ACQUIRE:
                        try:
                            app_name = data_arr[1].rstrip()
                        except IndexError as ie:
                            RKLogger.error("Missing app_name",extra=self.logger_extra)
                            response = RKClusterLock.FAILED
                            self.request.sendall(bytes(response, 'ascii'))
                            continue
    
                        try:
                            acquire_wait_time = float(data_arr[2])
                        except (IndexError, ValueError) as err:
                            acquire_wait_time = 5
                            
                        try:
                            max_release_time = float(data_arr[3])
                        except (IndexError, ValueError) as err:
                            max_release_time = 5.0
                        
                        try:
                            self.node = self.nodes[app_name]
                        except KeyError as ke:
                            self.node = RKClusterNode()
                            self.node.lock = Lock()
                            self.nodes[app_name] = self.node
                        
                        if self.node.lock.acquire(True, acquire_wait_time):
                            try:
                                RKLogger.info("Lock Acquired",extra=self.logger_extra)
                                self.request.settimeout(max_release_time)
                                
                                response = RKClusterLock.LOCKED + RKClusterLock.SEPARATOR + self.node.data 
                                self.request.sendall(bytes(response.strip(), 'ascii'))                            
                                
                                data = str(self.request.recv(RKClusterLock.BUF_SIZE), 'ascii')                        
                                data_arr = data.split(RKClusterLock.SEPARATOR, 1)
        
                                if data_arr[0] == RKClusterLock.RELEASE:
                                    RKLogger.info("Releasing lock",extra=self.logger_extra)
                                    try:
                                        self.node.data = data_arr[1]                                        
                                    except:
                                        pass
                                                                
                            except socket.timeout as to:
                                RKLogger.error("Request timeout",extra=self.logger_extra)
                                continue
                            finally:
                                self.node.lock.release()
                        else:
                            response = RKClusterLock.FAILED
                            self.request.sendall(bytes(response, 'ascii'))
                            
                    else:
                        response = RKClusterLock.ERROR
                        self.request.sendall(bytes(response, 'ascii'))
                        
                            
                except ConnectionError as ce:                
                    RKLogger.error("Connection error", extra=self.logger_extra)
                    break
                except Exception as e:
                    #An Unknown exception has occured, lets not do anything just log the error and close the socket
                    RKLogger.exception(str(e), extra=self.logger_extra)
                    try:
                        self.request.close()
                    except:
                        pass
                    break
                
            
    return RKTCPRequestHandler



if __name__ == "__main__":

    RKLogger.initialize('rkclusterlock', 'rkclusterlock.log', RKLogger.DEBUG, '%(asctime)s - %(name)s - %(ip)s:%(port)d - %(levelname)s - %(message)s')
    lock_server = RKClusterLockServer()
    lock_server.start('0.0.0.0', 9191)
    
