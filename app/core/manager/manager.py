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
        self.log_sender=LogSender()

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
        while self.senders and self.running:
            start_time = time.time()
            for key in list(self.senders.keys()):
                self.senders[key].run()
            
            elapsed_time = time.time() - start_time
            if elapsed_time < 10:
                time.sleep(10 - elapsed_time)

    def start_queue(self):
        if not self.running:
            self.running = True
            self.queue_thread = Thread(target=self.__run_queue__)
            self.queue_thread.start()
            

    def stop_queue(self):
        self.running = False
        if hasattr(self, 'queue_thread') and self.queue_thread.is_alive():
            self.queue_thread.join()

    def stop(self, item: Item):
        if item.name in self.senders:
            del self.senders[item.name]
            if not self.senders:
                self.stop_queue()
        self.log_sender.send_log([item.name, time.time(), 'Stoped'])
        
