from app import create_app, db
from app.models import User
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_superuser()
    app.run(debug=True)
