import os
import requests
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import re
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# with app.app_context():
#     inspector = db.inspect(db.engine)
#     if 'content' not in [col['name'] for col in inspector.get_columns('lesson')]:
#         with db.engine.connect() as conn:
#             conn.execute(db.text('ALTER TABLE lesson ADD COLUMN content TEXT'))
#             conn.commit()
#     db.create_all()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    courses = db.relationship('Course', backref='user', lazy=True)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    lessons = db.relationship('Lesson', backref='course', lazy=True)


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))


class API:
    @staticmethod
    def generate_course(topic):
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "LearnifyAI",
            "Content-Type": "application/json"
        }

        prompt = f"""
        Сгенерируй ПОЛНЫЙ учебный курс по теме "{topic}" в формате JSON. Весь текст внутри JSON должен быть ПОЛНОСТЬЮ написан: подробный, законченный, готовый к использованию без доработок. Не сокращай.

        ‼Важно:
        - Раздел "Теория" должен быть написан как **глава из учебника** — минимум 4 абзаца, академическим языком, с чёткими определениями, терминами и объяснениями.
        - Раздел "Практика" должен включать **примеры, задачи, кейсы с объяснениями**.
        - Не пиши "в этом уроке вы узнаете", а сразу переходи к сути.
        - Ответ — **только JSON**, без текста вне фигурных скобок.

        Пример структуры и одновременно шаблон:

        {{
          "title": "Установка и настройка среды разработки",
          "description": "Курс посвящён подготовке среды для разработки на Python с использованием Flask.",
          "lessons": [
            {{
              "number": 1,
              "title": "Подготовка среды разработки",
              "description": "Изучим установку Python, настройку виртуального окружения и установку Flask.",
              "sections": [
                {{
                  "title": "Теория",
                  "content": "Установка и настройка среды разработки — это основа любого проекта. Без правильно настроенной среды невозможно эффективно писать и тестировать код. Первый шаг — установка интерпретатора Python. На официальном сайте python.org доступна последняя версия для Windows, macOS и Linux. После установки необходимо убедиться, что Python добавлен в системную переменную PATH, чтобы его можно было вызывать из терминала или командной строки.\n\nСледующим этапом является создание виртуального окружения. Это позволяет изолировать зависимости проекта и избежать конфликтов. Команда `python -m venv env` создаёт директорию с виртуальным окружением. Для активации используется `source env/bin/activate` (на Unix-подобных системах) или `env\\Scripts\\activate` (на Windows). После активации можно устанавливать библиотеки, например, Flask.\n\nFlask — это микрофреймворк на Python для создания веб-приложений. Он лёгкий, гибкий и отлично подходит для небольших проектов и учебных целей. Установить его можно с помощью команды `pip install flask`. Также важно настроить редактор кода. Один из лучших вариантов — Visual Studio Code, так как он поддерживает Python, форматирование, автодополнение и встроенный терминал.\n\nХорошо настроенная среда разработки позволяет писать код быстрее, избегать ошибок и поддерживать проект в чистоте. Она играет ту же роль, что и хорошо укомплектованная мастерская для инженера или повара: всё должно быть на месте, чтобы сосредоточиться на главном — создании продукта."
                }},
                {{
                  "title": "Практика",
                  "content": "1. Скачайте Python с официального сайта.\n2. Установите и активируйте виртуальное окружение.\n3. Установите Flask с помощью pip.\n4. Настройте VS Code и запустите 'Hello, World' на Flask."
                }}
              ],
              "questions": [
                "Зачем нужно виртуальное окружение?",
                "Какая команда используется для установки Flask?",
                "Как активировать виртуальное окружение в Windows?"
              ]
            }}
          ]
        }}
        """

        data = {
            "model": "qwen/qwen3-30b-a3b:free",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": 6000,
            "temperature": 0.7
        }

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=180
            )
            response.raise_for_status()

            output = response.json()["choices"][0]["message"]["content"]

            json_start = output.find('{')
            json_end = output.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("Не найден JSON в ответе")

            clean_json = output[json_start:json_end]

            clean_json = re.sub(r'[\x00-\x1f]', '', clean_json)
            course_data = json.loads(clean_json)

            if not all(key in course_data for key in ['title', 'description', 'lessons']):
                raise ValueError("Неверная структура курса")

            return course_data

        except Exception as e:
            print(f"API Error: {str(e)}\nResponse: {response.text if 'response' in locals() else ''}")
            raise ValueError("Ошибка при генерации курса. Попробуйте другую тему.")


