import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'monipan-secret-key-2024'
    
    INITIAL_CAPITAL = 1000000.0
    TRANSACTION_FEE_RATE = 0.0003
    STAMP_DUTY_RATE = 0.001
    TRANSFER_FEE = 0.00002
    
    TUSHARE_TOKEN = os.environ.get('TUSHARE_TOKEN') or ''
    
    DATA_CACHE_TIME = 60
    
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'monipan.db')
    
    DEBUG = True
