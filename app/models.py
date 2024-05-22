from flask_sqlalchemy import SQLAlchemy
from time import sleep
import threading
from app.core.notifier import SMSSender

db = SQLAlchemy()

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Items model for store company data
class Item(db.Model):
    name = db.Column(db.String(100),primary_key=True)
    password  = db.Column(db.String(100))
    message = db.Column(db.Text)
    did = db.Column(db.String(10))
    call_duration = db.Column(db.Integer)
    timezone_diff = db.Column(db.Integer)
    running = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean,default=False)

    def __repr__(self):
        return '<Item %r>' % self.name

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