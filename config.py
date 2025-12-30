import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """Flask应用配置类"""
    
    # Flask基础配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_secret_key_change_in_production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # 文章显示配置
    ARTICLES_PER_PAGE = int(os.getenv('ARTICLES_PER_PAGE', '10'))  # 首页显示的文章数量
    
    # 本地数据库配置
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'root')
    DB_NAME = os.getenv('DB_NAME', 'flask_app')
    
    # 远程网站数据库配置
    REMOTE_DB_HOST = os.getenv('REMOTE_DB_HOST', '192.168.58.25')
    REMOTE_DB_PORT = os.getenv('REMOTE_DB_PORT', '3306')
    REMOTE_DB_USER = os.getenv('REMOTE_DB_USER', 'flask')
    REMOTE_DB_PASSWORD = os.getenv('REMOTE_DB_PASSWORD', 'root')
    REMOTE_DB_NAME = os.getenv('REMOTE_DB_NAME', 'flask_app')
    
    # SQLAlchemy配置
    # 使用PyMySQL作为MySQL驱动
    SQLALCHEMY_DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4'
    
    # 远程数据库连接URI
    REMOTE_DATABASE_URI = f'mysql+pymysql://{REMOTE_DB_USER}:{REMOTE_DB_PASSWORD}@{REMOTE_DB_HOST}:{REMOTE_DB_PORT}/{REMOTE_DB_NAME}?charset=utf8mb4'
    
    # 禁用SQLAlchemy的事件系统（可选，减少内存消耗）
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 数据库连接池配置（可选）
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,        # 连接池大小
        'pool_recycle': 3600,   # 连接回收时间（秒）
        'pool_pre_ping': True,  # 每次连接前检查连接是否有效
    }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
