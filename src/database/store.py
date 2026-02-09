from src.config import db
# Здесь мы инициализируем и проверяем таблицу store
class Storage(db.Model):

    __tablename__ = 'storage'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    count = db.Column(db.Integer, default=0, nullable=False)
    type_of_product = db.Column(db.String(25), nullable=False) 
    price = db.Column(db.Integer, nullable=False, default=0)

    def __init__(self, name, count, type_of_product, price):
        self.name = name
        self.count = count
        self.type_of_product = type_of_product
        self.price = price

    def __repr__(self):
        return f'<Item {self.name} - {self.count} шт, {self.price} руб>'
