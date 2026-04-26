from typing import Dict, List, Any
from datetime import datetime
from app.models.database import execute_query, execute_insert, get_db_connection
from config import Config

class AccountService:
    def get_account_info(self) -> Dict[str, Any]:
        account = execute_query(
            'SELECT * FROM account ORDER BY id DESC LIMIT 1',
            fetch_one=True
        )
        
        if account:
            return {
                'total_capital': float(account['total_capital']),
                'available_cash': float(account['available_cash']),
                'market_value': float(account['market_value']),
                'total_profit': float(account['total_profit']),
                'profit_rate': float(account['profit_rate']),
                'total_assets': float(account['available_cash']) + float(account['market_value']),
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        return {
            'total_capital': Config.INITIAL_CAPITAL,
            'available_cash': Config.INITIAL_CAPITAL,
            'market_value': 0.0,
            'total_profit': 0.0,
            'profit_rate': 0.0,
            'total_assets': Config.INITIAL_CAPITAL,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_portfolio(self) -> List[Dict[str, Any]]:
        portfolio = execute_query(
            'SELECT * FROM portfolio WHERE quantity > 0 ORDER BY market_value DESC',
            fetch_all=True
        )
        
        result = []
        for item in portfolio:
            result.append({
                'stock_symbol': item['stock_symbol'],
                'stock_name': item['stock_name'],
                'quantity': int(item['quantity']),
                'avg_cost_price': float(item['avg_cost_price']),
                'current_price': float(item['current_price']),
                'market_value': float(item['market_value']),
                'profit_loss': float(item['profit_loss']),
                'profit_loss_rate': float(item['profit_loss_rate'])
            })
        
        return result
    
    def get_transaction_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        transactions = execute_query(
            'SELECT * FROM transactions ORDER BY transaction_time DESC LIMIT ?',
            (limit,),
            fetch_all=True
        )
        
        result = []
        for tx in transactions:
            result.append({
                'id': tx['id'],
                'transaction_type': tx['transaction_type'],
                'stock_symbol': tx['stock_symbol'],
                'stock_name': tx['stock_name'],
                'quantity': int(tx['quantity']),
                'price': float(tx['price']),
                'total_amount': float(tx['total_amount']),
                'fee': float(tx['fee']),
                'stamp_duty': float(tx['stamp_duty']),
                'transfer_fee': float(tx['transfer_fee']),
                'transaction_time': tx['transaction_time']
            })
        
        return result
    
    def update_account_balance(self, cash_change: float, market_value_change: float = 0):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM account ORDER BY id DESC LIMIT 1')
        account = cursor.fetchone()
        
        if account:
            new_available_cash = float(account['available_cash']) + cash_change
            new_market_value = float(account['market_value']) + market_value_change
            total_assets = new_available_cash + new_market_value
            total_profit = total_assets - float(account['total_capital'])
            profit_rate = (total_profit / float(account['total_capital'])) * 100
            
            cursor.execute('''
                UPDATE account SET 
                    available_cash = ?,
                    market_value = ?,
                    total_profit = ?,
                    profit_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_available_cash, new_market_value, total_profit, profit_rate, account['id']))
        
        conn.commit()
        conn.close()
    
    def update_portfolio_price(self, stock_symbol: str, current_price: float):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM portfolio WHERE stock_symbol = ?', (stock_symbol,))
        holding = cursor.fetchone()
        
        if holding:
            quantity = int(holding['quantity'])
            avg_cost = float(holding['avg_cost_price'])
            market_value = quantity * current_price
            profit_loss = (current_price - avg_cost) * quantity
            profit_loss_rate = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
            
            cursor.execute('''
                UPDATE portfolio SET
                    current_price = ?,
                    market_value = ?,
                    profit_loss = ?,
                    profit_loss_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE stock_symbol = ?
            ''', (current_price, market_value, profit_loss, profit_loss_rate, stock_symbol))
        
        conn.commit()
        conn.close()
    
    def add_to_portfolio(self, stock_symbol: str, stock_name: str, quantity: int, price: float):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM portfolio WHERE stock_symbol = ?', (stock_symbol,))
        existing = cursor.fetchone()
        
        if existing:
            current_quantity = int(existing['quantity'])
            current_avg_cost = float(existing['avg_cost_price'])
            
            new_quantity = current_quantity + quantity
            new_avg_cost = ((current_quantity * current_avg_cost) + (quantity * price)) / new_quantity
            
            cursor.execute('''
                UPDATE portfolio SET
                    quantity = ?,
                    avg_cost_price = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE stock_symbol = ?
            ''', (new_quantity, new_avg_cost, stock_symbol))
        else:
            cursor.execute('''
                INSERT INTO portfolio (
                    stock_symbol, stock_name, quantity, avg_cost_price,
                    current_price, market_value, profit_loss, profit_loss_rate
                ) VALUES (?, ?, ?, ?, ?, 0, 0, 0)
            ''', (stock_symbol, stock_name, quantity, price))
        
        conn.commit()
        conn.close()
    
    def remove_from_portfolio(self, stock_symbol: str, quantity: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM portfolio WHERE stock_symbol = ?', (stock_symbol,))
        existing = cursor.fetchone()
        
        if existing:
            current_quantity = int(existing['quantity'])
            new_quantity = current_quantity - quantity
            
            if new_quantity <= 0:
                cursor.execute('DELETE FROM portfolio WHERE stock_symbol = ?', (stock_symbol,))
            else:
                cursor.execute('''
                    UPDATE portfolio SET
                        quantity = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE stock_symbol = ?
                ''', (new_quantity, stock_symbol))
        
        conn.commit()
        conn.close()
    
    def record_transaction(self, transaction_type: str, stock_symbol: str, stock_name: str,
                           quantity: int, price: float, total_amount: float,
                           fee: float, stamp_duty: float, transfer_fee: float):
        execute_insert('''
            INSERT INTO transactions (
                transaction_type, stock_symbol, stock_name, quantity,
                price, total_amount, fee, stamp_duty, transfer_fee
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_type, stock_symbol, stock_name, quantity,
              price, total_amount, fee, stamp_duty, transfer_fee))
    
    def recalculate_market_value(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT SUM(market_value) as total FROM portfolio WHERE quantity > 0')
        result = cursor.fetchone()
        total_market_value = float(result['total']) if result and result['total'] else 0.0
        
        cursor.execute('SELECT * FROM account ORDER BY id DESC LIMIT 1')
        account = cursor.fetchone()
        
        if account:
            total_assets = float(account['available_cash']) + total_market_value
            total_profit = total_assets - float(account['total_capital'])
            profit_rate = (total_profit / float(account['total_capital'])) * 100
            
            cursor.execute('''
                UPDATE account SET
                    market_value = ?,
                    total_profit = ?,
                    profit_rate = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (total_market_value, total_profit, profit_rate, account['id']))
        
        conn.commit()
        conn.close()
