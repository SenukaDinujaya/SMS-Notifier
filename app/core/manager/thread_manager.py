from app.core.manager.thread_runner import Run
from app.core.utils.log import LogSender
from time import time,sleep

class Manager:
    def __init__(self):
        self.threads = {}
        self.logger = LogSender()

    def add_thread(self, item_id, item):
        if item_id not in self.threads:
            self.threads[item_id] = Run(item)
        else:
            self.threads[item_id].restart()
        

    def remove_thread(self, item_id):
        if item_id in self.threads:
            self.threads[item_id].stop()
            self.logger.send_log([item_id,time(),'Stopped'])
            sleep(2) # This is tempararay
            del self.threads[item_id]

    def get_thread(self, item_id):
        return self.threads.get(item_id, None)