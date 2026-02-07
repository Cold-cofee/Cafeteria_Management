import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from src.config import app, db
from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests


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
    category = db.Column(db.String(50), default='Еда')  # Новое поле для категории
    status = db.Column(db.String(20), default='В ожидании')
    date = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


# Глобальный доступ к моделям в HTML
@app.context_processor
def inject_models():
    return dict(User=User, SupplyRequest=SupplyRequest, Storage=Storage)


# --- ЛОГИКА ЛИЧНОГО КАБИНЕТА ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    update_val = request.args.get('update_allergies')
    if update_val is not None:
        user.allergies = update_val
        db.session.commit()
        return redirect(url_for('index'))

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
            else:
                return "<h1>Ошибка: Товар закончился!</h1><a href='/cook/orders'>Назад</a>", 400
        elif new_status == 'rejected':
            order.status = 'Отклонено'
        db.session.commit()
    return redirect(url_for('cook_orders'))


# --- АДМИН-ПАНЕЛЬ И ПОПОЛНЕНИЕ ---

@app.route('/admin/panel')
def admin_panel():
    if session.get('role') != 'admin': return "Доступ запрещен", 403
    all_users = User.query.filter(User.id != session['user_id']).all()
    supply_reqs = SupplyRequest.query.filter_by(status='В ожидании').all()
    return render_template('admin/admin_panel.html', users=all_users, supply_requests=supply_reqs)


@app.route('/admin/change_role/<int:user_id>/<string:new_role>')
def change_role(user_id, new_role):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    target = User.query.get(user_id)
    if target:
        target.role = new_role
        db.session.commit()
    return redirect(url_for('admin_panel'))


@app.route('/admin/approve_supply/<int:sup_id>/<string:status>')
def approve_supply(sup_id, status):
    if session.get('role') != 'admin': return redirect(url_for('login'))
    sup = SupplyRequest.query.get(sup_id)
    if sup and sup.status == 'В ожидании':
        if status == 'approved':
            # Ищем товар по имени
            item = Storage.query.filter_by(name=sup.item_name).first()
            if item:
                item.count += sup.quantity
            else:
                # Если товара нет, создаем его с указанной категорией
                db.session.add(Storage(name=sup.item_name, count=sup.quantity, type_of_product=sup.category))
            sup.status = 'Одобрено'
        else:
            sup.status = 'Отклонено'
        db.session.commit()
    return redirect(url_for('admin_panel'))


# --- ПАНЕЛЬ ПОВАРА ---

@app.route('/cook/orders')
def cook_orders():
    if session.get('role') not in ['cook', 'admin']: return redirect(url_for('login'))
    reqs = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/orders_manage.html', requests=reqs)


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
        # Сохраняем имя и категорию отдельно
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


# --- СИСТЕМА (Вход, Регистрация, Отзывы) ---

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
            session['user_id'], session['role'] = user.id, user.role
            return redirect(url_for('index'))
    return render_template('common/login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        l, p = request.form.get('login'), request.form.get('password')
        if User.query.filter_by(login=l).first(): return "Логин занят"
        role = 'admin' if User.query.count() == 0 else 'student'
        db.session.add(User(login=l, password=generate_password_hash(p), role=role))
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

