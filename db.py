import sqlite3
import bcrypt
from cryptography.fernet import Fernet, InvalidToken
import os

# secret.key 파일에서 키를 로드하는 함수
def load_fernet_key():
    # secret.key 파일에서 키 로드
    with open("secret.key", "rb") as key_file:
        key = key_file.read()
    return Fernet(key)

# Fernet 키 로드 및 암호화 객체 초기화
try:
    cipher_suite = load_fernet_key()
except FileNotFoundError:
    print("secret.key 파일을 찾을 수 없습니다. 키를 생성하거나 올바른 위치에 파일이 있는지 확인하세요.")
    cipher_suite = None

# 비밀번호 해시화
def hash_password(password):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

# 비밀번호 검증
def check_password(password, hashed):
    if isinstance(hashed, str): 
        hashed = hashed.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# API 키 암호화
def encrypt_api_key(api_key):
    if cipher_suite is None:
        print("Cipher suite is not initialized. Cannot encrypt the API key.")
        return None
    return cipher_suite.encrypt(api_key.encode('utf-8'))

# API 키 복호화
def decrypt_api_key(encrypted_key):
    if cipher_suite is None:
        print("Cipher suite is not initialized. Cannot decrypt the API key.")
        return None
    try:
        return cipher_suite.decrypt(encrypted_key).decode('utf-8')
    except InvalidToken:
        print("Invalid Token: Unable to decrypt the API key.")
        return None

# 데이터베이스 연결
def create_connection():
    try:
        conn = sqlite3.connect('users.db')
        conn.execute("PRAGMA foreign_keys = 1")  # 외래 키 기능 활성화
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

# users 테이블 생성
def create_user_table():
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                api_key BLOB
            );
            ''')
        conn.close()

# personal_info 테이블 생성
def create_personal_info_table():
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS personal_info (
                user_id INTEGER PRIMARY KEY,
                name TEXT, 
                birthdate DATE, 
                gender TEXT, 
                height REAL, 
                weight REAL, 
                personal_color TEXT, 
                mbti TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            ''')
        conn.close()

# 회원가입
def register_user(username, password):
    conn = create_connection()
    if conn:
        hashed_password = hash_password(password)
        try:
            with conn:
                conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            print("회원가입이 완료되었습니다.")
        except sqlite3.IntegrityError:
            print("이미 존재하는 사용자 이름입니다.")
        conn.close()

# 로그인
def login_user(username, password):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password(password, user[2]):
            print("로그인 성공")
            return user
        else:
            print("로그인 실패: 아이디나 비밀번호가 올바르지 않습니다.")
    return None

# API 키 업데이트
def update_api_key(username, api_key):
    conn = create_connection()
    if conn:
        encrypted_key = encrypt_api_key(api_key)
        with conn:
            conn.execute('UPDATE users SET api_key = ? WHERE username = ?', (encrypted_key, username))
        conn.close()
        print("API 키가 업데이트되었습니다.")

# API 키 불러오기
def get_api_key(username):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT api_key FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return decrypt_api_key(result[0])
    return None

# 개인 정보 추가
def add_personal_info(user_id, name, birthdate, gender, height, weight, personal_color, mbti):
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            INSERT INTO personal_info (user_id, name, birthdate, gender, height, weight, personal_color, mbti)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, name, birthdate, gender, height, weight, personal_color, mbti))
        conn.close()
        print("개인 정보가 추가되었습니다.")

# 개인 정보 조회
def get_personal_info(user_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM personal_info WHERE user_id = ?', (user_id,))
        info = cursor.fetchone()
        conn.close()
        return info
    return None

# 개인 정보 업데이트
def update_personal_info(user_id, name, birthdate, gender, height, weight, personal_color, mbti):
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            UPDATE personal_info
            SET name = ?, birthdate = ?, gender = ?, height = ?, weight = ?, personal_color = ?, mbti = ?
            WHERE user_id = ?
            ''', (name, birthdate, gender, height, weight, personal_color, mbti, user_id))
        conn.close()
        print("개인 정보가 업데이트되었습니다.")

# 모든 개인 정보 조회
def get_all_personal_info():
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM personal_info')
        all_info = cursor.fetchall()
        conn.close()
        return all_info
    return []

# user_images 테이블 생성
def create_user_images_table():
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            CREATE TABLE IF NOT EXISTS user_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            ''')
        conn.close()
        print("user_images 테이블이 생성되었습니다.")

# 이미지 정보 추가
def add_user_image(user_id, filename, filepath):
    conn = create_connection()
    if conn:
        with conn:
            conn.execute('''
            INSERT INTO user_images (user_id, filename, filepath)
            VALUES (?, ?, ?)
            ''', (user_id, filename, filepath))
        conn.close()
        print("이미지 정보가 추가되었습니다.")

# 특정 사용자가 업로드한 모든 이미지 조회 (최신순으로 정렬)
def get_user_images(user_id):
    conn = create_connection()
    if conn:
        cursor = conn.cursor()
        # 최신 업로드일 기준으로 내림차순 정렬
        cursor.execute('SELECT filename, filepath, upload_date FROM user_images WHERE user_id = ? ORDER BY upload_date DESC', (user_id,))
        images = cursor.fetchall()
        conn.close()
        return images
    return []


# 테이블 생성
def initialize_database():
    create_user_table()
    create_personal_info_table()
    create_user_images_table()  # 추가된 부분

