import time

from threading import Thread, current_thread
from rkclusterlock import RKClusterLock


def runClient():
    #rlock = RKClusterLock('localhost', 9191,'FKAPP')
    rlock = RKClusterLock('13.251.32.176', 9191,'FKAPP')
    cur_thread = current_thread()
    while 1:
        data = ""
        resp, data = rlock.acquire(wait=True, acquire_wait_time=5, max_release_time=5)
        if resp:
            try:                
                print(f"Got Lock for thread {cur_thread.name}  with data {data}")
                # Here is what we will do during the lock mode
                if data:
                    try:
                        int_data = int(data)
                        int_data = int_data + 1
                        data = str(int_data)
                    except:
                        data = "1"
                else:
                    data = "1"
                
                #time.sleep(10)
            finally:
                rlock.release(data)
        else:
            print(f"Failed to get Lock for thread {cur_thread.name}")
        time.sleep(1)
    


print("Lets start some clients now")

for i in range(200):
    print(f"Creating Client {i}")
    client = Thread(target=runClient)
    client.daemon = True
    client.start()
