"""
Какие функции реализуются здесь:

    Принимает запросы: (создать заказ) или (получить список заказов для повара).
    Вызывает логику: Он не считает деньги и не проверяет продукты сам, он передает эту задачу в service.py.
    Возвращает ответ: Отдает данные обратно на фронтенд в формате, описанном в schemas.py.
"""
import os
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from src.student import StudentService
from src.schemas import StudentSchema
from src.database.users import User
from src.config import db
from src.database.history import History
from src.database.store import Storage
from src.database.requests import Requests
from datetime import datetime


current_dir = os.path.dirname(os.path.abspath(__file__)) # Папка src
root_dir = os.path.dirname(current_dir) # Корневая папка проекта
template_dir = os.path.join(root_dir, 'frontend', 'templates') # Путь к frontend/templates
# Создаем чертеж для путей, связанных с кошельком
wallet_bp = Blueprint('wallet_bp', __name__, template_folder=template_dir)
@wallet_bp.route("/wallet", methods=["GET", "POST"])
@login_required
def wallet_page():
    user = current_user
    
    message = None
    message_type = None
    """
    Страница кошелька.
    GET запрос: Просто показывает страницу с балансом.
    POST запрос: Обрабатывает нажатие кнопок Пополнить/Снять.
    """
    
    #  если пришли данные от пользователя
    if request.method == "POST":
        # Получаем данные из формы
        action = request.form.get("action")   # deposit или withdraw
        amount_str = request.form.get("amount") # Сумма строкой

        #1: валидация (Schema)
        # Узнаём корректность данных от пользователя
        amount, errors = StudentSchema.validate_payment(amount_str)

        if errors:
            # если ошибка
            message = errors[0] # Берем текст ошибки из схемы
            message_type = "error"
        else:
            # если всё ок
            if action == "deposit":
                success, msg = StudentService.top_up_balance(user, amount)
            elif action == "withdraw":
                success, msg = StudentService.withdraw_balance(user, amount)
            
            message = msg
            # Если операция прошла успешно — зеленый цвет, если нет денег — красный
            message_type = "success" if success else "error"

    # 2. Если просто зашли на страницу (GET)
    # Запрашиваем актуальные данные, чтобы показать пользователю
    balance, card_last_4 = StudentService.get_wallet_info(user)
    
    history_records = History.query.filter_by(user=user.id).order_by(History.date.desc()).all()#запрос истории 

    # Отдаем HTML и вставляем туда цифры
    return render_template("student/history.html",
                         balance=balance, 
                         card_number=card_last_4,
                         message=message,
                         message_type=message_type,
                         history=history_records)

# страница повара для создания заявок на закупку продуктов
@wallet_bp.route('/cook/procurement', methods=['GET', 'POST'])
@login_required
def procurement_page():
    if request.method == 'POST':
        product_name = request.form.get('product')
        amount = request.form.get('amount')
        
        # Цену тут не спрашиваем, её нет в БД заявок
        
        user_id = current_user.id 
        current_date = datetime.now()

        if product_name and amount:
            try:
                new_req = Requests(
                    user=user_id,
                    product=product_name,
                    amount=int(amount),
                    status="Ожидает",
                    date=current_date
                )
                db.session.add(new_req)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка: {e}")
                
        return redirect(url_for('wallet_bp.procurement_page'))
    
    all_requests = Requests.query.order_by(Requests.date.desc()).all()
    return render_template('cook/procurement.html', requests=all_requests)


# страница администратора для управления инвентарем
@wallet_bp.route('/admin/requests', methods=['GET'])
@login_required
def admin_page():
    pending_requests = Requests.query.filter_by(status="Ожидает").all()
    return render_template('admin/requests.html', requests=pending_requests)


@wallet_bp.route('/admin/requests', methods=['GET'])
@login_required
def requests_page():
    all_requests = Requests.query.all()
    return render_template('admin/requests.html', requests=all_requests)


@wallet_bp.route('/requests/approve', methods=['POST'])
@login_required
def approve_request():
    # Получаем данные 
    req_id = request.form.get('req_id')
    price_val = request.form.get('price_for_sell') # <--- ВОТ ТУТ МЫ ПОЛУЧАЕМ ЦЕНУ

    if req_id and price_val:
        req = Requests.query.get(req_id)
        if req:
            # Создаем товар в Storage (тут цена обязательна)
            new_item = Storage(
                name=req.product,
                count=req.amount,
                price=int(price_val), # Берем цену, которую ввел админ
                type_of_product="Еда"
            )
            
            try:
                db.session.add(new_item)
                req.status = "Одобрено"
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Ошибка одобрения: {e}")

    return redirect(url_for('wallet_bp.requests_page'))

@wallet_bp.route('/requests/delete/<int:req_id>')
@login_required
def delete_request(req_id):
    """
    Отклонение (удаление) заявки без добавления на склад.
    """
    req = Requests.query.get(req_id)
    if req:
        req.status = "Отклонено"
        db.session.commit()
    
    # Возвращаем на страницу заявок
    return redirect(url_for('wallet_bp.requests_page'))

#списание вручную (для админа)
@wallet_bp.route('/requests/delete/<int:item_id>')
@login_required
def delete_admin_item(item_id):
    item = Storage.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('wallet_bp.requests_page'))

# Страница меню (где студент видит товары)
@wallet_bp.route('/menu', methods=['GET'])
@login_required
def menu_page():
    # Показываем только те товары, которых не 0
    items = Storage.query.filter(Storage.count > 0).all()
    return render_template('student/menu.html', items=items)

@wallet_bp.route('/ticket/<item_name>')
@login_required
def ticket_page(item_name):
    # Показываем тикет с текущим временем
    now = datetime.now().strftime("%H:%M %d.%m")
    return render_template('student/ticket.html', item_name=item_name, date=now)


# Удаление со склада
@wallet_bp.route('/buy/<int:item_id>', methods=['POST'])
@login_required
def buy_product(item_id):
    # 1. Ищем товар на складе
    item = Storage.query.get(item_id)
    
    if not item:
        return "Товар не найден", 404

    # 2. Проверяем, есть ли он в наличии
    if item.count <= 0:
        return "Товар закончился", 400

    # 3. Пробуем списать деньги
    user = current_user
    success, msg = StudentService.buy_item(user, item.name, item.price)

    if success:
        # 4. Если деньги списались — уменьшаем количество на складе
        item.count -= 1
        db.session.commit()
        return redirect(url_for('wallet_bp.ticket_page', item_name=item.name))
    # Возвращаемся в меню с сообщением
    return redirect(url_for('wallet_bp.menu_page'))