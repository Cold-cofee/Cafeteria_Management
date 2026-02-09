"""
Какие функции реализуются здесь: (самое сложное)
    Проверка условий: Хватает ли у студента денег на балансе? Есть ли продукты на складе для этого блюда?
    Транзакции: Списать деньги с кошелька, создать запись о заказе, уменьшить количество продуктов на складе.
"""
from datetime import datetime
from src.config import db
from src.database.history import History
from src.database.requests import Requests
from src.database.store import Storage
from src.student import StudentService # Импортируем, чтобы работать с кошельком

class CafeteriaService:
    """
    Здесь живет логика торговли и склада:
    - Покупка товара (Транзакция)
    - Заявки повара
    - Одобрение админа
    """

    @staticmethod
    def buy_product_transaction(user, item_id):
        """
        СЛОЖНАЯ ТРАНЗАКЦИЯ ПОКУПКИ:
        1. Проверяем наличие товара.
        2. Проверяем баланс (через StudentService).
        3. Списываем деньги и товар ОДНОВРЕМЕННО.
        """
        # 1. Ищем товар
        item = Storage.query.get(item_id)
        if not item:
            return False, "Товар не найден", None

        # 2. Проверяем склад
        if item.count <= 0:
            return False, "Товар закончился", None

        # 3. Работаем с кошельком через StudentService (чтобы не дублировать код)
        # Нам нужно получить объект кошелька, чтобы изменить баланс внутри этой сессии
        wallet = StudentService._get_or_create_wallet(user)

        if wallet.money < item.price:
            return False, "Недостаточно средств", None

        try:
            #начало транзакции
            wallet.money -= item.price   # Списали деньги
            item.count -= 1              # Списали товар
            
            # Записали в историю
            record = History(
                user=user.id, 
                type_of_transaction=f"Покупка: {item.name}", 
                amount=item.price, 
                date=datetime.now()
            )
            db.session.add(record)
            
            db.session.commit() # фиксируем
            # конец транзакции 
            
            return True, "Успешно", item.name
            
        except Exception as e:
            db.session.rollback()
            print(f"Transaction Error: {e}")
            return False, "Ошибка при обработке покупки", None

    # повар
    @staticmethod
    def create_procurement_request(user_id, product_name, amount):
        try:
            new_req = Requests(
                user=user_id,
                product=product_name,
                amount=int(amount),
                status="Ожидает",
                date=datetime.now()
            )
            db.session.add(new_req)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    # админ
    @staticmethod
    def approve_request(req_id, price_val):
        req = Requests.query.get(req_id)
        if req:
            try:
                new_item = Storage(
                    name=req.product,
                    count=req.amount,
                    price=int(price_val),
                    type_of_product="Еда"
                )
                db.session.add(new_item)
                req.status = "Одобрено"
                db.session.commit()
                return True
            except Exception as e:
                db.session.rollback()
        return False

    @staticmethod
    def reject_request(req_id):
        req = Requests.query.get(req_id)
        if req:
            req.status = "Отклонено"
            db.session.commit()

    @staticmethod
    def delete_item(item_id):
        item = Storage.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()

            