from flask import Flask, redirect, url_for
import os
# Импортируем настройки из твоего конфига
from src.config import app, db, login_manager

# Импортируем модели, чтобы SQLAlchemy знал о таблицах
from src.database.users import User
from src.database.wallets import Wallet
from src.database.history import History
from src.database.menu import Menu
from src.database.store import Storage
from src.database.reviews import Reviews
from src.database.requests import Requests

# Импортируем маршруты (blueprints)
from src.router import wallet_bp

# === КРИТИЧЕСКИ ВАЖНЫЙ ИМПОРТ ===
# Мы импортируем auth, чтобы Flask зарегистрировал все @app.route из него
import src.auth as auth

# Инициализация менеджера логина
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == "__main__":
    # Логика проверки и создания базы данных
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if uri.startswith('sqlite:///'):
        # Для SQLite проверяем физическое наличие файла
        db_path = uri.replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print(f"Создание базы данных по пути: {db_path}")
            with app.app_context():
                db.create_all()
            print("База данных успешно создана!")
    else:
        # Для других БД просто создаем таблицы
        with app.app_context():
            db.create_all()

    # Регистрация блюпринта кошелька
    app.register_blueprint(wallet_bp)

    print('Сервер успешно настроен. Запуск...')
    # Запускаем приложение
    app.run(debug=True, host="0.0.0.0", port=5000)