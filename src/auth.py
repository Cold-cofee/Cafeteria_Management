import os
from flask_login import login_user, current_user
from datetime import datetime
from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from sqlalchemy import func
from src.service import CafeteriaService
from src.database.wallets import Wallet # Чтобы видеть баланс
from src.config import app, db
# Импортируем готовые модели из папки database
from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests


# --- ВСПОМОГАТЕЛЬНЫЕ МОДЕЛИ (Которых нет в базе данных проекта) ---

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class SupplyRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), default='Еда')
    status = db.Column(db.String(20), default='В ожидании')
    date = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Устанавливаем ключ шифрования для работы расшифровки кошелька
# (Тот же ключ, что использовался при создании User)
KEY = '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k='
cipher_suite = Fernet(KEY.encode())


# Функция для расшифровки кошелька прямо здесь
def decrypt_wallet(encrypted_wallet):
    try:
        return cipher_suite.decrypt(encrypted_wallet.encode('utf-8')).decode('utf-8')
    except:
        return "Ошибка кошелька"


@app.context_processor
def inject_models():
    return dict(User=User, SupplyRequest=SupplyRequest, Storage=Storage, Requests=Requests, Notification=Notification)


# --- МАРШРУТЫ ---

@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Проверка авторизации
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # 2. ОБРАБОТКА СОХРАНЕНИЯ ПРОФИЛЯ (POST)
    if request.method == 'POST':
        # Получаем данные из формы (из тех самых name="update_allergies")
        new_allergen = request.form.get('update_allergies')
        new_prefs = request.form.get('update_preferences')

        if new_allergen is not None:
            user.allergen = new_allergen
        if new_prefs is not None:
            user.preferences = new_prefs

        db.session.commit()
        # Редирект, чтобы при обновлении страницы данные не отправлялись повторно
        return redirect(url_for('index'))

    # 3. ПОДГОТОВКА ДАННЫХ ДЛЯ ОТОБРАЖЕНИЯ (GET)

    # Получаем баланс из таблицы Wallet, используя связь по номеру кошелька
    user_wallet = Wallet.query.filter_by(wallet_number=user.wallet).first()
    balance_text = f"{user_wallet.money} руб." if user_wallet else "0 руб."

    # Расшифровываем номер карты и добавляем баланс в строку
    wallet_display = f"💳 {decrypt_wallet(user.wallet)} ({balance_text})"

    # Уведомления пользователя
    notifs = Notification.query.filter_by(email=user.email).order_by(Notification.created_at.desc()).limit(5).all()

    # Фильтрация меню по категориям
    selected_cat = request.args.get('category', 'Все')
    query = Storage.query.filter(Storage.count > 0)
    if selected_cat != 'Все':
        query = query.filter_by(type_of_product=selected_cat)

    menu_items = query.all()

    # Список уникальных категорий для вкладок
    categories = [c[0] for c in db.session.query(Storage.type_of_product).distinct().all()]

    # Отзывы и история заказов текущего пользователя
    reviews = Review.query.order_by(Review.date.desc()).all()
    my_reqs = Requests.query.filter_by(user=user.id).order_by(Requests.date.desc()).all()

    # Перевод ролей для красивого отображения в бейдже
    role_translate = {'student': 'Ученик', 'cook': 'Повар', 'admin': 'Администратор'}

    return render_template('common/index.html',
                           user=user,
                           user_role_ru=role_translate.get(user.role, user.role),
                           wallet_number=wallet_display,
                           menu=menu_items,
                           categories=categories,
                           current_category=selected_cat,
                           reviews=reviews,
                           my_requests=my_reqs,
                           notifications=notifs)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(login=request.form.get('login')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user) # Для Flask-Login
            session['user_id'] = user.id
            session['role'] = user.role # <--- ОБЯЗАТЕЛЬНО ДОБАВЬ ЭТО
            return redirect(url_for('index'))
    return render_template('common/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Вытаскиваем данные из полей формы
        l = request.form.get('login')
        p = request.form.get('password')
        e = request.form.get('email')

        # Проверка, не занят ли логин
        if User.query.filter_by(login=l).first():
            flash("Логин занят")
            return redirect(url_for('register'))

        # Назначаем роль (первый юзер в базе будет админом)
        role = 'admin' if User.query.count() == 0 else 'student'

        # Создаем пользователя
        new_user = User(login=l, password=generate_password_hash(p), role=role, email=e)

        db.session.add(new_user)
        db.session.commit()

        # Сразу записываем в сессию, чтобы не логиниться заново
        session['user_id'] = new_user.id
        session['role'] = new_user.role

        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# --- ПАНЕЛЬ ПОВАРА ---

@app.route('/cook/storage')
def cook_storage():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    return render_template('cook/storage_manage.html', storage=Storage.query.all())


@app.route('/cook/request_supply', methods=['POST'])
def request_supply():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    name = request.form.get('name')
    count = request.form.get('count')
    cat = request.form.get('category', 'Еда')
    if name and count:
        db.session.add(SupplyRequest(item_name=name, quantity=int(count), category=cat))
        db.session.commit()
    return redirect(url_for('cook_storage'))


@app.route('/cook/delete_product/<int:item_id>')
def delete_product(item_id):
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    item = Storage.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('cook_storage'))


@app.route('/cook/orders')
def cook_orders():
    # Проверяем, залогинен ли пользователь и является ли он поваром/админом
    if session.get('role') not in ['cook', 'admin']:
        return redirect(url_for('login'))

    # Получаем все заказы из базы данных
    reqs = Requests.query.order_by(Requests.date.desc()).all()

    # Рендерим страницу заказов
    return render_template('cook/orders_manage.html', requests=reqs)


