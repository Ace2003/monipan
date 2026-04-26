from typing import Dict, Any
from datetime import datetime
from app.services.account_service import AccountService
from app.data.data_provider import DataProvider
from config import Config

class TradingService:
    def __init__(self):
        self.account_service = AccountService()
        self.data_provider = DataProvider()
    
    def calculate_transaction_fees(self, transaction_type: str, amount: float, quantity: int) -> Dict[str, float]:
        fee = amount * Config.TRANSACTION_FEE_RATE
        fee = max(fee, 5.0)
        
        stamp_duty = amount * Config.STAMP_DUTY_RATE if transaction_type == 'sell' else 0.0
        
        transfer_fee = amount * Config.TRANSFER_FEE
        transfer_fee = max(transfer_fee, 1.0)
        
        return {
            'fee': fee,
            'stamp_duty': stamp_duty,
            'transfer_fee': transfer_fee,
            'total_fees': fee + stamp_duty + transfer_fee
        }
    
    def buy_stock(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        if quantity <= 0 or quantity % 100 != 0:
            raise ValueError("买入数量必须是100的整数倍且大于0")
        
        if price <= 0:
            raise ValueError("价格必须大于0")
        
        stock_info = self.data_provider.get_stock_info(symbol)
        stock_name = stock_info.get('name', symbol)
        
        total_amount = quantity * price
        fees = self.calculate_transaction_fees('buy', total_amount, quantity)
        total_cost = total_amount + fees['total_fees']
        
        account_info = self.account_service.get_account_info()
        if account_info['available_cash'] < total_cost:
            raise ValueError(f"可用资金不足。需要: {total_cost:.2f} 元, 可用: {account_info['available_cash']:.2f} 元")
        
        self.account_service.add_to_portfolio(symbol, stock_name, quantity, price)
        
        cash_change = -total_cost
        market_value_change = total_amount
        self.account_service.update_account_balance(cash_change, market_value_change)
        
        self.account_service.record_transaction(
            'buy', symbol, stock_name, quantity, price, total_amount,
            fees['fee'], fees['stamp_duty'], fees['transfer_fee']
        )
        
        self.account_service.update_portfolio_price(symbol, price)
        
        return {
            'success': True,
            'transaction_type': 'buy',
            'symbol': symbol,
            'name': stock_name,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'fees': fees,
            'total_cost': total_cost,
            'transaction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def sell_stock(self, symbol: str, quantity: int, price: float) -> Dict[str, Any]:
        if quantity <= 0:
            raise ValueError("卖出数量必须大于0")
        
        if price <= 0:
            raise ValueError("价格必须大于0")
        
        portfolio = self.account_service.get_portfolio()
        holding = next((h for h in portfolio if h['stock_symbol'] == symbol), None)
        
        if not holding or holding['quantity'] < quantity:
            available = holding['quantity'] if holding else 0
            raise ValueError(f"持仓不足。尝试卖出: {quantity} 股, 可用: {available} 股")
        
        stock_info = self.data_provider.get_stock_info(symbol)
        stock_name = stock_info.get('name', symbol)
        
        total_amount = quantity * price
        fees = self.calculate_transaction_fees('sell', total_amount, quantity)
        net_receipt = total_amount - fees['total_fees']
        
        self.account_service.remove_from_portfolio(symbol, quantity)
        
        cash_change = net_receipt
        market_value_change = -total_amount
        self.account_service.update_account_balance(cash_change, market_value_change)
        
        self.account_service.record_transaction(
            'sell', symbol, stock_name, quantity, price, total_amount,
            fees['fee'], fees['stamp_duty'], fees['transfer_fee']
        )
        
        return {
            'success': True,
            'transaction_type': 'sell',
            'symbol': symbol,
            'name': stock_name,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'fees': fees,
            'net_receipt': net_receipt,
            'transaction_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def update_portfolio_prices(self):
        portfolio = self.account_service.get_portfolio()
        
        for holding in portfolio:
            stock_info = self.data_provider.get_stock_info(holding['stock_symbol'])
            current_price = stock_info.get('current', holding['current_price'])
            self.account_service.update_portfolio_price(holding['stock_symbol'], current_price)
        
        self.account_service.recalculate_market_value()
