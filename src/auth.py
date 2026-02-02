import os
import secrets
import string
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

# Импортируем настройки и модель
from src.config import app, db
from src.database.users import User

# 1. ГАРАНТИЯ КЛЮЧА (нужен для шифрования кошелька)
if not os.getenv("KEY"):
    os.environ["KEY"] = Fernet.generate_key().decode()

# 2. ИНИЦИАЛИЗАЦИЯ БАЗЫ
with app.app_context():
    db.create_all()


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        l_val = request.form.get('username') or request.form.get('login')
        p_val = request.form.get('password')
        r_val = request.form.get('role', 'student')

        if not l_val or not p_val:
            return "Ошибка: заполните поля!"

        hashed_pw = generate_password_hash(p_val)

        try:
            with app.app_context():
                # ТЕПЕРЬ ПЕРЕДАЕМ ВСЁ СРАЗУ В КОНСТРУКТОР
                new_user = User(login=l_val, password=hashed_pw, role=r_val)

                db.session.add(new_user)
                db.session.commit()
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return f"Критическая ошибка: {str(e)}"

    return render_template('common/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u_login = request.form.get('username') or request.form.get('login')
        u_password = request.form.get('password')

        user = User.query.filter_by(login=u_login).first()

        if user and check_password_hash(user.password, u_password):
            session['user_id'] = user.id
            session['role'] = user.role
            return f"Вы вошли! Ваш кошелек: {user.get_wallet()}"

        return "Неверный логин или пароль"

    return render_template('common/login.html')


@app.route('/')
def index():
    return "Главная. <a href='/register'>Регистрация</a>"


if __name__ == '__main__':
    app.run(debug=True, port=5000)

