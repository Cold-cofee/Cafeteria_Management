<<<<<<< HEAD
from config import db
=======
>>>>>>> origin/админ3
from cryptography.fernet import Fernet
from flask_login import UserMixin
import os
import secrets
import string
from flask_login import UserMixin
<<<<<<< HEAD
=======
from src.config import db
>>>>>>> origin/админ3


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True) # новое
    role = db.Column(db.String(10), nullable=False)
    wallet = db.Column(db.String(255), nullable=False, unique=True)
    allergen = db.Column(db.String(255), nullable=True) # изменено
    preferences = db.Column(db.String(255), nullable=True) # новое

    def __init__(self, login, password, role="student", wallet=None, allergen=None):
        self.login = login
        self.password = password
        self.role = role
        self.allergen = allergen

        if wallet is None:
            generated_wallet = ''.join(secrets.choice(string.digits) for _ in range(16))
            self.set_wallet(generated_wallet)
        else:
            self.set_wallet(wallet)
            # Ключ шифрования: берем из системы ИЛИ генерируем временный (чтобы код не падал)
    key = os.getenv("KEY", Fernet.generate_key().decode())

    def set_wallet(self, wallet_value):
        # Превращаем ключ в байты, если он строка (Fernet требует байты)
        k = self.key.encode() if isinstance(self.key, str) else self.key
        cipher_suite = Fernet(k)
        
        # 1. Шифруем данные (превращаем в байты -> шифруем)
        encrypted_text = cipher_suite.encrypt(str(wallet_value).encode('utf-8'))
        
        # 2. Сохраняем как строку (чтобы записать в базу данных)
        self.wallet = encrypted_text.decode('utf-8')

    def get_wallet(self):
        try:
            cipher_suite = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
            decrypted_text = cipher_suite.decrypt(self.wallet.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            return f"Error: {e}"