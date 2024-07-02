from app.core.sender import SMSSender
from threading import Thread, Lock
from app.models import Item
from app.core.utils.log import LogSender
from typing import Dict
import time
import copy


class Manager:
    
    def __init__(self) -> None:
        self.senders: Dict[str, SMSSender] = {}
        self.running = False
        self.log_sender = LogSender()
        self.queue_thread = None
        self.restarter = None
        self.restart_lock = Lock()

    def add_to_queue(self, item: Item):
        item = copy.deepcopy(item)
        self.senders[item.name] = SMSSender(
            user_name=item.name,
            password=item.password,
            message=item.message,
            sender_did=item.did,
            call_duration=item.call_duration,
            limit_to_one_DID=item.limit_to_one_DID
        )

        if not self.running:
            self.__start_queue__()
        self.log_sender.send_log([item.name, time.time(), 'Started'])

    def __run_queue__(self):
        try:
            self.log_sender.send_log(['Thread', time.time(), 'Started'])
            loop_time = time.time()
            while self.senders and self.running:
                start_time = time.time()
                for key in list(self.senders.keys()):
                    self.senders[key].run()
                
                elapsed_time = time.time() - start_time
                if elapsed_time < 10: # Will run it every 10 seconds
                    time.sleep(10 - elapsed_time)

                if time.time() - loop_time > 3600*6: # Will restart the thread every 1h
                    self.__start_restarter_thread__()

        except Exception as e:
            self.log_sender.send_log(['Thread', time.time(), str(e)])
            self.__start_restarter_thread__()
            
        finally:
            self.log_sender.send_log(['Thread', time.time(), 'Stopped'])

    def __start_queue__(self):
        if not self.running:
            self.running = True
            self.queue_thread = Thread(target=self.__run_queue__,daemon=True)
            self.queue_thread.start()
            self.log_sender.send_log(['Queue', time.time(), 'Queue thread started'])

    def __stop_queue__(self):
        self.running = False
        if hasattr(self, 'queue_thread') and self.queue_thread.is_alive():
            self.queue_thread.join()
        self.log_sender.send_log(['Queue', time.time(), 'Queue thread stopped'])

    def stop(self, item: Item):
        if item.name in self.senders:
            del self.senders[item.name]
            self.log_sender.send_log(['System', time.time(), str(item.name)])
            if not self.senders:
                self.__stop_queue__()
        self.log_sender.send_log([item.name, time.time(), 'Stopped'])

    def __restart_queue_thread__(self):
        self.__stop_queue__()
        time.sleep(1)
        self.__start_queue__()

    def __start_restarter_thread__(self):
        with self.restart_lock:
            if self.restarter is None or not self.restarter.is_alive():
                self.restarter = Thread(target=self.__restart_queue_thread__)
                self.restarter.start()