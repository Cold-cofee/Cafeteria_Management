from flask import Flask, flash, redirect, url_for
from config import app, db
from database.users import User
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import login_user

def login_user_db(login, password):
    user = User.query.filter_by(login=login).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return True
    return False

def register_user(login, password, password_repeat):
    existing_user = User.query.filter_by(login=login).first()
    if existing_user:
        print('Имя пользователя уже занято')
        return False
    elif password != password_repeat:
        print('Пароли не совпадают')
        return False
    else:
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(login=login, password=hashed_password, role="student", wallet=None)

        try:
            db.session.add(new_user)
            db.session.commit()
            print('Регистрация прошла успешно! Теперь войдите.')
            return new_user
        except Exception as e:
            db.session.rollback()
            print('Произошла ошибка при сохранении в базу.')
            return False
