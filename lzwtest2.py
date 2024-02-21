# lzwtest2.py
from flask import Flask, render_template, request, redirect, url_for, jsonify, make_response, session
import pymysql
import jwt
import time
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] - %(message)s')


app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'your_secret_key'

# 设置最大尝试次数
max_attempts = 5
attempts = 0

# 等待MySQL服务准备好
while attempts < max_attempts:
    try:
        # 尝试连接MySQL
        connection = pymysql.connect(
            host="mysql",
            user="test",
            password="123456",
            database="diary_db",
            charset='utf8mb4',
            port=3306,
            cursorclass=pymysql.cursors.DictCursor,
        )
        # 如果连接成功，退出循环
        break
    except pymysql.Error as err:
        # 如果连接失败，等待一段时间后重试
        attempts += 1
        print(f"Failed to connect to MySQL (Attempt {attempts}/{max_attempts})")
        time.sleep(1)

# 检查是否成功连接，否则抛出错误
if attempts == max_attempts:
    raise ConnectionError("Failed to connect to MySQL after maximum attempts")

## MySQL 连接配置
#connection = pymysql.connect(
#    host='mysql',
#    user='test',
#    password='123456',
#    charset='utf8mb4',
#    cursorclass=pymysql.cursors.DictCursor
#)


# 检查并创建数据库
def create_database():
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS diary_db")
    connection.commit()

# 创建 user 表
def create_user_table():
    with connection.cursor() as cursor:
        cursor.execute("""CREATE TABLE IF NOT EXISTS diary_db.user (
                          id INT NOT NULL AUTO_INCREMENT,
                          username VARCHAR(255) NOT NULL,
                          password VARCHAR(255) NOT NULL,
                          registration_time TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                          PRIMARY KEY (id),
                          UNIQUE KEY (username)
                      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    connection.commit()

# 创建 diary 表
def create_diary_table():
    with connection.cursor() as cursor:
        cursor.execute("""CREATE TABLE IF NOT EXISTS diary_db.diary (
                          id INT NOT NULL AUTO_INCREMENT,
                          user_id INT NOT NULL,
                          title VARCHAR(255) NOT NULL,
                          content TEXT,
                          created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
                          PRIMARY KEY (id),
                          FOREIGN KEY (user_id) REFERENCES user(id)
                      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""")
    connection.commit()

# 添加日记
def add_diary(title, content, user_id):
    with connection.cursor() as cursor:
        sql = "INSERT INTO diary (title, content, user_id) VALUES (%s, %s, %s)"
        cursor.execute(sql, (title, content, user_id))
        connection.commit()

# 注册用户
def register_user(username, password):
    with connection.cursor() as cursor:
        try:
            sql = "INSERT INTO user (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, password))
            connection.commit()
            return None
        except pymysql.IntegrityError:
            return "Username already exists"

# 编辑日记
def edit_diary(diary_id, title, content):
    with connection.cursor() as cursor:
        sql = "UPDATE diary SET title=%s, content=%s WHERE id=%s"
        cursor.execute(sql, (title, content, diary_id))
        connection.commit()

# 删除日记
def delete_diary(diary_id):
    with connection.cursor() as cursor:
        sql = "DELETE FROM diary WHERE id=%s"
        cursor.execute(sql, (diary_id,))
        connection.commit()

# 获取当前登录用户的所有日记
def get_user_diaries(user_id):
    with connection.cursor() as cursor:
        sql = "SELECT * FROM diary WHERE user_id=%s"
        cursor.execute(sql, (user_id,))
        return cursor.fetchall()


# 用户登录
def login_user(username, password):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM user WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        logging.info(f'user is {user}')
        if user:
            return user
        else:
            return None

# 生成JWT Token
def generate_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1)  # Token有效期1天
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token

# 验证JWT Token
def verify_token(token):
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None  # Token已过期
    except jwt.InvalidTokenError:
        return None  # Token无效

# 登录验证装饰器
def login_required(route_function):
    def wrapper(*args, **kwargs):
        token = session.get('token')
        if not token:
            return redirect(url_for('login'))
        user_id = verify_token(token)
        if not user_id:
            return redirect(url_for('login'))
        return route_function(*args, **kwargs)  # 返回被装饰的函数
    wrapper.__name__ = route_function.__name__
    return wrapper



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = login_user(username, password)
        if user:
            token = generate_token(user['id'])
            session['token'] = token
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Invalid username or password")

@app.route('/index')
@login_required
def index():
    user_id = verify_token(session.get('token'))
    diaries = get_user_diaries(user_id)
    return render_template('index.html', diaries=diaries)


@app.route('/add', methods=['POST'])
@login_required
def add():
    title = request.form['title']
    content = request.form['content']
    user_id = verify_token(session.get('token'))
    add_diary(title, content, user_id)
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    elif request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = register_user(username, password)
        if error:
            return render_template('register.html', error=error)
        else:
            return redirect(url_for('index'))

@app.route('/edit/<int:diary_id>', methods=['GET', 'POST'])
@login_required
def edit(diary_id):
    if request.method == 'GET':
        with connection.cursor() as cursor:
            sql = "SELECT * FROM diary WHERE id=%s"
            cursor.execute(sql, (diary_id,))
            diary = cursor.fetchone()
        return render_template('edit.html', diary=diary)
    elif request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        edit_diary(diary_id, title, content)
        return redirect(url_for('index'))

@app.route('/delete/<int:diary_id>', methods=['POST'])
@login_required
def delete(diary_id):
    delete_diary(diary_id)
    return redirect(url_for('index'))

@app.route('/user_notes')
@login_required
def user_notes():
    user_id = verify_token(session.get('token'))
    with connection.cursor() as cursor:
        sql = "SELECT * FROM diary WHERE user_id=%s"
        cursor.execute(sql, (user_id,))
        user_diaries = cursor.fetchall()
    return render_template('user_notes.html', diaries=user_diaries)

# 根路由重定向到登录页
@app.route('/')
def redirect_to_login():
    return redirect(url_for('login'))

if __name__ == '__main__':
    create_database()
    connection.select_db('diary_db')
    create_user_table()
    create_diary_table()
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(host="0.0.0.0", debug=True, port=6000)