def last_news():
    telegram_u = 'https://t.me/s/AI_learns'
    r = requests.get(telegram_u)
    soup = BeautifulSoup(r.text, "lxml")
    link = soup.find_all('a')
    url = link[-1]['href']
    url = url.replace('https://t.me/', "")
    chanal, news_id = url.split("/")
    urls = []
    for i in range(3):
        urls.append(f"{chanal}/{int(news_id) - i}")
    return urls

@app.route('/')
def home():
    urls = last_news()
    return render_template('index.html', urls=urls)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        session['logged_in'] = True
        session['user_id'] = user.id
        session['username'] = user.username
        return redirect(url_for('profile'))
    return render_template('register.html', show_header=False)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['logged_in'] = True
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('profile'))
        return 'Неверные данные'
    return render_template('login.html', show_header=False)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/generate-course', methods=['POST'])
def generate_course():
    if not session.get('logged_in'):
        flash('Для создания курса необходимо авторизоваться', 'error')
        return redirect(url_for('login'))

    title = request.form.get('course-title')
    if not title:
        flash('Пожалуйста, укажите тему курса', 'error')
        return redirect(url_for('home'))

    try:
        user = User.query.filter_by(username=session['username']).first()
        course_data = API.generate_course(title)

        course = Course(
            title=course_data['title'],
            description=course_data['description'],
            user=user
        )
        db.session.add(course)
        db.session.flush()

        for lesson_data in course_data['lessons']:
            lesson_content = {
                'sections': lesson_data.get('sections', []),
                'questions': lesson_data.get('questions', [])
            }

            lesson = Lesson(
                number=lesson_data['number'],
                title=lesson_data['title'],
                description=lesson_data['description'],
                content=json.dumps(lesson_content, ensure_ascii=False),
                course_id=course.id
            )
            db.session.add(lesson)

        db.session.commit()
        flash('Курс успешно создан!', 'success')
        return redirect(url_for('course_detail', course_id=course.id))

    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'error')
    except Exception as e:
        db.session.rollback()
        flash('Произошла ошибка при создании курса', 'error')
        print(f"Ошибка: {str(e)}")

    return redirect(url_for('home'))


@app.route('/profile')
def profile():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user = User.query.filter_by(username=session['username']).first()
    return render_template('profile.html', user=user)


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    return render_template('course.html', course=course)


@app.route('/courses')
def courses():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    return render_template('courses.html', courses=user.courses)


@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    next_lesson = Lesson.query.filter_by(course_id=lesson.course_id, number=lesson.number + 1).first()
    return render_template('lesson.html', lesson=lesson, course=lesson.course, next_lesson=next_lesson)


@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value) if value else {}
    except json.JSONDecodeError:
        return {}


