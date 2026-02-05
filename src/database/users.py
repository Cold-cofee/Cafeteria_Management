from src.config import db
from cryptography.fernet import Fernet
import os
import secrets
import string


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    wallet = db.Column(db.String(255), nullable=False, unique=True)

    def __init__(self, login, password, role="student", wallet=None):
        self.login = login
        self.password = password
        self.role = role

        # Получаем ключ шифрования из окружения
        self.key = os.getenv("KEY")
        if not self.key:
            self.key = Fernet.generate_key().decode()

        if wallet is None:
            generated_wallet = ''.join(secrets.choice(string.digits) for _ in range(16))
            self.set_wallet(generated_wallet)
        else:
            self.set_wallet(wallet)

    def set_wallet(self, wallet_value):
        cipher_suite = Fernet(self.key)
        encrypted_text = cipher_suite.encrypt(str(wallet_value).encode('utf-8'))
        self.wallet = encrypted_text.decode('utf-8')

    def get_wallet(self):
        try:
            key = os.getenv("KEY") or self.key
            cipher_suite = Fernet(key)
            decrypted_text = cipher_suite.decrypt(self.wallet.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            return f"Ошибка расшифровки: {e}"

