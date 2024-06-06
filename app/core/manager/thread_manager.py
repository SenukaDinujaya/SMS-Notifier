from app.core.manager.thread_runner import Run
from app.core.utils.log import LogSender
from time import time

from app.core.manager.thread_runner import Run
from app.core.utils.log import LogSender
from time import time

class Manager:
    def __init__(self):
        self.threads = {}
        self.logger = LogSender()

    def add_thread(self, item_id, item):
        # Create a new thread if it doesn't exist or it has been stopped and removed
        if item_id not in self.threads:
            self.threads[item_id] = Run(item)
            self.logger.send_log([item_id, time(), 'Started'])

    def remove_thread(self, item_id):
        if item_id in self.threads:
            self.threads[item_id].stop()
            
            # Ensure the thread has fully stopped
            self.threads[item_id].join()

            del self.threads[item_id]
            self.logger.send_log([item_id, time(), 'Stopped'])

    def restart_thread(self, item_id, item):
        # Remove the existing thread if it exists
        if item_id in self.threads:
            self.remove_thread(item_id)
        
        # Add a new thread
        self.add_thread(item_id, item)

    def get_thread(self, item_id):
        return self.threads.get(item_id, None)