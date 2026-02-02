import os
import secrets
import string
from cryptography.fernet import Fernet
from src.config import db


class User(db.Model):
    # Поля базы данных
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False)
    wallet = db.Column(db.String(255), nullable=False, unique=True)

    # Мы используем стандартный __init__, чтобы избежать ошибок с аргументами
    def __init__(self, login=None, password=None, role="student", wallet=None):
        self.login = login
        self.password = password
        self.role = role

        # Генерация кошелька, если он не передан
        if wallet is None:
            # Создаем 16 случайных цифр
            generated_wallet = ''.join(secrets.choice(string.digits) for _ in range(16))
            self.set_wallet(generated_wallet)
        else:
            self.set_wallet(wallet)

    # Метод для шифрования кошелька
    def set_wallet(self, wallet_value):
        key = os.getenv("KEY")
        # Если ключа нет в системе (например, забыли создать .env),
        # создаем временный, чтобы код не упал
        if not key:
            key = Fernet.generate_key().decode()
            os.environ["KEY"] = key

        cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)
        encrypted_text = cipher_suite.encrypt(str(wallet_value).encode('utf-8'))
        self.wallet = encrypted_text.decode('utf-8')

    # Метод для расшифровки кошелька
    def get_wallet(self):
        try:
            key = os.getenv("KEY")
            if not key:
                return "Error: No decryption key found"

            cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)
            decrypted_text = cipher_suite.decrypt(self.wallet.encode('utf-8'))
            return decrypted_text.decode('utf-8')
        except Exception as e:
            return f"Error decoding: {e}"

