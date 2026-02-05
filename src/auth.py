import os
from datetime import datetime
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from src.config import app, db
from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(80), nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])

    selected_cat = request.args.get('category', 'Все')
    # Показываем только то, что есть в наличии (count > 0)
    query = Storage.query.filter(Storage.count > 0)
    if selected_cat != 'Все':
        query = query.filter_by(type_of_product=selected_cat)

    menu_items = query.all()
    categories = [c[0] for c in db.session.query(Storage.type_of_product).distinct().all()]
    reviews = Review.query.order_by(Review.date.desc()).all()
    my_reqs = Requests.query.filter_by(user=user.id).order_by(Requests.date.desc()).all()

    return render_template('common/index.html',
                           user=user, wallet_number=user.get_wallet(),
                           menu=menu_items, categories=categories,
                           current_category=selected_cat, reviews=reviews,
                           my_requests=my_reqs)


@app.route('/create_request', methods=['POST'])
def create_request():
    if 'user_id' not in session: return redirect(url_for('login'))

    product_name = request.form.get('item_name')
    # Находим товар на складе
    product_in_store = Storage.query.filter_by(name=product_name).first()

    # Проверяем, осталось ли что-то в наличии
    if product_in_store and product_in_store.count > 0:
        # 1. Уменьшаем количество на складе
        product_in_store.count -= 1

        # 2. Создаем заявку
        new_req = Requests(user=session['user_id'], product=product_name,
                           amount=1, status='pending', date=datetime.now())

        db.session.add(new_req)
        db.session.commit()
    else:
        # Если еда кончилась, пока мы нажимали кнопку
        print("Ошибка: еда закончилась!")

    return redirect(url_for('index'))


# --- ПАНЕЛЬ ПОВАРА: УПРАВЛЕНИЕ СКЛАДОМ ---

@app.route('/cook/storage')
def cook_storage():
    # Проверка роли (только для повара)
    if 'user_id' not in session or session.get('role') != 'cook':
        return redirect(url_for('login'))

    # Получаем все товары со склада
    all_storage = Storage.query.all()
    return render_template('cook/storage_manage.html', storage=all_storage)


@app.route('/cook/add_product', methods=['POST'])
def add_product():
    if session.get('role') != 'cook': return redirect(url_for('login'))

    name = request.form.get('name')
    count = int(request.form.get('count', 0))
    category = request.form.get('category', 'Еда')

    # Если такой товар уже есть — прибавляем количество, если нет — создаем новый
    existing = Storage.query.filter_by(name=name).first()
    if existing:
        existing.count += count
    else:
        new_item = Storage(name=name, count=count, type_of_product=category)
        db.session.add(new_item)

    db.session.commit()
    return redirect(url_for('cook_storage'))


@app.route('/cook/delete_product/<int:item_id>')
def delete_product(item_id):
    if session.get('role') != 'cook': return redirect(url_for('login'))

    item = Storage.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('cook_storage'))


@app.route('/cook/orders')
def cook_orders():
    if session.get('role') != 'cook': return redirect(url_for('login'))
    # Повар видит все активные заказы (сначала новые)
    all_reqs = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/orders_manage.html', requests=all_reqs)


@app.route('/cook/update_status/<int:req_id>/<string:new_status>')
def update_status(req_id, new_status):
    if session.get('role') != 'cook': return redirect(url_for('login'))

    order = Requests.query.get(req_id)
    if order:
        order.status = new_status
        db.session.commit()
    return redirect(url_for('cook_orders'))


@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_id' not in session: return redirect(url_for('login'))
    text = request.form.get('review_text')
    if text:
        user = User.query.get(session['user_id'])
        db.session.add(Review(author=user.login, text=text))
        db.session.commit()
    return redirect(url_for('index'))


# Остальные маршруты (login, register, logout) остаются без изменений
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
        login = request.form.get('login') or request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        if User.query.filter_by(login=login).first(): return "Логин занят"
        new_user = User(login=login, password=generate_password_hash(password), role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

