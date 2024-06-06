from app import create_app, db
from app.models import User, Item
from werkzeug.security import generate_password_hash

def create_superuser():
    if not User.query.first():
        username = input("Enter a username for the superuser: ")
        password = input("Enter a password for the superuser: ")
        hashed_password = generate_password_hash(password)
        superuser = User(username=username, password=hashed_password)
        db.session.add(superuser)
        db.session.commit()
        print("Superuser created successfully!")

app = create_app()
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_superuser()
        items = Item.query.all()
        if items!= None:
            for item in items:
                item.running = False
                item.active = False
            db.session.commit()
    print("App is starting...")