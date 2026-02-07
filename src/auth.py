import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from sqlalchemy import func

from src.config import app, db
#from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)  # ВОТ ЭТО ПОЛЕ ОШИБКА НЕ ВИДЕЛА
    role = db.Column(db.String(10), nullable=False, default='student')
    wallet = db.Column(db.String(255), nullable=False, unique=True)
    allergen = db.Column(db.String(255), nullable=True)
    preferences = db.Column(db.String(255), nullable=True)

    def __init__(self, login, password, role="student", wallet=None, email=None):
        self.login = login
        self.password = password
        self.role = role
        self.email = email

        # Генерация и шифрование кошелька
        import secrets, string
        from cryptography.fernet import Fernet
        key = os.getenv("KEY", '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k=')
        cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)

        if wallet is None:
            wallet_val = ''.join(secrets.choice(string.digits) for _ in range(16))
        else:
            wallet_val = wallet

        self.wallet = cipher_suite.encrypt(str(wallet_val).encode('utf-8')).decode('utf-8')

    def get_wallet(self):
        from cryptography.fernet import Fernet
        key = os.getenv("KEY", '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k=')
        try:
            cipher_suite = Fernet(key.encode() if isinstance(key, str) else key)
            return cipher_suite.decrypt(self.wallet.encode('utf-8')).decode('utf-8')
        except:
            return "Ошибка расшифровки"
# Устанавливаем ключ шифрования (обязательно для работы кошелька)
os.environ["KEY"] = '3df5tPHi4nZQhof7gCKGPKOOy3z_HJEXmQNie1i55_k='


# --- ВНУТРЕННИЕ МОДЕЛИ СТОЛОВОЙ ---

# --- МОДЕЛИ ДАННЫХ ---

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

# ДОБАВЬ ЭТО СЮДА:
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False) # Убрали ForeignKey для упрощения связки
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)





@app.context_processor
def inject_models():
    return dict(User=User, SupplyRequest=SupplyRequest, Storage=Storage, Requests=Requests, Notification=Notification)


# --- ЛИЧНЫЙ КАБИНЕТ УЧЕНИКА ---
with app.app_context():
    db.create_all()
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # Сохранение аллергенов и предпочтений
    new_allergen = request.args.get('update_allergies')
    new_prefs = request.args.get('update_preferences')

    if new_allergen is not None or new_prefs is not None:
        if new_allergen is not None: user.allergen = new_allergen
        if new_prefs is not None: user.preferences = new_prefs
        db.session.commit()
        return redirect(url_for('index'))

    # Данные для профиля
    wallet_number = f"💳 {user.get_wallet()}"
    notifs = Notification.query.filter_by(email=user.email).order_by(Notification.created_at.desc()).limit(5).all()

    # Меню и фильтрация
    selected_cat = request.args.get('category', 'Все')
    query = Storage.query.filter(Storage.count > 0)
    if selected_cat != 'Все':
        query = query.filter_by(type_of_product=selected_cat)

    menu_items = query.all()
    categories = [c[0] for c in db.session.query(Storage.type_of_product).distinct().all()]
    reviews = Review.query.order_by(Review.date.desc()).all()
    my_reqs = Requests.query.filter_by(user=user.id).order_by(Requests.date.desc()).all()

    role_translate = {'student': 'Ученик', 'cook': 'Повар', 'admin': 'Администратор'}

    return render_template('common/index.html',
                           user=user, user_role_ru=role_translate.get(user.role, user.role),
                           wallet_number=wallet_number, menu=menu_items, categories=categories,
                           current_category=selected_cat, reviews=reviews,
                           my_requests=my_reqs, notifications=notifs)


# --- ЛОГИКА ЗАКАЗОВ ---

@app.route('/create_request', methods=['POST'])
def create_request():
    if 'user_id' not in session: return redirect(url_for('login'))
    prod_name = request.form.get('item_name')
    prod = Storage.query.filter_by(name=prod_name).first()

    if prod and prod.count > 0:
        new_req = Requests(user=session['user_id'], product=prod.name,
                           amount=1, status='В ожидании', date=datetime.now())
        db.session.add(new_req)
        db.session.commit()
    return redirect(url_for('index'))


