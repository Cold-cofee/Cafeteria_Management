from src.config import db
from src.database.users import User

class Wallet(db.Model):
    wallet_number = db.Column(db.String(255), db.ForeignKey('user.wallet'), unique=True, nullable=False, primary_key=True)
    money = db.Column(db.Integer, nullable=False, default=0)
    
    def __init__(self, wallet_number, money=0):
        self.money = money if money is not None else 0
        self.wallet_number = wallet_number