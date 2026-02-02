import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Указываем путь к папке с шаблонами (она на уровень выше папки src)
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, '../frontend/templates')

app = Flask(__name__, template_folder=template_dir)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your_secret_key' # Нужно для работы session и flash

db = SQLAlchemy(app)