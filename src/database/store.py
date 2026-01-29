from src.config import db
# Здесь мы инициализируем и проверяем таблицу store
class Storage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    count = db.Column(db.Integer, nullable=False)
    type_of_product = db.Column(db.String(25), nullable=False) 

    def __init__(self, name, count, type_of_product):
        self.name = name
        self.count = count
        self.type_of_product = type_of_product

    def __repr__(self):
        return f'<Storage {self.id}>'
