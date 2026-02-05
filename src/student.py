"""
Какие функции реализуются здесь:

    Пополнение кошелька через yookassa
    Создание отзывов к каждому блюду
    Изменение профиля (аллергии, предпочтения, изменение пароля, изменение почты)
    Оплата абонемента
    Просмотр истории заказов и пополнения кошелька
    
"""
from src.config import db
from src.database.wallets import Wallet

class StudentService:
    @staticmethod
    def _get_or_create_wallet(user):
        """
        Внутренний метод. Гарантирует, что у пользователя есть запись в таблице wallets.
        Если записи нет — создает её с балансом 0.
        """
        # user.wallet — это зашифрованный ключ (из таблицы users)
        wallet_key = user.wallet
        
        # Ищем этот ключ в таблице кошельков
        wallet = Wallet.query.get(wallet_key)
        
        # Если кошелька нет в базе создаем
        if not wallet:
            print(f"Создаем новый кошелек для пользователя...")
            wallet = Wallet(wallet_number=wallet_key, money=0)
            db.session.add(wallet)
            db.session.commit()
            
        return wallet

    @staticmethod
    def top_up_balance(user, amount):
        """
        Пополнение баланса.
        """
        # Получаем кошелек 
        wallet = StudentService._get_or_create_wallet(user)
        
        # Меняем баланс
        wallet.money += amount
        db.session.commit() # Сохраняем в БД
        
        return True, f"Баланс успешно пополнен на {amount} ₽"

    @staticmethod
    def withdraw_balance(user, amount):
        """
        Снятие средств.
        """
        wallet = StudentService._get_or_create_wallet(user)

        # Проверяем, хватает ли денег
        if wallet.money >= amount:
            wallet.money -= amount
            db.session.commit() # Сохраняем в БД
            return True, f"Успешно снято {amount} ₽"
        else:
            return False, "Недостаточно средств на счете"

    @staticmethod
    def get_wallet_info(user):
        """
        Получение данных для отображения на странице.
        """
        wallet = StudentService._get_or_create_wallet(user)
        
        # Расшифровываем номер карты, чтобы показать последние 4 цифры
        full_card_number = user.get_wallet()
        last_4_digits = full_card_number[-4:] if full_card_number else "****"
        
        return wallet.money, last_4_digits