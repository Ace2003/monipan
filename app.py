from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import os

from config import Config
from app.data.data_provider import DataProvider
from app.services.trading_service import TradingService
from app.services.account_service import AccountService
from app.models.database import init_db

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

data_provider = DataProvider()
trading_service = TradingService()
account_service = AccountService()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/market')
def get_market_data():
    try:
        market_data = data_provider.get_market_overview()
        return jsonify({'success': True, 'data': market_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stock/<symbol>')
def get_stock_data(symbol):
    try:
        stock_info = data_provider.get_stock_info(symbol)
        return jsonify({'success': True, 'data': stock_info})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/stock/<symbol>/history')
def get_stock_history(symbol):
    try:
        period = request.args.get('period', '1month')
        history_data = data_provider.get_stock_history(symbol, period)
        return jsonify({'success': True, 'data': history_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/account')
def get_account_info():
    try:
        account_info = account_service.get_account_info()
        return jsonify({'success': True, 'data': account_info})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/portfolio')
def get_portfolio():
    try:
        portfolio = account_service.get_portfolio()
        return jsonify({'success': True, 'data': portfolio})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/trade/buy', methods=['POST'])
def buy_stock():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        quantity = int(data.get('quantity'))
        price = float(data.get('price'))
        
        result = trading_service.buy_stock(symbol, quantity, price)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/trade/sell', methods=['POST'])
def sell_stock():
    try:
        data = request.get_json()
        symbol = data.get('symbol')
        quantity = int(data.get('quantity'))
        price = float(data.get('price'))
        
        result = trading_service.sell_stock(symbol, quantity, price)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/transactions')
def get_transactions():
    try:
        limit = request.args.get('limit', 50)
        transactions = account_service.get_transaction_history(limit)
        return jsonify({'success': True, 'data': transactions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/search')
def search_stocks():
    try:
        keyword = request.args.get('keyword', '')
        results = data_provider.search_stocks(keyword)
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/news')
def get_market_news():
    try:
        news = data_provider.get_market_news()
        return jsonify({'success': True, 'data': news})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

def init_app():
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    init_db()
    
    print("=" * 50)
    print("模拟盘炒股系统已启动")
    print("=" * 50)
    print(f"初始资金: {Config.INITIAL_CAPITAL:,.2f} 元")
    print(f"交易费率: {Config.TRANSACTION_FEE_RATE * 100}%")
    print(f"印花税: {Config.STAMP_DUTY_RATE * 100}% (卖出时收取)")
    print("=" * 50)
    print(f"服务地址: http://localhost:5000")
    print("=" * 50)

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
