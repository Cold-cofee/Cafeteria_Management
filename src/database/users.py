from cryptography.fernet import Fernet
import os
import secrets
import string
from flask_login import UserMixin
from src.config import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    wallet = db.Column(db.String(255), nullable=False, unique=True)
    allergen = db.Column(db.JSON, nullable=True)  # Используем их формат JSON

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

    # Ключ должен быть в переменной окружения или задан строкой для теста
    # ВАЖНО: Ключ Fernet должен быть base64-encoded 32-byte key
    key = os.getenv("KEY", Fernet.generate_key().decode())

    def set_wallet(self, wallet_value):
        cipher_suite = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
        encrypted_text = cipher_suite.encrypt(str(wallet_value).encode('utf-8'))
        self.wallet = encrypted_text.decode('utf-8')

    def get_wallet(self):
        try:
            cipher_suite = Fernet(self.key.encode() if isinstance(self.key, str) else self.key)
            decrypted_text = cipher_suite.decrypt(self.wallet.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            return f"Error: {e}"