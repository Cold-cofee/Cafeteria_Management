import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from src.config import app, db
from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests


# Модель отзывов (храним прямо здесь для удобства)
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()
@app.context_processor
def inject_user():
    return dict(User=User)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Защита: если пользователя нет в базе (база была удалена), выходим
    if not user:
        session.clear()
        return redirect(url_for('login'))

    # НОВОЕ: Обработка обновления аллергий
    update_val = request.args.get('update_allergies')
    if update_val is not None:
        user.allergies = update_val
        db.session.commit()
        return redirect(url_for('index'))

    # Кошелек
    wallet_number = f"💳 ШК-{user.id + 1000:05d}"

    selected_cat = request.args.get('category', 'Все')
    query = Storage.query.filter(Storage.count > 0)
    if selected_cat != 'Все':
        query = query.filter_by(type_of_product=selected_cat)

    menu_items = query.all()
    categories = [c[0] for c in db.session.query(Storage.type_of_product).distinct().all()]
    reviews = Review.query.order_by(Review.date.desc()).all()
    my_reqs = Requests.query.filter_by(user=user.id).order_by(Requests.date.desc()).all()

    role_translate = {'student': 'Ученик', 'cook': 'Повар', 'admin': 'Администратор'}
    user_role_ru = role_translate.get(user.role, user.role)

    return render_template('common/index.html',
                           user=user, user_role_ru=user_role_ru, wallet_number=wallet_number,
                           menu=menu_items, categories=categories,
                           current_category=selected_cat, reviews=reviews,
                           my_requests=my_reqs)


# --- ЛОГИКА ЗАКАЗОВ (ОБНОВЛЕННАЯ) ---

@app.route('/create_request', methods=['POST'])
def create_request():
    if 'user_id' not in session: return redirect(url_for('login'))

    prod = Storage.query.filter_by(name=request.form.get('item_name')).first()

    # Проверяем наличие, но НЕ уменьшаем count здесь
    if prod and prod.count > 0:
        new_req = Requests(user=session['user_id'], product=prod.name,
                           amount=1, status='В ожидании', date=datetime.now())
        db.session.add(new_req)
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/cook/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))

    order = Requests.query.get(req_id)
    if order:
        if new_status == 'approved':
            # Списываем со склада ТОЛЬКО ПРИ ОДОБРЕНИИ
            prod = Storage.query.filter_by(name=order.product).first()
            if prod and prod.count > 0:
                prod.count -= 1
                order.status = 'Одобрено'
            else:
                return "<h1>Ошибка: Товар закончился!</h1><a href='/cook/orders'>Назад</a>", 400

        elif new_status == 'rejected':
            order.status = 'Отклонено'

        db.session.commit()
    return redirect(url_for('cook_orders'))


# --- АДМИН-ПАНЕЛЬ ---

@app.route('/admin/panel')
def admin_panel():
    if 'user_id' not in session or session.get('role') != 'admin':
        return "<h1>Доступ запрещен</h1>", 403
    all_users = User.query.filter(User.id != session['user_id']).all()
    return render_template('admin/admin_panel.html', users=all_users)


@app.route('/admin/change_role/<int:user_id>/<string:new_role>')
def change_role(user_id, new_role):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    target_user = User.query.get(user_id)
    if target_user:
        target_user.role = new_role
        db.session.commit()
    return redirect(url_for('admin_panel'))


# --- ПАНЕЛЬ ПОВАРА ---

@app.route('/cook/storage')
def cook_storage():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    return render_template('cook/storage_manage.html', storage=Storage.query.all())


@app.route('/cook/orders')
def cook_orders():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    return render_template('cook/orders_manage.html', requests=Requests.query.order_by(Requests.date.desc()).all())


@app.route('/cook/add_product', methods=['POST'])
def add_product():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    name = request.form.get('name')
    count = int(request.form.get('count', 0))
    category = request.form.get('category', 'Еда')
    existing = Storage.query.filter_by(name=name).first()
    if existing:
        existing.count += count
    else:
        db.session.add(Storage(name=name, count=count, type_of_product=category))
    db.session.commit()
    return redirect(url_for('cook_storage'))


@app.route('/cook/delete_product/<int:item_id>')
def delete_product(item_id):
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    item = Storage.query.get(item_id)
    if item: db.session.delete(item); db.session.commit()
    return redirect(url_for('cook_storage'))


# --- СИСТЕМНЫЕ ФУНКЦИИ ---

@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_id' not in session: return redirect(url_for('login'))
    text = request.form.get('review_text')
    if text:
        user = User.query.get(session['user_id'])
        db.session.add(Review(author=user.login, text=text))
        db.session.commit()
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(login=request.form.get('login')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('index'))
    return render_template('common/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        login_val = request.form.get('login')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        if User.query.filter_by(login=login_val).first(): return "Логин занят"
        db.session.add(User(login=login_val, password=generate_password_hash(password), role=role))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

