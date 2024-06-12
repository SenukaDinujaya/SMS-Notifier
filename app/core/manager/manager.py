from app.core.sender import SMSSender
from threading import Thread
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
        self.watchdog_thread = Thread(target=self.__watchdog__, daemon=True)
        self.watchdog_thread.start()

    def add_to_queue(self, item: Item):
        item = copy.deepcopy(item)
        self.senders[item.name] = SMSSender(
            user_name=item.name,
            password=item.password,
            message=item.message,
            sender_did=item.did,
            call_duration=item.call_duration,
        )
        
        if not self.running:
            self.start_queue()
        self.log_sender.send_log([item.name, time.time(), 'Started'])

    def __run_queue__(self):
        try:
            self.log_sender.send_log(['Thread', time.time(), 'Started'])
            while self.senders and self.running:
                start_time = time.time()
                for key in list(self.senders.keys()):
                    self.senders[key].run()
                
                
                elapsed_time = time.time() - start_time
                if elapsed_time < 10:
                    time.sleep(10 - elapsed_time)

        except Exception as e:
            self.log_sender.send_log(['Thread', time.time(), str(e)])
        finally:
            self.log_sender.send_log(['Thread', time.time(), 'Stopped'])

    def __watchdog__(self):
        while True:
            if self.running and (self.queue_thread is None or not self.queue_thread.is_alive()):
                self.log_sender.send_log(['Watchdog', time.time(), 'Queue thread stopped, restarting...'])
                self.running = False
                self.start_queue()
            time.sleep(5)

    def start_queue(self):
        if not self.running:
            self.running = True
            self.queue_thread = Thread(target=self.__run_queue__,daemon=True)
            self.queue_thread.start()
            self.log_sender.send_log(['Queue', time.time(), 'Queue thread started'])

    def stop_queue(self):
        self.running = False
        if hasattr(self, 'queue_thread') and self.queue_thread.is_alive():
            self.queue_thread.join()
        self.log_sender.send_log(['Queue', time.time(), 'Queue thread stopped'])

    def stop(self, item: Item):
        if item.name in self.senders:
            del self.senders[item.name]
            self.log_sender.send_log(['System', time.time(), list(self.senders.keys())])
            if not self.senders:
                self.stop_queue()
        self.log_sender.send_log([item.name, time.time(), 'Stopped'])

    def restart_queue_thread(self):  # Not in use
        self.stop_queue()
        time.sleep(1)
        self.start_queue()
