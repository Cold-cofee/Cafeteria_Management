import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

# Импорты из файлов проекта
from src.config import db
from src.database.users import User
from src.database.store import Storage
app = Flask(__name__, template_folder='../frontend/templates')
app.config['SECRET_KEY'] = 'super-secret-key-2026'

# 1. Настройка пути к базе данных
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, '..', 'database.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(db_path)}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 2. КЛЮЧ ИЗ ТВОЕГО .ENV
# Устанавливаем ключ, чтобы Fernet в модели User мог зашифровать кошелек
os.environ["KEY"] = '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k='


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login = request.form.get('login')
        password = request.form.get('password')
        role = request.form.get('role')
        allergies = request.form.get('allergies')  # Получаем аллергии из формы

        with app.app_context():
            # Проверка: не занят ли логин
            if User.query.filter_by(login=login).first():
                return "<h1>Этот логин уже занят!</h1><a href='/register'>Назад</a>"

            # Хешируем пароль
            hashed_pw = generate_password_hash(password)

            try:
                # Создаем объект пользователя
                new_user = User()


                # Это создаст юзера и зашифрует кошелек ключом из os.environ
                new_user.init(login=login, password=hashed_pw, role=role)

                # Если нужно где-то сохранить аллергии, их нужно добавить в модель User.
                # Пока просто выведем в консоль, чтобы программа не падала.
                if allergies:
                    print(f"У пользователя {login} аллергия на: {allergies}")

                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                return f"<h1>Ошибка при регистрации: {e}</h1>"

    return render_template('common/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        password_val = request.form.get('password')

        with app.app_context():
            user = User.query.filter_by(login=login_val).first()

            if user and check_password_hash(user.password, password_val):
                # Расшифровка кошелька
                try:
                    wallet_info = user.get_wallet()
                except Exception as e:
                    wallet_info = "Ошибка расшифровки"

                return f"""
                <div style="text-align:center; margin-top:50px; font-family: sans-serif;">
                    <h1 style="color: #2c3e50;">Вход выполнен!</h1>
                    <p>Привет, <b>{user.login}</b>!</p>
                    <p>Роль: <span style="color: #3498db;">{user.role}</span></p>
                    <p>Твой номер кошелька: <b style="background: #eee; padding: 5px;">{wallet_info}</b></p>
                    <hr style="width: 50%;">
                    <a href='/register'>Выйти / Зарегистрировать другого</a>
                </div>
                """
            else:
                return "<h1>Неверный логин или пароль!</h1><a href='/login'>Назад</a>"

    return render_template('common/login.html')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

# Импортируем модель Storage из файла store.py
from src.database.store import Storage

# --- ЛОГИКА СКЛАДА ---

@app.route('/storage', methods=['GET', 'POST'])
def storage_list():
    if request.method == 'POST':
        # Получаем данные из формы (названия берем из твоего будущего HTML)
        name = request.form.get('name')
        count = request.form.get('count')
        type_of_product = request.form.get('type_of_product')

        with app.app_context():
            # Создаем объект Storage
            new_item = Storage(name=name, count=int(count), type_of_product=type_of_product)
            db.session.add(new_item)
            db.session.commit()
        return redirect(url_for('storage_list'))

    # Получаем все товары для таблицы
    items = Storage.query.all()
    return render_template('common/storage.html', items=items)

@app.route('/storage/delete/<int:item_id>')
def delete_storage_item(item_id):
    with app.app_context():
        item = Storage.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
    return redirect(url_for('storage_list'))
# Страница склада для повара
@app.route('/cook/inventory', methods=['GET', 'POST'])
def manage_inventory():
    if request.method == 'POST':
        # Собираем данные из полей формы
        name = request.form.get('name')
        count = request.form.get('count')
        product_type = request.form.get('type_of_product')

        with app.app_context():
            # Создаем запись, используя init от nyKilka
            new_item = Storage(name=name, count=int(count), type_of_product=product_type)
            db.session.add(new_item)
            db.session.commit()
        return redirect(url_for('manage_inventory'))

    # Получаем все товары из базы для отображения
    all_items = Storage.query.all()
    return render_template('cook/inventory.html', items=all_items)

# Функция удаления товара
@app.route('/cook/inventory/delete/<int:item_id>')
def delete_item(item_id):
    with app.app_context():
        item = Storage.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
    return redirect(url_for('manage_inventory'))





