import secrets
import string
from app import create_app
from extensions import db, bcrypt
from models import User

def create_admin():
    """Создание администратора через командную строку (без вывода пароля в логи)"""
    app = create_app()
    with app.app_context():
        print("=== Создание администратора ===")
        username = input("Имя пользователя (default: admin): ") or "admin"
        email = input("Email: ")
        password = input("Пароль (минимум 8 символов): ")
        
        if len(password) < 8:
            print("❌ Пароль слишком короткий")
            return
        
        if User.query.filter_by(username=username).first():
            print("❌ Имя пользователя уже существует")
            return
        
        if User.query.filter_by(email=email).first():
            print("❌ Email уже зарегистрирован")
            return
        
        admin = User(
            username=username,
            email=email,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f"✅ Администратор {username} успешно создан")

if __name__ == "__main__":
    create_admin()