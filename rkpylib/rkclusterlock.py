# import ssl
import socket


class RKClusterLock():
    
    WELCOME     = 'helo'
    REGISTER    = 'reg'
    ACQUIRE     = 'acq'
    LOCKED      = 'lck'
    RELEASE     = 'rel'
    FAILED      = 'fail'
    HELP        = 'help'
    ERROR       = 'err'
    QUIT        = 'quit'
    SEPARATOR   = ' '
    BUF_SIZE    = 128
    
    
    def __init__(self, ip, port, app_name):
        self.ip = ip
        self.port = port
        self.app_name = app_name
        self.connect()
        

    def __del__(self):
        try:
            self.sock.close()
        except:
            pass


    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5)
        #self.sock.setdefaulttimeout(5)

        # For ssl support we can use self.ssl_sock instead of self.sock
        # self.ssl_sock = ssl.wrap_socket(s, ca_certs="cert.pem", cert_reqs=ssl.CERT_REQUIRED, ssl_version=ssl.PROTOCOL_TLSv1)
        
        self.sock.connect((self.ip, self.port))
        response = str(self.sock.recv(RKClusterLock.BUF_SIZE), 'ascii')        
        

    def acquire(self, wait, acquire_wait_time = 5, max_release_time = 5):

        data = None
        try:
            if not wait:
                acquire_wait_time = 0
            
            message = f'{RKClusterLock.ACQUIRE}{RKClusterLock.SEPARATOR}{self.app_name}{RKClusterLock.SEPARATOR}{acquire_wait_time}{RKClusterLock.SEPARATOR}{max_release_time}' 
            
            try:
                self.sock.sendall(bytes(message, 'ascii'))
            except ConnectionError as ce:
                self.connect()
                self.sock.sendall(bytes(message, 'ascii'))

            
            response = str(self.sock.recv(RKClusterLock.BUF_SIZE), 'ascii')
            response = response.strip()
            response_arr = response.split(RKClusterLock.SEPARATOR,1)
            
            if response_arr[0] == RKClusterLock.LOCKED:
                #Got the lock, lets return True
                try:
                    data = response_arr[1]
                except IndexError as ie:
                    pass               
                
                return True, data
            
            elif response_arr[0] == RKClusterLock.FAILED:
                return False, None
            else:
                data = response_arr[1]
                raise Exception(data)
                return False, None
                
        except socket.timeout as to:
            return False, None
        
        except ConnectionError as ce:
            self.connect()
            return False, None
                        
    
    def release(self, data = ""):
        if not isinstance(data, str):
            raise ValueError("parameter data must be of string type")
            return False

        message = RKClusterLock.RELEASE + RKClusterLock.SEPARATOR + data 
        self.sock.sendall(bytes(message, 'ascii'))

        # we take the response and ignore it
        response = str(self.sock.recv(RKClusterLock.BUF_SIZE), 'ascii')
        

        return True

