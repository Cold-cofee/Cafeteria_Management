"""
Какие функции реализуются здесь:

    Принимает запросы: (создать заказ) или (получить список заказов для повара).
    Вызывает логику: Он не считает деньги и не проверяет продукты сам, он передает эту задачу в service.py.
    Возвращает ответ: Отдает данные обратно на фронтенд в формате, описанном в schemas.py.
"""
from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from src.student import StudentService
from src.schemas import StudentSchema
from src.database.users import User
from src.config import db



# Создаем чертеж для путей, связанных с кошельком
wallet_bp = Blueprint('wallet_bp', __name__)

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
    
    # --- 1. ЕСЛИ ПРИШЛИ ДАННЫЕ ОТ ПОЛЬЗОВАТЕЛЯ (POST) ---
    if request.method == "POST":
        # Получаем данные из формы
        action = request.form.get("action")   # deposit или withdraw
        amount_str = request.form.get("amount") # Сумма строкой

        #1: ВАЛИДАЦИЯ (Schema)
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
    
    # Отдаем HTML и вставляем туда цифры
    return render_template("wallet.html",
                         balance=balance, 
                         card_number=card_last_4,
                         message=message,
                         message_type=message_type)