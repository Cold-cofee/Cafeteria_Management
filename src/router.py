import os
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from src.config import db
from src.student import StudentService
from src.service import CafeteriaService
from src.schemas import StudentSchema
from src.database.history import History
from src.database.store import Storage
from src.database.requests import Requests

# Настройка путей к шаблонам
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
template_dir = os.path.join(root_dir, 'frontend', 'templates')

wallet_bp = Blueprint('wallet_bp', __name__, template_folder=template_dir)


# --- 1. ЛИЧНЫЙ КАБИНЕТ И КОШЕЛЕК ---
@wallet_bp.route("/wallet", methods=["GET", "POST"])
@login_required
def wallet_page():
    user = current_user
    message = None
    message_type = None

    if request.method == "POST":
        action = request.form.get("action")
        amount_str = request.form.get("amount")
        amount, errors = StudentSchema.validate_payment(amount_str)

        if not errors:
            if action == "deposit":
                success, msg = StudentService.top_up_balance(user, amount)
            elif action == "withdraw":
                success, msg = StudentService.withdraw_balance(user, amount)
            message = msg
            message_type = "success" if success else "error"
        else:
            message = errors[0]
            message_type = "error"

    balance, card_last_4 = StudentService.get_wallet_info(user)
    # История транзакций
    history_records = History.query.filter_by(user=user.id).order_by(History.date.desc()).all()
    # Список всех заказов пользователя для оплаты
    user_requests = Requests.query.filter_by(user=user.id).order_by(Requests.date.desc()).all()

    return render_template("student/history.html",
                           balance=balance, card_number=card_last_4,
                           message=message, message_type=message_type,
                           history=history_records,
                           user_requests=user_requests)


# --- 2. МЕНЮ И СОЗДАНИЕ ЗАКАЗА (ОЖИДАНИЕ) ---
@wallet_bp.route('/menu', methods=['GET'])
@login_required
def menu_page():
    items = Storage.query.filter(Storage.count > 0).all()
    return render_template('student/menu.html', items=items)


@wallet_bp.route('/buy/<int:item_id>', methods=['POST'])
@login_required
def buy_product(item_id):
    item = Storage.query.get_or_404(item_id)

    # Создаем заявку со статусом 'waiting'
    new_request = Requests(
        user=current_user.id,
        product=item.name,
        amount=1,
        price=item.price,
        status='waiting',
        date=datetime.now()
    )
    db.session.add(new_request)
    db.session.commit()
    return redirect(url_for('wallet_bp.menu_page'))


# --- 3. ОПЛАТА ОДОБРЕННОГО ЗАКАЗА ---
@wallet_bp.route('/pay_request/<int:req_id>', methods=['POST'])
@login_required
def pay_request(req_id):
    req = Requests.query.get_or_404(req_id)
    balance, _ = StudentService.get_wallet_info(current_user)

    if req.status == 'approved':
        if balance >= req.price:
            # Списываем деньги
            StudentService.withdraw_balance(current_user, req.price)
            # Меняем статус и списываем товар
            req.status = 'paid'
            item = Storage.query.filter_by(name=req.product).first()
            if item:
                item.count -= req.amount
            db.session.commit()
            return redirect(url_for('wallet_bp.ticket_page', item_name=req.product))
        else:
            flash("Недостаточно средств!")

    return redirect(url_for('wallet_bp.wallet_page'))


# --- 4. ПАНЕЛЬ АДМИНИСТРАТОРА (ОДОБРЕНИЕ) ---
@wallet_bp.route('/admin/requests', methods=['GET'])
@login_required
def requests_page():
    if current_user.role != 'admin':
        return "Доступ запрещен", 403

    all_requests = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('admin/requests.html', requests=all_requests)


@wallet_bp.route('/requests/approve', methods=['POST'])
@login_required
def approve_request():
    if current_user.role != 'admin':
        return "Доступ запрещен", 403

    req_id = request.form.get('req_id')
    price_val = request.form.get('price')

    req = Requests.query.get(req_id)
    if req:
        req.status = 'approved'
        if price_val:
            req.price = int(price_val)
        db.session.commit()
    return redirect(url_for('wallet_bp.requests_page'))


@wallet_bp.route('/requests/delete/<int:req_id>')
@login_required
def delete_request(req_id):
    if current_user.role != 'admin':
        return "Доступ запрещен", 403
    CafeteriaService.reject_request(req_id)
    return redirect(url_for('wallet_bp.requests_page'))


# --- 5. ПРОЧЕЕ ---
@wallet_bp.route('/ticket/<item_name>')
@login_required
def ticket_page(item_name):
    now = datetime.now().strftime("%H:%M %d.%m")
    return render_template('student/ticket.html', item_name=item_name, date=now)


@wallet_bp.route('/cook/procurement', methods=['GET', 'POST'])
@login_required
def procurement_page():
    if current_user.role not in ['cook', 'admin']:
        return "Доступ запрещен", 403

    if request.method == 'POST':
        product_name = request.form.get('product')
        amount = request.form.get('amount')
        if product_name and amount:
            CafeteriaService.create_procurement_request(current_user.id, product_name, amount)
        return redirect(url_for('wallet_bp.procurement_page'))

    all_requests = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/procurement.html', requests=all_requests)