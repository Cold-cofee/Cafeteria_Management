from flask import Flask, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash

# Инициализация приложения.
# Везде, где было просто name, теперь __name__ (по два подчеркивания!)
app = Flask(__name__,template_folder='../frontend/templates')
app.config['SECRET_KEY'] = 'dev-secret-key'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Получаем данные из твоей анкеты
        login = request.form.get('login')
        password = request.form.get('password')
        role = request.form.get('role')
        allergies = request.form.get('allergies')

        # Шифруем пароль (безопасность по ТЗ)
        hashed_pw = generate_password_hash(password)

        # Печатаем в консоль PyCharm, чтобы ты видел результат
        print(f"\n--- НОВЫЙ ПОЛЬЗОВАТЕЛЬ ---")
        print(f"Логин: {login}\nРоль: {role}\nХеш: {hashed_pw}\nАллергии: {allergies}")

        return "<h1>Регистрация успешна! Данные в консоли.</h1><a href='/register'>Назад</a>"

    # Путь к HTML-файлу внутри папки templates
    return render_template('common/register.html')


# Самая важная строчка для запуска
if __name__ == '__main__':
    app.run(debug=True)
