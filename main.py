from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src.database.users import User
from src.database.wallets import Wallet
from src.database.history import History
from src.database.menu import Menu
from src.database.store import Storage
from src.database.reviews import Reviews
from src.database.requests import Requests
from src.config import *

if __name__ == "__main__":

    with app.app_context():
        db.create_all()