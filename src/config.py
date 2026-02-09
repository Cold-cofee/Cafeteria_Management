import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager    

# === 1. НАСТРОЙКА ПУТЕЙ ===
# Получаем папку, где лежит этот файл (src)
current_dir = os.path.dirname(os.path.abspath(__file__))
# Получаем корень проекта (на уровень выше)
root_dir = os.path.dirname(current_dir)

# Путь к шаблонам (Берем из Ветки admin3 - это важно для фронтенда!)
template_dir = os.path.join(root_dir, 'frontend', 'templates')

# Путь к базе данных (Берем из HEAD - у нас база cafeteria.db, а не просто database.db)
db_path = os.path.join(current_dir, "database", 'cafeteria.db')

# === 2. ИНИЦИАЛИЗАЦИЯ FLASK ===
# Важно: передаем template_folder, чтобы Flask видел HTML (из admin3)
app = Flask(__name__, template_folder=template_dir)

# === 3. КОНФИГУРАЦИЯ ===
app.config['SECRET_KEY'] = 'dev_key_secret'  # Любой ключ (взяли из HEAD)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}' # Путь к базе (из HEAD)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Отключаем лишние логи (из HEAD)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = 'login'#если не вошёл - на страницу входа