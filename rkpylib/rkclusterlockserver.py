import ssl

from socketserver import ThreadingMixIn, TCPServer, BaseRequestHandler
from threading import Lock
import socket

import platform, os, sys, getopt

from rkclusterlock import RKClusterLock
import rkutils
import logging


help_str = '''
helo :
    Welcome message from server

reg <app_name> :
    Register a new APP:                                                     

acq <app_name> <acquire_wait_time> <max_release_time> :
    Client request to acquire lock for APP <app_name>.
    Server will wait for <acquire_wait_time> to acquire the lock
    and wait for <max_release_time> for the lock to be release
    otherwise releases the lock forcefully.

lck <data> :
    Servers response to acq, mentioning the lock is acquired 
    followed by the current data stored for the APP 
    
rel <data> :
    Release lock for the acquired APP and set the new data.

fail :
    Servers response to acq, mentioning the server failed to
    acquire lock for this client during the <acquire_wait_time>
    
help :
    Help using RKClusterLock

err :
    Error occured at server side, which could be due invalid
    commands or wrong sequence

quit :
    End connection with the server\n
'''


class RKClusterNode():
    def __init__(self):
        self.lock  = Lock()
        self.data = ""


class RKClusterLockServer():
    def __init__(self):

        self.logger = logging.getLogger('rkclusterlock')
        self.logger.setLevel(logging.DEBUG) # logging.ERROR
        
        log_file = '/var/log/rkclusterlock.log'
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)        
        log_format = '%(asctime)s - %(name)s - %(ip)s:%(port)d - %(levelname)s - %(message)s'
        formatter = logging.Formatter(log_format)
        fh.setFormatter(formatter)        
        self.logger.addHandler(fh)
        
    
    def start(self, host, port, data_path):
    
        def load_app_data(nodes):
            for filename in os.listdir(data_path):
                
                if os.path.isfile(data_path + "/" + filename) and filename[0:1] != ".": 
                    f=open(data_path + "/" + filename, 'r')
                    data = ""
                    for line in f:                    
                        data = data + line

                    node = RKClusterNode()
                    node.lock = Lock()
                    node.data = data 
                    nodes[filename] = node
                    f.close()
                
            
        
        @rkutils.setInterval(60)
        def save_app_data(nodes):
            for app_name,node in nodes.items():
                if node.lock.acquire(True, 1):
                    try:
                        data = node.data
                    finally:
                        node.lock.release()
                    
                    with open(data_path + "/" + app_name, 'w+') as f:
                        f.write(data)
                        
                    
            
        nodes = dict()
        load_app_data(nodes)
        save_app_data(nodes)
        
        self.server = RKTCPServer((host, port), RKTCPHandlerClassFactory(nodes, self.logger))
        
        ip, port = self.server.server_address
        
        extra = {'ip':ip, 'port':port}
        self.logger.info('RKClusterLock server started...', extra=extra)


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
    
    

