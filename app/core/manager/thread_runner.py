from app.core.sender import SMSSender
from app.models import Item
from time import sleep
import threading

#SMS Sender Session
class Run:
    def __init__(self, item:Item) -> None:
        self.run_it = True

        self.sender = SMSSender(
            user_name=item.name,password=item.password,
            sender_did=item.did,call_duration=item.call_duration,
            message=item.message,timezone_diff=item.timezone_diff,log=True)
        self.item = item
        self.thread = threading.Thread(target=self.run, name=item.name)
        self.thread.start()

    def run(self):
        while self.run_it:
            try:    
                self.sender.run()
            except:
                self.restart()

    def stop(self):
        self.run_it = False

    def restart(self):
        self.stop()
        sleep(5)
        self.run_it = True
        print('Restarting...')
        self.run()