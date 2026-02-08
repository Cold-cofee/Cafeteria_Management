import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Абсолютный путь к базе данных
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(basepath, "src", "database",'cafeteria.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)