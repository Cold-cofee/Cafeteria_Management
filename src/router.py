import os
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from src.student import StudentService
from src.service import CafeteriaService  
from src.schemas import StudentSchema
from src.database.history import History
from src.database.store import Storage
from src.database.requests import Requests

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
template_dir = os.path.join(root_dir, 'frontend', 'templates')

wallet_bp = Blueprint('wallet_bp', __name__, template_folder=template_dir)

# кошелёк (Работает через StudentService)
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

        if errors:
            message = errors[0]; message_type = "error"
        else:
            if action == "deposit":
                success, msg = StudentService.top_up_balance(user, amount)
            elif action == "withdraw":
                success, msg = StudentService.withdraw_balance(user, amount)
            
            message = msg
            message_type = "success" if success else "error"

    balance, card_last_4 = StudentService.get_wallet_info(user)
    history_records = History.query.filter_by(user=user.id).order_by(History.date.desc()).all()

    return render_template("student/history.html",
                           balance=balance, card_number=card_last_4,
                           message=message, message_type=message_type,
                           history=history_records)


#повар (Работает через CafeteriaService)
@wallet_bp.route('/cook/procurement', methods=['GET', 'POST'])
@login_required
def procurement_page():
    if request.method == 'POST':
        product_name = request.form.get('product')
        amount = request.form.get('amount')
        
        if product_name and amount:
            CafeteriaService.create_procurement_request(current_user.id, product_name, amount)
                
        return redirect(url_for('wallet_bp.procurement_page'))
    
    all_requests = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/procurement.html', requests=all_requests)


# админ (Работает через CafeteriaService) 
@wallet_bp.route('/admin/requests', methods=['GET'])
@login_required
def requests_page():
    all_requests = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('admin/requests.html', requests=all_requests)

@wallet_bp.route('/requests/approve', methods=['POST'])
@login_required
def approve_request():
    req_id = request.form.get('req_id')
    price_val = request.form.get('price_for_sell')

    if req_id and price_val:
        CafeteriaService.approve_request(req_id, price_val)

    return redirect(url_for('wallet_bp.requests_page'))

@wallet_bp.route('/requests/delete/<int:req_id>')
@login_required
def delete_request(req_id):
    CafeteriaService.reject_request(req_id)
    return redirect(url_for('wallet_bp.requests_page'))

@wallet_bp.route('/storage/delete/<int:item_id>')
@login_required
def delete_admin_item(item_id):
    CafeteriaService.delete_item(item_id)
    return redirect(url_for('wallet_bp.requests_page'))


# покупка
@wallet_bp.route('/menu', methods=['GET'])
@login_required
def menu_page():
    items = Storage.query.filter(Storage.count > 0).all()
    return render_template('student/menu.html', items=items)

@wallet_bp.route('/buy/<int:item_id>', methods=['POST'])
@login_required
def buy_product(item_id):
    # Вызываем сложную транзакцию из сервиса
    success, msg, item_name = CafeteriaService.buy_product_transaction(current_user, item_id)

    if success:
        return redirect(url_for('wallet_bp.ticket_page', item_name=item_name))
    
    # Если ошибка - просто обновляем страницу меню (можно добавить вывод ошибки)
    return redirect(url_for('wallet_bp.menu_page'))

@wallet_bp.route('/ticket/<item_name>')
@login_required
def ticket_page(item_name):
    now = datetime.now().strftime("%H:%M %d.%m")
    return render_template('student/ticket.html', item_name=item_name, date=now)