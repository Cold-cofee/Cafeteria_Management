import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

# SQLAlchemy
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
db_path = os.path.join(basepath, "src", "database",'cafeteria.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'

