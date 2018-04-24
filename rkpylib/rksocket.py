import socket

""" Yet to be developed """

def process_start(s_sock):
    raw_request = s_sock.recv(32)
    s_sock.send(ok_message)
    s_sock.close()
    
    sys.exit(0) #kill the child process

       
def create_socket_connection(ipaddr, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((ipaddr, port))
    s.listen(1)
    try:
        while True:
            try:
                s_sock, s_addr = s.accept()
                p = Process(target=process_start, args=(s_sock,))
                p.start()
            except socket.error:
                # stop the client disconnect from killing us
                print('Got a socket error')
            
    except Exception as e:
        print(f'An exception occured.. {e}')
        sys.exit(1)
    finally:
        s.close()
                

create_socket_connection('127.0.0.1', 8383)