@app.route('/admin/panel')
def admin_panel():
    # Проверка прав: только админ может войти
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403

    # Получаем список всех пользователей (кроме самого себя)
    all_users = User.query.filter(User.id != session.get('user_id')).all()

    # Получаем запросы на поставку (если используешь модель SupplyRequest)
    # Если такой модели нет, закомментируй строку ниже и в render_template
    supply_reqs = SupplyRequest.query.filter_by(status='В ожидании').all()

    # Считаем статистику для красивого отображения
    today = datetime.utcnow().date()
    total_orders = Requests.query.filter_by(status='Одобрено').count()

    stats = {
        'total_orders': total_orders,
        'today_date': today.strftime('%d.%m.%Y')
    }

    return render_template('admin/admin_panel.html',
                           users=all_users,
                           supply_requests=supply_reqs,
                           stats=stats)


@app.route('/admin/approve_supply/<int:sup_id>/<string:status>')
def approve_supply(sup_id, status):
    # Проверка прав (только админ)
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    # Ищем запрос в базе по его ID
    sup = SupplyRequest.query.get(sup_id)

    if sup and sup.status == 'В ожидании':
        if status == 'approved':
            # Ищем товар на складе, чтобы увеличить его количество
            item = Storage.query.filter_by(name=sup.item_name).first()
            if item:
                item.count += sup.quantity
            else:
                # Если такого товара еще нет на складе — создаем его
                new_item = Storage(
                    name=sup.item_name,
                    count=sup.quantity,
                    type_of_product=sup.category,
                    price=0.0  # Можно поставить цену по умолчанию
                )
                db.session.add(new_item)

            sup.status = 'Одобрено'
        else:
            sup.status = 'Отклонено'

        db.session.commit()
        flash(f"Запрос на поставку {sup.item_name} {status}")

    return redirect(url_for('admin_panel'))


@app.route('/create_request', methods=['POST'])
def create_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    prod_name = request.form.get('item_name')

    # Ищем товар на складе
    item = Storage.query.filter_by(name=prod_name).first()
    if not item:
        flash("Товар не найден")
        return redirect(url_for('index'))

    # 1. Проверяем баланс перед покупкой
    user_wallet = Wallet.query.filter_by(wallet_number=user.wallet).first()
    if not user_wallet or user_wallet.money < item.price:
        flash(f"Недостаточно средств! Нужно {item.price} руб., у вас {user_wallet.money if user_wallet else 0} руб.")
        return redirect(url_for('index'))

    # 2. Вызываем сервис напарника для проведения транзакции
    # Это спишет деньги, уменьшит count в Storage и создаст билет
    success, msg, item_name = CafeteriaService.buy_product_transaction(user, item.id)

    if success:
        flash(f"Покупка успешна! Списано {item.price} руб.")
        return redirect(url_for('wallet_bp.ticket_page', item_name=item_name))
    else:
        flash(f"Ошибка: {msg}")
        return redirect(url_for('index'))


@app.route('/admin/update_price', methods=['POST'])
def update_price():
    # Проверка прав: только админ может менять цены
    if session.get('role') != 'admin':
        return "Доступ запрещен", 403

    item_id = request.form.get('item_id')
    new_price = request.form.get('price')

    # Находим товар в таблице storage
    item = Storage.query.get(item_id)

    if item and new_price:
        try:
            # Превращаем строку в число и сохраняем
            item.price = int(new_price)
            db.session.commit()
            flash(f"Цена на {item.name} успешно обновлена!")
        except ValueError:
            flash("Ошибка: Цена должна быть числом")

    return redirect(url_for('admin_panel'))



@app.route('/cook/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    # Проверяем права (повар или админ)
    if session.get('role') not in ['cook', 'admin']:
        return redirect(url_for('login'))

    # Ищем заказ
    order = Requests.query.get(req_id)
    if order:
        if new_status == 'approved':
            # Ищем товар, чтобы уменьшить его количество
            prod = Storage.query.filter_by(name=order.product).first()
            if prod and prod.count > 0:
                prod.count -= 1  # Списываем 1 единицу
                order.status = 'Одобрено'

                # Создаем уведомление для ученика (если есть такая модель)
                u = User.query.get(order.user)
                if u and u.email:
                    new_notif = Notification(
                        email=u.email,
                        subject="Заказ готов!",
                        message=f"Ваш заказ ({order.product}) выдан. Приятного аппетита!",
                        status='sent'
                    )
                    db.session.add(new_notif)
            else:
                flash("Ошибка: Товар закончился на складе!")
                return redirect(url_for('cook_orders'))

        elif new_status == 'rejected':
            order.status = 'Отклонено'

        db.session.commit()
        flash(f"Статус заказа №{req_id} обновлен")

    return redirect(url_for('cook_orders'))

@app.route('/admin/change_role/<int:user_id>/<string:new_role>')

def change_role(user_id, new_role):
    
    if current_user.role != 'admin':
        return "Доступ запрещен", 403

    allowed_roles = ['student', 'cook', 'admin']
    if new_role not in allowed_roles:
        flash("Некорректная роль")
        return redirect(url_for('admin_panel'))

    
    user = User.query.get(user_id)
    if user:
        
        if user.id == current_user.id and new_role != 'admin':
            flash("Вы не можете снять с себя права администратора!")
        else:
            user.role = new_role
            db.session.commit()
            flash(f"Роль пользователя {user.login} изменена на {new_role}")
    else:
        flash("Пользователь не найден")

    return redirect(url_for('admin_panel'))