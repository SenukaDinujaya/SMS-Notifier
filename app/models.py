from . import db

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
    running = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean,default=False)

    def __repr__(self):
        return '<Item %r>' % self.name
    
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company = db.Column(db.String(100))
    timestamp = db.Column(db.String(50))
    record = db.Column(db.Text)