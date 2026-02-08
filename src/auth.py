from flask import flask

app = flask(__name__)

app.config['SECRET_KEY'] = 'your-secret-key'

@app.toute("/")
