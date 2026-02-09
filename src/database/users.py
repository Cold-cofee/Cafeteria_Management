
from src.config import db

from cryptography.fernet import Fernet
from flask_login import UserMixin
import os
import secrets
import string
from flask_login import UserMixin

KEY = '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k='
cipher_suite = Fernet(KEY.encode())
from src.config import db


class User(db.Model, UserMixin): # Добавь UserMixin
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    role = db.Column(db.String(10), nullable=False, default='student')
    wallet = db.Column(db.String(255), nullable=False, unique=True)
    allergen = db.Column(db.String(255), nullable=True)
    preferences = db.Column(db.String(255), nullable=True)

    def get_wallet(self):
        try:
            # Расшифровываем номер кошелька для сервисов напарника
            return cipher_suite.decrypt(self.wallet.encode('utf-8')).decode('utf-8')
        except:
            return "0000000000000000"
    # Добавляем email в список аргументов здесь!
    def __init__(self, login, password, role="student", wallet=None, email=None):
        self.login = login
        self.password = password
        self.role = role
        self.email = email  # <--- Вот эта строчка важна

        # Логика кошелька (оставь ту, что у тебя там была)
        import secrets, string
        from cryptography.fernet import Fernet
        import os

        KEY = '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k='
        cipher_suite = Fernet(KEY.encode())

        if wallet is None:
            wallet_val = ''.join(secrets.choice(string.digits) for _ in range(16))
        else:
            wallet_val = wallet
        self.wallet = cipher_suite.encrypt(str(wallet_val).encode('utf-8')).decode('utf-8')