import sqlite3
import os
from datetime import datetime
from config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_capital REAL DEFAULT 1000000.0,
            available_cash REAL DEFAULT 1000000.0,
            market_value REAL DEFAULT 0.0,
            total_profit REAL DEFAULT 0.0,
            profit_rate REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_symbol TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_cost_price REAL NOT NULL,
            current_price REAL DEFAULT 0.0,
            market_value REAL DEFAULT 0.0,
            profit_loss REAL DEFAULT 0.0,
            profit_loss_rate REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(stock_symbol)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_type TEXT NOT NULL,
            stock_symbol TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            total_amount REAL NOT NULL,
            fee REAL NOT NULL,
            stamp_duty REAL NOT NULL,
            transfer_fee REAL NOT NULL,
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('SELECT COUNT(*) FROM account')
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO account (total_capital, available_cash, market_value, total_profit, profit_rate)
            VALUES (1000000.0, 1000000.0, 0.0, 0.0, 0.0)
        ''')
    
    conn.commit()
    conn.close()

def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    
    result = None
    if fetch_one:
        result = cursor.fetchone()
    elif fetch_all:
        result = cursor.fetchall()
    
    conn.close()
    return result

def execute_insert(query, params=()):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id
