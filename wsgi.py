from app import create_app

app = create_app()
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

if __name__ == '__main__':
    app.run(debug=False)
