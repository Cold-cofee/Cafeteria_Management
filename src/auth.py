import os
from flask import render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet

# Импорт конфигурации и моделей
from src.config import app, db
from src.database.users import User
from src.database.store import Storage
from src.database.requests import Requests

# Настройка путей шаблонов
base_dir = os.path.dirname(os.path.abspath(__file__))
app.template_folder = os.path.join(base_dir, '../frontend/templates')

# Гарантия ключа шифрования
if not os.getenv("KEY"):
    os.environ["KEY"] = Fernet.generate_key().decode()

with app.app_context():
    db.create_all()


# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОИСКА ПОЛЯ ---
def get_user_field(obj):
    """Находит, как в модели Requests называется связь с юзером"""
    for field in ['user_id', 'id_user', 'student_id', 'owner_id']:
        if hasattr(obj, field):
            return field
    return None


# --- МАРШРУТЫ ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))

    if user.role == 'cook':
        return redirect(url_for('view_requests'))

    # Получаем заявки текущего студента
    all_reqs = Requests.query.all()
    user_field = get_user_field(Requests)

    my_requests = []
    if user_field:
        my_requests = [r for r in all_reqs if getattr(r, user_field) == user.id]

    return render_template('common/index.html',
                           user=user,
                           wallet_number=user.get_wallet(),
                           my_requests=my_requests)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        l_val = request.form.get('username') or request.form.get('login')
        p_val = request.form.get('password')
        r_val = request.form.get('role', 'student')

        if User.query.filter_by(login=l_val).first():
            return "Ошибка: Логин уже занят!"

        new_user = User(login=l_val, password=generate_password_hash(p_val), role=r_val)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('common/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        l_val = request.form.get('username') or request.form.get('login')
        p_val = request.form.get('password')
        user = User.query.filter_by(login=l_val).first()
        if user and check_password_hash(user.password, p_val):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('index'))
        return "Неверный логин или пароль"
    return render_template('common/login.html')


@app.route('/create_request', methods=['POST'])
def create_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item_name = request.form.get('item_name', 'Обед')
    try:
        new_req = Requests()
        # Заполняем поля динамически, чтобы не было AttributeError
        setattr(new_req, 'item', item_name)
        setattr(new_req, 'status', 'pending')

        user_field = get_user_field(Requests)
        if user_field:
            setattr(new_req, user_field, session['user_id'])

        db.session.add(new_req)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return f"Ошибка базы: {e}"

    return redirect(url_for('index'))


@app.route('/cook/requests')
def view_requests():
    if session.get('role') != 'cook':
        return "Нет доступа", 403

    all_reqs = Requests.query.order_by(Requests.id.desc()).all()
    return render_template('cook/manage_requests.html', requests=all_reqs)


@app.route('/update_request/<int:req_id>/<string:new_status>')
def update_request_status(req_id, new_status):
    if session.get('role') != 'cook':
        return "Нет прав", 403

    req = Requests.query.get(req_id)
    if req:
        if new_status == 'approved':
            # Логика склада
            product = Storage.query.filter_by(name=req.item).first()
            if product and product.count > 0:
                product.count -= 1
                req.status = 'approved'
            else:
                return "Товара нет на складе!"
        else:
            req.status = 'rejected'
        db.session.commit()
    return redirect(url_for('view_requests'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, port=5000)

