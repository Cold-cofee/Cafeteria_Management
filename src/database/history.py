from src.config import db
from src.database.users import User
# Здесь мы инициализируем и проверяем таблицу history
class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type_of_transaction = db.Column(db.String(25), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
   
    def __init__(self, user, type_of_transaction, amount, date):
        self.user = user
        self.type_of_transaction = type_of_transaction
        self.amount = amount
        self.date = date

    def __repr__(self):
        return f'<History {self.id}>'