def create_templates():
    templates = {
        'base.html': '''<!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{% block title %}AI Learning Platform{% endblock %}</title>
        <style>
            :root {
                --primary: #6366f1;
                --primary-dark: #4f46e5;
                --secondary: #06b6d4;
                --dark: #1e293b;
                --darker: #0f172a;
                --light: #f8fafc;
                --lighter: #ffffff;
                --gray: #e2e8f0;
                --gray-dark: #94a3b8;
                --success: #10b981;
                --error: #ef4444;
                --warning: #f59e0b;
                --radius: 0.5rem;
                --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            }

            body {
                background-color: var(--light);
                color: var(--dark);
                line-height: 1.6;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
            }

            a {
                text-decoration: none;
                color: inherit;
            }

            .container {
                width: 100%;
                max-width: 1200px;
                margin: 0 auto;
                padding: 0 1rem;
            }

            header {
                background: linear-gradient(135deg, var(--primary), var(--primary-dark));
                color: var(--lighter);
                padding: 1rem 0;
                box-shadow: var(--shadow);
                position: sticky;
                top: 0;
                z-index: 50;
            }

            nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 1rem;
            }

            .logo {
                font-size: 1.5rem;
                font-weight: 700;
                color: var(--lighter);
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .nav-links {
                display: flex;
                gap: 0.5rem;
            }

            .nav-links a {
                padding: 0.5rem 1rem;
                border-radius: var(--radius);
                transition: var(--transition);
                font-weight: 500;
            }

            .nav-links a:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }

            main {
                flex: 1;
                padding: 2rem 0;
            }

            footer {
                background-color: var(--darker);
                color: var(--lighter);
                text-align: center;
                padding: 1.5rem;
                margin-top: auto;
            }

            .btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background-color: var(--primary);
                color: var(--lighter);
                padding: 0.75rem 1.5rem;
                border: none;
                border-radius: var(--radius);
                cursor: pointer;
                font-weight: 500;
                transition: var(--transition);
                box-shadow: var(--shadow);
                gap: 0.5rem;
            }

            .btn:hover {
                background-color: var(--primary-dark);
                transform: translateY(-2px);
                box-shadow: var(--shadow-lg);
            }

            .btn-secondary {
                background-color: var(--gray);
                color: var(--dark);
            }

            .btn-secondary:hover {
                background-color: var(--gray-dark);
            }


            .form-group {
                margin-bottom: 1.5rem;
            }

            .form-control {
                width: 100%;
                padding: 0.75rem 1rem;
                border: 1px solid var(--gray);
                border-radius: var(--radius);
                font-size: 1rem;
                transition: var(--transition);
            }

            .form-control:focus {
                outline: none;
                border-color: var(--primary);
                box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
            }

            label {
                display: block;
                margin-bottom: 0.5rem;
                font-weight: 500;
            }


            .card {
                background-color: var(--lighter);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                overflow: hidden;
                transition: var(--transition);
            }

            .card:hover {
                transform: translateY(-5px);
                box-shadow: var(--shadow-lg);
            }

            .card-header {
                padding: 1.5rem;
                border-bottom: 1px solid var(--gray);
            }

            .card-body {
                padding: 1.5rem;
            }

            .hero {
                text-align: center;
                padding: 4rem 2rem;
                background: linear-gradient(135deg, var(--primary), var(--primary-dark));
                color: var(--lighter);
                border-radius: var(--radius);
                margin-bottom: 3rem;
            }

            .hero h1 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                line-height: 1.2;
            }

            .hero p {
                font-size: 1.25rem;
                max-width: 800px;
                margin: 0 auto 2rem;
            }


            .course-generator {
                max-width: 600px;
                margin: 0 auto;
                background-color: var(--lighter);
                padding: 2rem;
                border-radius: var(--radius);
                box-shadow: var(--shadow);
            }

            .course-content, .lesson-content {
                background-color: var(--lighter);
                border-radius: var(--radius);
                padding: 2rem;
                box-shadow: var(--shadow);
                line-height: 1.8;
            }

            .lesson-navigation {
                display: flex;
                justify-content: space-between;
                margin-top: 2rem;
                gap: 1rem;
            }

            .auth-form {
                max-width: 400px;
                margin: 0 auto;
                padding: 2rem;
                background-color: var(--lighter);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
            }

            .course-card {
                background-color: var(--lighter);
                padding: 1.5rem;
                border-radius: var(--radius);
                margin-bottom: 2rem;
                box-shadow: var(--shadow);
                transition: var(--transition);
            }

            .course-card:hover {
                transform: translateY(-5px);
                box-shadow: var(--shadow-lg);
            }

            .course-card h2 {
                font-size: 1.5rem;
                margin-bottom: 0.5rem;
                color: var(--darker);
            }

            .course-card p {
                color: var(--gray-dark);
                margin-bottom: 1.5rem;
            }

            .lessons-list {
                margin-top: 2rem;
            }

            .lesson-item {
                margin-bottom: 1.5rem;
                padding: 1.5rem;
                background-color: var(--lighter);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
            }


            .questions {
                margin-top: 2rem;
                padding: 1.5rem;
                background-color: rgba(6, 182, 212, 0.05);
                border-radius: var(--radius);
                border-left: 4px solid var(--secondary);
            }

            .flash {
                padding: 1rem;
                margin-bottom: 1rem;
                border-radius: var(--radius);
                font-weight: 500;
            }

            .flash.success {
                background-color: rgba(16, 185, 129, 0.1);
                color: var(--success);
                border-left: 4px solid var(--success);
            }

            .flash.error {
                background-color: rgba(239, 68, 68, 0.1);
                color: var(--error);
                border-left: 4px solid var(--error);
            }

            @media (max-width: 768px) {
                nav {
                    flex-direction: column;
                }

                .nav-links {
                    width: 100%;
                    justify-content: space-around;
                }

                .hero h1 {
                    font-size: 2rem;
                }

                .hero p {
                    font-size: 1rem;
                }

                .course-content, .lesson-content, .auth-form {
                    padding: 1.5rem;
                }
            }

            @media (max-width: 480px) {
                .hero {
                    padding: 2rem 1rem;
                }

                .btn {
                    width: 100%;
                }

                .lesson-navigation {
                    flex-direction: column;
                }
            }
        </style>

    </head>
    <body>
        {% if show_header|default(True) %}
        <header>
            <div class="container">     
                <nav>
                    <a href="/" class="logo">Learnify AI</a>
                    <div class="nav-links">
                        <a href="/">Главная</a>
                        <a href="/courses">Курсы</a>
                        <a href="/profile">Профиль</a>
                        {% if not session.logged_in %}
                            <a href="/register">Регистрация</a>
                            <a href="/login">Войти</a>
                        {% else %}
                            <a href="/logout">Выйти</a>
                        {% endif %}
                    </div>
                </nav>
            </div>
        </header>
        {% endif %}

        <main class="container">
            {% block content %}{% endblock %}
        </main>

        <footer>
            <div class="container">
                <p>© 2025 LearnifyAI Все права защищены</p>
            </div>
        </footer>
    </body>
    </html>
    ''',

        'index.html': '''{% extends "base.html" %}
    {% block content %}
    <section class="hero">
        <h1>Создайте свой курс обучения</h1>
        <p>Введите тему, и наша платформа сгенерирует для вас персонализированный курс</p>
    </section>

    <div class="course-generator">
        <form action="/generate-course" method="POST">
            <div class="form-group">
                <input type="text" name="course-title" class="form-control" placeholder="Введите тему курса" required>
            </div>
            <button type="submit" class="btn">Сгенерировать курс</button>
        </form>
        <h1 align="center"> Новости</h1>
        {% for url in urls %}
            <script async src="https://telegram.org/js/telegram-widget.js?22" data-telegram-post={{ url }} data-width="100%"></script>
        {% endfor %}
        <a href="https://t.me/techn_sup000_bot">Техничекая поддержка</a>
    </div>
    {% endblock %}
    ''',

        'courses.html': '''{% extends "base.html" %}
    {% block content %}
    <div class="course-content">
        <h1>Мои курсы</h1>
        {% if courses %}
            {% for course in courses %}
            <div class="course-card">
                <h2>{{ course.title }}</h2>
                <p>{{ course.description }}</p>
                <a href="{{ url_for('course_detail', course_id=course.id) }}" class="btn">Перейти к курсу</a>
            </div>
            {% endfor %}
        {% else %}
            <p>У вас пока нет курсов. Создайте курс на главной странице.</p>
        {% endif %}
    </div>
    {% endblock %}

    ''',

        'course.html': '''{% extends "base.html" %}
    {% block title %}{{ course.title }}{% endblock %}
    {% block content %}
    <div class="course-content">
        <h1>{{ course.title }}</h1>
        <p>{{ course.description }}</p>

        <div class="lessons-list">
            <h2>Уроки курса</h2>
            {% for lesson in course.lessons %}
            <div class="lesson-item">
                <h3>{{ lesson.title }}</h3>
                <a href="/lesson/{{ lesson.id }}" class="btn">Начать урок</a>
            </div>
            {% endfor %}

        </div>
    </div>
    {% endblock %}
    ''',

        'lesson.html': '''{% extends "base.html" %}
{% block title %}{{ lesson.title }}{% endblock %}
{% block content %}
<div class="lesson-content">
    <h1>{{ lesson.title }}</h1>

    {# фильтр для преобразования JSON строки в объект #}
    {% set lesson_content = lesson.content|fromjson if lesson.content else {} %}

    {% if lesson_content.sections %}
        {% for section in lesson_content.sections %}
            <h2>{{ section.title }}</h2>
            <p>{{ section.content }}</p>
        {% endfor %}
    {% else %}
        <p>{{ lesson.description }}</p>
    {% endif %}

    {% if lesson_content.questions %}
        <div class="questions">
            <h3>Контрольные вопросы:</h3>
            <ol>
                {% for question in lesson_content.questions %}
                    <li>{{ question }}</li>
                {% endfor %}
            </ol>
        </div>
    {% endif %}

    <div class="lesson-navigation">
        <a href="{{ url_for('course_detail', course_id=lesson.course_id) }}" class="btn">Назад к курсу</a>
        {% if next_lesson %}
            <a href="{{ url_for('lesson', lesson_id=next_lesson.id) }}" class="btn">Следующий урок</a>
        {% endif %}
    </div>
</div>
{% endblock %}

    ''',

        'register.html': '''{% extends "base.html" %}
    {% block content %}
    <div class="auth-form">
        <h2>Регистрация</h2>
        <form method="POST">
            <div class="form-group">
                <input type="text" name="username" class="form-control" placeholder="Имя пользователя" required>
            </div>
            <div class="form-group">
                <input type="email" name="email" class="form-control" placeholder="Email" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" class="form-control" placeholder="Пароль" required>
            </div>
            <button type="submit" class="btn">Зарегистрироваться</button>
        </form>
    </div>
    {% endblock %}
    ''',

        'login.html': '''{% extends "base.html" %}
    {% block content %}
    <div class="auth-form">
        <h2>Вход</h2>
        <form method="POST">
            <div class="form-group">
                <input type="email" name="email" class="form-control" placeholder="Email" required>
            </div>
            <div class="form-group">
                <input type="password" name="password" class="form-control" placeholder="Пароль" required>
            </div>
            <button type="submit" class="btn">Войти</button>
        </form>
    </div>
    {% endblock %}
    ''',
        'profile.html': '''{% extends "base.html" %}
    {% block content %}
    <h2>Личный кабинет {{ user.username }}</h2>
    <h3>Мои курсы:</h3>
    <ul>
        {% for course in user.courses %}
        <li>
            <a href="{{ url_for('course_detail', course_id=course.id) }}">{{ course.title }}</a>
        </li>
        {% else %}
        <li>У вас пока нет курсов</li>
        {% endfor %}
    </ul>
    {% endblock %}

    '''
    }

    if not os.path.exists('templates'):
        os.makedirs('templates')

    for filename, content in templates.items():
        with open(f'templates/{filename}', 'w', encoding='utf-8') as f:
            f.write(content)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_templates()
    app.run(debug=True)

# OPENROUTER_API_KEY=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
