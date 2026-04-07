import os
from dotenv import load_dotenv

# Загружаем .env только в разработке (на сервере переменные окружения задаются отдельно)
if os.path.exists('.env'):
    load_dotenv()

class Config:
    """Базовый класс конфигурации"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("❌ SECRET_KEY не задан в переменных окружения. Укажите его!")
    
    # База данных: если DATABASE_URL не задан, используем SQLite (только для разработки)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///voice_assistant.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    # Для продакшена обязательно должна быть задана DATABASE_URL
    if not os.environ.get('DATABASE_URL'):
        raise ValueError("❌ В production режиме DATABASE_URL обязательна!")