# --- ПАНЕЛЬ ПОВАРА (ВЫДАЧА И СКЛАД) ---

@app.route('/cook/orders')
def cook_orders():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    reqs = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/orders_manage.html', requests=reqs)


@app.route('/cook/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    order = Requests.query.get(req_id)
    if order:
        if new_status == 'approved':
            prod = Storage.query.filter_by(name=order.product).first()
            if prod and prod.count > 0:
                prod.count -= 1
                order.status = 'Одобрено'

                # Создаем уведомление ученику
                u = User.query.get(order.user)
                if u and u.email:
                    db.session.add(Notification(email=u.email, subject="Заказ готов!",
                                                message=f"Ваш заказ ({order.product}) выдан. Приятного аппетита!",
                                                status='sent'))
            else:
                return "<h1>Ошибка: Товар закончился!</h1><a href='/cook/orders'>Назад</a>", 400
        elif new_status == 'rejected':
            order.status = 'Отклонено'
        db.session.commit()
    return redirect(url_for('cook_orders'))


@app.route('/cook/storage')
def cook_storage():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    return render_template('cook/storage_manage.html', storage=Storage.query.all())


@app.route('/cook/request_supply', methods=['POST'])
def request_supply():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    name, count, cat = request.form.get('name'), request.form.get('count'), request.form.get('category', 'Еда')
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


# --- ПАНЕЛЬ АДМИНИСТРАТОРА (АНАЛИТИКА) ---

@app.route('/admin/panel')
def admin_panel():
    if session.get('role') != 'admin': return "Доступ запрещен", 403

    all_users = User.query.filter(User.id != session['user_id']).all()
    supply_reqs = SupplyRequest.query.filter_by(status='В ожидании').all()

    # Статистика
    today = datetime.utcnow().date()
    visitors = db.session.query(func.count(func.distinct(Requests.user))).filter(
        func.date(Requests.date) == today).scalar()
    total_orders = Requests.query.filter_by(status='Одобрено').count()
    popular_query = db.session.query(Requests.product, func.count(Requests.product)).group_by(
        Requests.product).order_by(func.count(Requests.product).desc()).first()

    stats = {
        'visitors': visitors or 0,
        'total_orders': total_orders,
        'popular': popular_query[0] if popular_query else "Нет данных",
        'today_date': today.strftime('%d.%m.%Y')
    }
    return render_template('admin/admin_panel.html', users=all_users, supply_requests=supply_reqs, stats=stats)


@app.route('/admin/approve_supply/<int:sup_id>/<string:status>')
def approve_supply(sup_id, status):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    sup = SupplyRequest.query.get(sup_id)
    if sup and sup.status == 'В ожидании':
        if status == 'approved':
            item = Storage.query.filter_by(name=sup.item_name).first()
            if item:
                item.count += sup.quantity
            else:
                db.session.add(Storage(name=sup.item_name, count=sup.quantity, type_of_product=sup.category))
            sup.status = 'Одобрено'
        else:
            sup.status = 'Отклонено'
        db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/admin/change_role/<int:user_id>/<string:new_role>')
def change_role(user_id, new_role):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    u = User.query.get(user_id)
    if u:
        u.role = new_role
        db.session.commit()
    return redirect(url_for('admin_panel'))


# --- АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(login=request.form.get('login')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            session['user_id'], session['role'] = user.id, user.role
            return redirect(url_for('index'))
    return render_template('common/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        l, p, e = request.form.get('login'), request.form.get('password'), request.form.get('email')
        if User.query.filter_by(login=l).first(): return "Логин занят"

        role = 'admin' if User.query.count() == 0 else 'student'
        new_user = User(login=l, password=generate_password_hash(p), role=role)
        new_user.email = e  # Добавляем email для уведомлений

        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_id' not in session: return redirect(url_for('login'))
    text = request.form.get('review_text')
    if text:
        u = User.query.get(session['user_id'])
        db.session.add(Review(author=u.login, text=text))
        db.session.commit()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)