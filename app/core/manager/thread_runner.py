from app.core.utils.log import LogSender
from app.core.sender import SMSSender
from app.models import Item
from time import sleep,time
import threading

#SMS Sender Session
class Run(threading.Thread):
    def __init__(self, item:Item) -> None:
        super().__init__()
        self.run_it = True
        self.logger = LogSender()
        self.sender = SMSSender(
            user_name=item.name,password=item.password,
            sender_did=item.did,call_duration=item.call_duration,
            message=item.message,log=True)
        self.item = item
        self.thread = threading.Thread(target=self.run, name=item.name)
        self.start()

    def run(self):
        self.logger.send_log([self.item.name,time(),'Started'])
        while self.run_it:
            try:    
                self.sender.run()
            except:
                self.restart()

    def stop(self):
        sleep(1)
        self.run_it = False


    def restart(self):
        self.logger.send_log([self.item.name,time(),'Restarting'])
        self.stop()
        sleep(5)
        self.run_it = True
        self.start()


# class Run:
#     def __init__(self, item:Item) -> None:
#         self.run_it = True
#         self.thread = threading.Thread(target=self.run, name=item.name)
#         self.thread.start()

#     def run(self):
#         ### The core of voip_client will go here
#         while self.run_it:
#             print('Hi')
#             sleep(1)
#             print('Bye')

#     def stop(self):
#         self.run_it = False