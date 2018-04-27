import threading
import queue
from enum import Enum
import time
from .rklogger import RKLogger 

class ThreadStatus(Enum):
    NOT_STARTED = 1
    IDLE = 2
    RUNNING = 3
    TERMINATED = 4

MAX_JOBS_PER_THREAD = 10

class RKThread(threading.Thread):
    "Thread-Pool Runner thread"
    def __init__(self, manager, thread_id, queue, queue_lock, on_run, on_complete, on_error):
        threading.Thread.__init__(self)
        self.manager = manager
        self.thread_id = thread_id
        self.status = ThreadStatus.NOT_STARTED
        self.queue = queue
        self.queue_lock = queue_lock
        self.jobs_done = 0
        self.daemon = True

        self.do_terminate = False
        self._on_run = on_run
        self._on_complete = on_complete
        self._on_error = on_error
        RKLogger.debug(f'Thread Id: {self.thread_id} - Created')
    
    def run(self):
        RKLogger.debug(f'Thread Id: {self.thread_id} - Running')
        while self.jobs_done < MAX_JOBS_PER_THREAD and not self.do_terminate:
            try:
                self.status = ThreadStatus.IDLE
                RKLogger.debug(f'Thread Id: {self.thread_id} - Idle')
                try:
                    job = self.queue.get(True, 5)
                except:
                    RKLogger.debug(f'Thread Id: {self.thread_id} - Job Queue Empty')
                    continue
                
                if job is None:
                    RKLogger.error(f'Thread Id: {self.thread_id} - Job cannot be of type None')
                    continue

                RKLogger.debug(f'Thread Id: {self.thread_id} - Job Details = {job}')

                try:            
                    self.status = ThreadStatus.RUNNING
                    self.jobs_done += 1
                    self._on_run(self.thread_id, self.jobs_done, job)                    
                except Exception as e:
                    self._on_error(self.thread_id, e, job)
                finally:
                    self._on_complete(self.thread_id, self.jobs_done, job)
                    self.status = ThreadStatus.IDLE
            except queue.Empty as emp:
                pass
            
        RKLogger.debug(f'Thread Id: {self.thread_id} - Terminating')
        self.status = ThreadStatus.TERMINATED
        mgr.unregister_thread(self.thread_id)
    


class RKThreadManager:
    "Thread-Pool Manager"
    def __init__(self, max_threads, on_run, on_complete, on_error):        

        self._max_threads = max_threads

        self._on_run = on_run
        self._on_complete = on_complete
        self._on_error = on_error
        
        self._active_threads = 0
        self._counter = 0
        
        self.terminating = False
        
        self._thread_lock = threading.Lock()
        self.queue_lock = threading.Lock()
        
        self.threads = dict()
        self.queue =  queue.Queue(100)    
        RKLogger.debug(f'ThreadManager - Initialized')


    def start(self, thread_count = 0):
        
        RKLogger.debug(f'ThreadManager - Starting {thread_count} worker threads')
        if not self.terminating:            
            if thread_count == 0:
                thread_count = self._max_threads
            elif thread_count > self._max_threads:
                return False
    
            i = 0
            while i < thread_count:
                self.new_thread()
                i += 1
            return True
        else:
            return False
        
    
    def new_thread(self):
        if not self.terminating: 
            if self._active_threads < self._max_threads:
                if self._thread_lock.acquire(True, 30):
                    try:
                        thread = RKThread(self, self._counter, self.queue, self.queue_lock, self._on_run, self._on_complete, self._on_error)
                        self.threads[self._counter] = thread                
                        self._counter += 1
                        self._active_threads += 1
                    finally:
                        self._thread_lock.release()
                    
                    thread.start()
                    return False
                else:
                    # could not acquire thread lock
                    return False
            else:
                # reached maxed thread
                return False
        else:
            return False
 

    def unregister_thread(self, threadid):
        if self._thread_lock.acquire(True, 30):
            try:
                del self.threads[threadid]
                self._active_threads -= 1
            finally:
                self._thread_lock.release()
        
        if not self.terminating:
            self.new_thread()
            

    def add_job(self, job_data_object):
        if not self.terminating:
            if self.queue_lock.acquire(True, 30) :
                try:
                    self.queue.put_nowait(job_data_object)
                    return True
                except queue.Full as full:
                    return False
                except:
                    return False
                finally:
                    self.queue_lock.release()     
            else:
                # Failed to acquire Queue Lock
                return False
        else:
            return False
        

    def wait_finish(self):
        def wait_for_thread_terminate():
            while self._active_threads != 0:
                time.sleep(1)
            
        RKLogger.debug(f'ThreadManager - Launching WAIT thread')
        wait_thread = threading.Thread(target = wait_for_thread_terminate, args=(), kwargs={})
        wait_thread.daemon = True
        wait_thread.start()
        wait_thread.join()


    def terminate(self):
        RKLogger.debug(f'ThreadManager - Terminating all ({self._active_threads}) threads')
        self.terminating = True
        self._thread_lock.acquire(True, 30)
        try:
            for index,thread in self.threads.items():
                thread.do_terminate = True
        finally:
            self._thread_lock.release()


    
    
if __name__ == '__main__':
    
    RKLogger.initialize('rkthread', 'rkthread.log')
    
    print('Testing Message %s','By RK')
    
    
    def dorun(thread_id, jobs_done, job_data):
        print(f'Running on ThreadId {thread_id}, JobsDone {jobs_done}, data {job_data}')    
    
    def docomplete(thread_id, jobs_done, job_data):
        print(f'Completing on ThreadId {thread_id}, JobsDone {jobs_done}, data {job_data}')


    def doerror(thread_id, error, job_data):
        print(f'Error on ThreadId {thread_id} with data {job_data}')
    
    
    mgr = RKThreadManager(11, dorun, docomplete, doerror)
    mgr.start(1)
    i = 0
    while i<11:
        i +=1
        print(f'Adding Job {i}')
        mgr.add_job(f'Job {i}')

    time.sleep(1)    
#    mgr.terminate()
#   or 
    mgr.wait_finish()
    
    print ('Process Completed')