def RKTCPHandlerClassFactory(nodes, logger):    
    class RKTCPRequestHandler(BaseRequestHandler):
        def __init__(self, *args, **kwargs):
            self.nodes = nodes
            self.logger = logger
            super(RKTCPRequestHandler, self).__init__(*args, **kwargs)            
    
    
        def handle(self):
            clientip, port = self.request.getpeername()
            self.logger_extra = {'ip':clientip, 'port':port}

            self.logger.info("New client connection",extra=self.logger_extra)
            response = RKClusterLock.WELCOME + f": Lock Server waiting for request \n"
            self.request.sendall(bytes(response, 'ascii'))

            while 1:
                data = ""
                try:
                    #self.request.setdefaulttimeout(5.0)
                    self.request.settimeout(None)
                    try:
                        data = str(self.request.recv(RKClusterLock.BUF_SIZE), 'ascii').strip()
                    except socket.timeout as to:
                        self.logger.error("Timeout reading from client", extra=self.logger_extra)
                        continue
                        
                    self.logger.debug(f"Got data-{data}", extra=self.logger_extra)
                    if not data:
                        self.logger.debug("Client disconnected", extra=self.logger_extra)
                        break
                    
                    data_arr = data.split(RKClusterLock.SEPARATOR)
 
                    if data_arr[0] == RKClusterLock.ACQUIRE:
                        try:
                            app_name = data_arr[1].strip()
                        except IndexError as ie:
                            self.logger.error("Missing app_name",extra=self.logger_extra)
                            response = RKClusterLock.FAILED + "\n"
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
                            node = self.nodes[app_name]
                        except KeyError as ke:
                            self.logger.error("APP {app_name} not registered",extra=self.logger_extra)
                            response = RKClusterLock.ERROR + f": APP {app_name} not registered\n"
                            self.request.sendall(bytes(response, 'ascii'))
                            continue
                        
                        if node.lock.acquire(True, acquire_wait_time):
                            try:
                                self.logger.info("Lock Acquired",extra=self.logger_extra)
                                self.request.settimeout(max_release_time)
                                
                                response = RKClusterLock.LOCKED + RKClusterLock.SEPARATOR + node.data + "\n"
                                self.request.sendall(bytes(response, 'ascii'))                            
                                
                                data = str(self.request.recv(RKClusterLock.BUF_SIZE), 'ascii').strip()                                
                                data_arr = data.split(RKClusterLock.SEPARATOR, 1)
        
                                if data_arr[0] == RKClusterLock.RELEASE:
                                    try:
                                        node.data = data_arr[1].strip()                                       
                                    except:
                                        pass
                                    self.logger.info(f"RELEASE request received, setting new data = {node.data}", extra=self.logger_extra)
                                    response = RKClusterLock.RELEASE + RKClusterLock.SEPARATOR + ": success\n"
                                    self.request.sendall(bytes(response, 'ascii'))
                                    self.logger.info(f"Response sent to client", extra=self.logger_extra)

                                else:
                                    self.logger.error(f"Expected {RKClusterLock.RELEASE} got {data_arr[0]}, lock released forcefully",extra=self.logger_extra)
                                    response = RKClusterLock.ERROR + RKClusterLock.SEPARATOR + f": Expected {RKClusterLock.RELEASE}, lock released forcefully\n"
                                    self.request.sendall(bytes(response, 'ascii'))
                                                                                                    
                            except socket.timeout as to:
                                self.logger.error("<max_release_time> timeout, lock released forcefully",extra=self.logger_extra)
                                response = RKClusterLock.ERROR + RKClusterLock.SEPARATOR + ":<max_release_time> timeout, lock released forcefully\n"
                                self.request.sendall(bytes(response, 'ascii'))                                
                                continue

                            except Exception as e: 
                                self.logger.error("Some Error" + str(e), extra=self.logger_extra)

                            finally:
                                node.lock.release()
                                self.logger.info("Lock Released",extra=self.logger_extra)

                        else:
                            response = RKClusterLock.FAILED + "\n"
                            self.request.sendall(bytes(response, 'ascii'))
                            
                    elif data_arr[0] == RKClusterLock.REGISTER:
                        try:
                            app_name = data_arr[1].strip()
                            node = RKClusterNode()
                            node.lock = Lock()
                            self.nodes[app_name] = node
                            response = RKClusterLock.REGISTER + RKClusterLock.SEPARATOR + ": success\n"
                            self.request.sendall(bytes(response, 'ascii'))
                        except:
                            self.logger.error("Missing app_name",extra=self.logger_extra)
                            response = RKClusterLock.ERROR + RKClusterLock.SEPARATOR + "app_name invalid or missing: \n"
                            self.request.sendall(bytes(response, 'ascii'))

                    elif data_arr[0] == RKClusterLock.HELP:
                        response = RKClusterLock.HELP + RKClusterLock.SEPARATOR + help_str
                        self.request.sendall(bytes(response, 'ascii'))

                    elif data_arr[0] == RKClusterLock.RELEASE:
                        self.logger.error("No active lock to be released",extra=self.logger_extra)
                        response = RKClusterLock.ERROR + ": No active lock to be released\n"
                        self.request.sendall(bytes(response, 'ascii'))

                    elif data_arr[0] == RKClusterLock.QUIT:
                        self.request.close()
                        break

                    else:
                        self.logger.error("Unexpected message",extra=self.logger_extra)
                        response = RKClusterLock.ERROR + ": Unexpected message\n"
                        self.request.sendall(bytes(response, 'ascii'))
                        
                            
                except ConnectionError as ce:                
                    self.logger.error("Connection error", extra=self.logger_extra)
                    break
                
                except Exception as e:
                    #An Unknown exception has occured, lets not do anything just log the error and close the socket
                    self.logger.exception(str(e), extra=self.logger_extra)
                    try:
                        self.request.close()
                    except:
                        pass
                    break
                
            
    return RKTCPRequestHandler



if __name__ == "__main__":

    ahost = "0.0.0.0"
    aport = "0"
    adata_path = ""
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv,"h:p:d:",["host=","port=","data-path="])
    except getopt.GetoptError:
        print('Invalid parameters, use the below syntax')
        print('glhttp.py -h <host> -p <port> -d <data-path>')
        print()
        print('\t-h <host>\t IP address on which to start the RKCLusterLockServer, defaults to 0.0.0.0')
        print('\t-p <port>\t Port on which RKClusterLockServer will listen, defaults to 9191')
        print('\t-d <data-path>\t  Path where the application data will be stored')
        sys.exit(2)
        
    for opt, arg in opts:
        if opt == '--help':
            print('glhttp.py -h <host> -p <port> -d <data-path>')
            sys.exit()
        elif opt in ("-h", "--host"):
            ahost = arg
        elif opt in ("-p", "--port"):
            aport = arg
        elif opt in ("-d", "--data-path"):
            adata_path = arg

    port = int(aport)
    host = ahost
    data_path = adata_path
    if not os.path.isdir(data_path):
        print("error: data-path does not exist")
        sys.exit(2)
    
    if not port in range(1,65525):
        port = 9191 
    
    lock_server = RKClusterLockServer()
    lock_server.start(host, port, data_path)
