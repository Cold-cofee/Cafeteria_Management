from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

from src.config import app, db
from src.database.users import User
from src.database.wallets import Wallet
from src.database.history import History
from src.database.menu import Menu
from src.database.store import Storage
from src.database.reviews import Reviews
from src.database.requests import Requests

if __name__ == "__main__":
    # Получаем путь к базе данных из конфига
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///'):
        db_path = uri.replace('sqlite:///', '')
        
        if not os.path.exists(db_path):
            print(f"Создание базы данных по пути: {db_path}")
            with app.app_context():
                db.create_all()
            print("База данных успешно создана!")
    else:
        with app.app_context():
            db.create_all()