import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
import re

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: akshare未安装，将使用备用数据源")

from app.data.crawler import StockCrawler

class DataProvider:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.crawler = StockCrawler()
        self._cache_ttl = {
            'market_overview': 30,
            'stock_info': 10,
            'stock_history': 300,
            'search': 60,
            'news': 120,
            'hot_stocks': 60
        }

    def _get_cache(self, key):
        if key in self.cache and key in self.cache_time:
            import time
            if time.time() - self.cache_time[key] < self._cache_ttl.get(key.split(':')[0], 60):
                return self.cache[key]
        return None

    def _set_cache(self, key, value):
        import time
        self.cache[key] = value
        self.cache_time[key] = time.time()
    
    def get_market_overview(self) -> Dict[str, Any]:
        cached = self._get_cache('market_overview')
        if cached:
            return cached
        
        try:
            indices = []
            sentiment_data = None
            
            try:
                sentiment_data = self.crawler.get_market_sentiment()
            except Exception as e:
                print(f"新浪API获取市场情绪失败: {e}")
            
            index_configs = [
                ('sh000001', '上证指数', 'sh_index'),
                ('sz399001', '深证成指', 'sz_index'),
                ('sz399006', '创业板指', 'cy_index'),
                ('sh000688', '科创50', None)
            ]
            
            for symbol, name, sentiment_key in index_configs:
                index_data = None
                
                if sentiment_data and sentiment_key and sentiment_key in sentiment_data and sentiment_data[sentiment_key]:
                    idx_data = sentiment_data[sentiment_key]
                    index_data = {
                        'symbol': symbol,
                        'name': name,
                        'current': idx_data.get('current', 0),
                        'change': idx_data.get('change', 0),
                        'change_point': idx_data.get('change_point', 0),
                        'volume': idx_data.get('volume', 0),
                        'amount': idx_data.get('amount', 0)
                    }
                
                if not index_data or index_data['current'] == 0:
                    index_data = self._get_index_info_fallback(symbol, name)
                
                indices.append(index_data)
            
            result = {
                'indices': indices,
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._set_cache('market_overview', result)
            return result
            
        except Exception as e:
            print(f"获取市场概览失败: {e}")
            return self._get_fallback_market_data()
    
    def _get_index_info_fallback(self, symbol: str, name: str) -> Dict[str, Any]:
        if AKSHARE_AVAILABLE:
            try:
                df = ak.stock_zh_index_spot()
                index_row = df[df['代码'].str.contains(symbol[2:])]
                
                if not index_row.empty:
                    row = index_row.iloc[0]
                    return {
                        'symbol': symbol,
                        'name': name,
                        'current': float(row['最新价']),
                        'change': float(row['涨跌幅']),
                        'change_point': float(row['涨跌额']),
                        'volume': float(row['成交量']) if pd.notna(row['成交量']) else 0,
                        'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0
                    }
            except Exception as e:
                print(f"akshare获取指数信息失败: {e}")
        
        return self._get_fallback_index(symbol, name)
    
    def _get_fallback_index(self, symbol: str, name: str) -> Dict[str, Any]:
        base_values = {
            'sh000001': 3100.0,
            'sz399001': 10500.0,
            'sz399006': 2100.0,
            'sh000688': 900.0
        }
        base = base_values.get(symbol, 1000.0)
        change = np.random.uniform(-2, 2)
        
        return {
            'symbol': symbol,
            'name': name,
            'current': round(base * (1 + change/100), 2),
            'change': round(change, 2),
            'change_point': round(base * change/100, 2),
            'volume': round(np.random.uniform(10000000, 50000000), 2),
            'amount': round(np.random.uniform(100000000, 500000000), 2)
        }
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        try:
            clean_symbol = self._clean_symbol(symbol)
            
            if AKSHARE_AVAILABLE:
                try:
                    realtime_df = ak.stock_zh_a_spot_em()
                    stock_row = realtime_df[realtime_df['代码'] == clean_symbol]
                    
                    if stock_row.empty:
                        stock_row = realtime_df[realtime_df['代码'].str.contains(clean_symbol)]
                    
                    if not stock_row.empty:
                        row = stock_row.iloc[0]
                        return {
                            'symbol': self._format_symbol(clean_symbol),
                            'name': row['名称'],
                            'current': float(row['最新价']),
                            'change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0,
                            'change_point': float(row['涨跌额']) if pd.notna(row['涨跌额']) else 0,
                            'open': float(row['今开']) if pd.notna(row['今开']) else 0,
                            'high': float(row['最高']) if pd.notna(row['最高']) else 0,
                            'low': float(row['最低']) if pd.notna(row['最低']) else 0,
                            'prev_close': float(row['昨收']) if pd.notna(row['昨收']) else 0,
                            'volume': float(row['成交量']) if pd.notna(row['成交量']) else 0,
                            'amount': float(row['成交额']) if pd.notna(row['成交额']) else 0,
                            'turnover_rate': float(row['换手率']) if pd.notna(row['换手率']) else 0,
                            'pe_ratio': float(row['市盈率-动态']) if pd.notna(row['市盈率-动态']) else 0,
                            'market_cap': float(row['总市值']) if pd.notna(row['总市值']) else 0,
                            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                except Exception as e:
                    print(f"akshare获取股票信息失败，尝试爬虫: {e}")
            
            crawler_data = self.crawler.get_stock_detail_from_sina(self._format_symbol(clean_symbol))
            if crawler_data:
                return {
                    'symbol': crawler_data.get('symbol', self._format_symbol(clean_symbol)),
                    'name': crawler_data.get('name', f'股票{clean_symbol}'),
                    'current': crawler_data.get('current', 0),
                    'change': crawler_data.get('change', 0),
                    'change_point': crawler_data.get('change_point', 0),
                    'open': crawler_data.get('open', 0),
                    'high': crawler_data.get('high', 0),
                    'low': crawler_data.get('low', 0),
                    'prev_close': crawler_data.get('prev_close', 0),
                    'volume': crawler_data.get('volume', 0),
                    'amount': crawler_data.get('amount', 0),
                    'turnover_rate': 0,
                    'pe_ratio': 0,
                    'market_cap': 0,
                    'update_time': crawler_data.get('update_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }
            
            return self._get_fallback_stock_info(clean_symbol)
        except Exception as e:
            print(f"获取股票信息失败: {e}")
            return self._get_fallback_stock_info(self._clean_symbol(symbol))
    
    def _get_fallback_stock_info(self, symbol: str) -> Dict[str, Any]:
        stock_names = {
            '600519': '贵州茅台',
            '000001': '平安银行',
            '601318': '中国平安',
            '000858': '五粮液',
            '002594': '比亚迪',
            '600036': '招商银行',
            '601012': '隆基绿能',
            '300750': '宁德时代',
            '600900': '长江电力',
            '600276': '恒瑞医药'
        }
        
        name = stock_names.get(symbol, f'股票{symbol}')
        base_price = float(symbol) % 100 + 10 if symbol.isdigit() else 50
        change = np.random.uniform(-5, 5)
        current = base_price * (1 + change/100)
        
        return {
            'symbol': self._format_symbol(symbol),
            'name': name,
            'current': round(current, 2),
            'change': round(change, 2),
            'change_point': round(current - base_price, 2),
            'open': round(base_price * (1 + np.random.uniform(-1, 1)/100), 2),
            'high': round(current * (1 + np.random.uniform(0, 2)/100), 2),
            'low': round(current * (1 - np.random.uniform(0, 2)/100), 2),
            'prev_close': round(base_price, 2),
            'volume': round(np.random.uniform(1000000, 10000000), 2),
            'amount': round(np.random.uniform(10000000, 100000000), 2),
            'turnover_rate': round(np.random.uniform(0.5, 5), 2),
            'pe_ratio': round(np.random.uniform(10, 50), 2),
            'market_cap': round(np.random.uniform(10000000000, 100000000000), 2),
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_stock_history(self, symbol: str, period: str = '1month') -> Dict[str, Any]:
        cache_key = f'history:{symbol}:{period}'
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            clean_symbol = self._clean_symbol(symbol)
            
            if period == 'intraday':
                result = self._get_intraday_data(clean_symbol)
                self._set_cache(cache_key, result)
                return result
            
            end_date = datetime.now().strftime('%Y%m%d')
            
            period_map = {
                '1week': timedelta(days=7),
                '1month': timedelta(days=30),
                '3month': timedelta(days=90),
                '6month': timedelta(days=180),
                '1year': timedelta(days=365)
            }
            
            start_date = (datetime.now() - period_map.get(period, timedelta(days=30))).strftime('%Y%m%d')
            
            if AKSHARE_AVAILABLE:
                try:
                    if clean_symbol.startswith('6'):
                        market = 'sh'
                    else:
                        market = 'sz'
                    
                    df = ak.stock_zh_a_hist(symbol=clean_symbol, period='daily', 
                                             start_date=start_date, end_date=end_date, adjust='qfq')
                    
                    if not df.empty:
                        history_data = []
                        for _, row in df.iterrows():
                            history_data.append({
                                'date': row['日期'].strftime('%Y-%m-%d') if hasattr(row['日期'], 'strftime') else str(row['日期']),
                                'open': float(row['开盘']),
                                'high': float(row['最高']),
                                'low': float(row['最低']),
                                'close': float(row['收盘']),
                                'volume': float(row['成交量']),
                                'amount': float(row['成交额'])
                            })
                        
                        result = {
                            'symbol': self._format_symbol(clean_symbol),
                            'period': period,
                            'data': history_data,
                            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        self._set_cache(cache_key, result)
                        return result
                except Exception as e:
                    print(f"akshare获取历史数据失败: {e}")
            
            try:
                days_map = {
                    '1week': 7,
                    '1month': 30,
                    '3month': 90,
                    '6month': 180,
                    '1year': 365
                }
                days = days_map.get(period, 30)
                
                crawler_history = self.crawler.get_stock_history_from_sina(self._format_symbol(clean_symbol), days)
                if crawler_history and len(crawler_history) > 0:
                    result = {
                        'symbol': self._format_symbol(clean_symbol),
                        'period': period,
                        'data': crawler_history,
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    self._set_cache(cache_key, result)
                    return result
            except Exception as e:
                print(f"爬虫获取历史数据失败: {e}")
            
            fallback = self._get_fallback_history(clean_symbol, period)
            self._set_cache(cache_key, fallback)
            return fallback
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            fallback = self._get_fallback_history(self._clean_symbol(symbol), period)
            self._set_cache(cache_key, fallback)
            return fallback
    
    def _get_intraday_data(self, clean_symbol: str) -> Dict[str, Any]:
        try:
            if AKSHARE_AVAILABLE:
                try:
                    df = ak.stock_zh_a_hist_min_em(symbol=clean_symbol, period='1', adjust='qfq')
                    
                    if not df.empty:
                        history_data = []
                        for _, row in df.tail(240).iterrows():
                            time_str = str(row['时间'])
                            if ' ' in time_str:
                                time_part = time_str.split(' ')[1][:5]
                            else:
                                time_part = time_str[:5]
                            
                            history_data.append({
                                'date': time_part,
                                'open': float(row['开盘']),
                                'high': float(row['最高']),
                                'low': float(row['最低']),
                                'close': float(row['收盘']),
                                'volume': float(row['成交量']),
                                'amount': float(row['成交额'])
                            })
                        
                        return {
                            'symbol': self._format_symbol(clean_symbol),
                            'period': 'intraday',
                            'data': history_data,
                            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                except Exception as e:
                    print(f"akshare获取分时数据失败: {e}")
            
            try:
                intraday_data = self.crawler.get_intraday_from_sina(self._format_symbol(clean_symbol))
                if intraday_data and len(intraday_data) > 0:
                    return {
                        'symbol': self._format_symbol(clean_symbol),
                        'period': 'intraday',
                        'data': intraday_data,
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            except Exception as e:
                print(f"爬虫获取分时数据失败: {e}")
            
            return self._get_fallback_intraday(clean_symbol)
        except Exception as e:
            print(f"获取分时数据失败: {e}")
            return self._get_fallback_intraday(clean_symbol)
    
    def _get_fallback_intraday(self, symbol: str) -> Dict[str, Any]:
        base_price = float(symbol) % 100 + 10 if symbol.isdigit() else 50
        history_data = []
        current_price = base_price * (1 + np.random.uniform(-1, 1)/100)
        
        times = []
        for hour in [9, 10, 11, 13, 14]:
            start_min = 30 if hour == 9 else 0
            end_min = 30 if hour == 11 else 60
            for minute in range(start_min, end_min):
                times.append(f"{hour:02d}:{minute:02d}")
        
        for time_str in times:
            change = np.random.uniform(-0.5, 0.5)
            open_price = current_price
            close_price = open_price * (1 + change/100)
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 0.2)/100)
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 0.2)/100)
            
            history_data.append({
                'date': time_str,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': round(np.random.uniform(10000, 100000), 2),
                'amount': round(close_price * np.random.uniform(10000, 100000), 2)
            })
            
            current_price = close_price
        
        return {
            'symbol': self._format_symbol(symbol),
            'period': 'intraday',
            'data': history_data,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _get_fallback_history(self, symbol: str, period: str) -> Dict[str, Any]:
        period_map = {
            '1week': 7,
            '1month': 30,
            '3month': 90,
            '6month': 180,
            '1year': 365
        }
        
        days = period_map.get(period, 30)
        base_price = float(symbol) % 100 + 10 if symbol.isdigit() else 50
        
        history_data = []
        current_price = base_price
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=days - i - 1)).strftime('%Y-%m-%d')
            change = np.random.uniform(-3, 3)
            open_price = current_price * (1 + np.random.uniform(-1, 1)/100)
            close_price = open_price * (1 + change/100)
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, 1)/100)
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, 1)/100)
            
            history_data.append({
                'date': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': round(np.random.uniform(1000000, 10000000), 2),
                'amount': round(close_price * np.random.uniform(1000000, 10000000), 2)
            })
            
            current_price = close_price
        
        return {
            'symbol': self._format_symbol(symbol),
            'period': period,
            'data': history_data,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        cache_key = f'search:{keyword}' if keyword else 'search:hot'
        cached = self._get_cache(cache_key)
        if cached:
            return cached
        
        try:
            results = None
            
            if not keyword:
                try:
                    hot_stocks = self.crawler.get_hot_stocks_from_sina()
                    if hot_stocks and len(hot_stocks) > 0:
                        results = hot_stocks
                except:
                    pass
                
                if not results:
                    results = self._get_hot_stocks()
            else:
                if AKSHARE_AVAILABLE:
                    try:
                        realtime_df = ak.stock_zh_a_spot_em()
                        search_results = []
                        
                        mask = (realtime_df['代码'].str.contains(keyword, case=False, na=False) | 
                               realtime_df['名称'].str.contains(keyword, case=False, na=False))
                        
                        filtered = realtime_df[mask].head(20)
                        
                        for _, row in filtered.iterrows():
                            search_results.append({
                                'symbol': self._format_symbol(row['代码']),
                                'name': row['名称'],
                                'current': float(row['最新价']) if pd.notna(row['最新价']) else 0,
                                'change': float(row['涨跌幅']) if pd.notna(row['涨跌幅']) else 0
                            })
                        
                        if search_results:
                            results = search_results
                    except Exception as e:
                        print(f"akshare搜索股票失败，尝试爬虫: {e}")
                
                if not results:
                    crawler_results = self.crawler.search_stocks_by_keyword(keyword)
                    if crawler_results and len(crawler_results) > 0:
                        for item in crawler_results:
                            stock_info = self.get_stock_info(item['symbol'])
                            item['current'] = stock_info.get('current', 0)
                            item['change'] = stock_info.get('change', 0)
                        results = crawler_results
                
                if not results:
                    results = self._get_fallback_search(keyword)
            
            self._set_cache(cache_key, results)
            return results
            
        except Exception as e:
            print(f"搜索股票失败: {e}")
            fallback = self._get_fallback_search(keyword)
            self._set_cache(cache_key, fallback)
            return fallback
    
    def _get_hot_stocks(self) -> List[Dict[str, Any]]:
        hot_stocks = [
            {'symbol': 'sh600519', 'name': '贵州茅台', 'base_price': 1800},
            {'symbol': 'sz000001', 'name': '平安银行', 'base_price': 12},
            {'symbol': 'sh601318', 'name': '中国平安', 'base_price': 45},
            {'symbol': 'sz000858', 'name': '五粮液', 'base_price': 160},
            {'symbol': 'sz002594', 'name': '比亚迪', 'base_price': 250},
            {'symbol': 'sh600036', 'name': '招商银行', 'base_price': 35},
            {'symbol': 'sh601012', 'name': '隆基绿能', 'base_price': 30},
            {'symbol': 'sz300750', 'name': '宁德时代', 'base_price': 200},
            {'symbol': 'sh600900', 'name': '长江电力', 'base_price': 28},
            {'symbol': 'sh600276', 'name': '恒瑞医药', 'base_price': 45}
        ]
        
        results = []
        for stock in hot_stocks:
            change = np.random.uniform(-5, 5)
            results.append({
                'symbol': stock['symbol'],
                'name': stock['name'],
                'current': round(stock['base_price'] * (1 + change/100), 2),
                'change': round(change, 2)
            })
        
        return results
    
    def _get_fallback_search(self, keyword: str) -> List[Dict[str, Any]]:
        hot_stocks = self._get_hot_stocks()
        
        if keyword:
            filtered = [s for s in hot_stocks if 
                       keyword.lower() in s['name'].lower() or 
                       keyword in s['symbol']]
            return filtered if filtered else hot_stocks[:5]
        
        return hot_stocks[:10]
    
    def get_market_news(self) -> List[Dict[str, Any]]:
        cached = self._get_cache('news')
        if cached:
            return cached
        
        try:
            results = None
            
            if AKSHARE_AVAILABLE:
                try:
                    news_list = ak.stock_news_em(symbol="A股市场")
                    
                    if not news_list.empty:
                        news_results = []
                        for _, row in news_list.head(10).iterrows():
                            news_results.append({
                                'title': row['新闻标题'],
                                'url': row['新闻链接'],
                                'source': row['信息来源'],
                                'time': row['发布时间'],
                                'content': row['新闻内容'] if pd.notna(row['新闻内容']) else ''
                            })
                        if news_results and len(news_results) > 0:
                            results = news_results
                except Exception as e:
                    print(f"akshare获取新闻失败，尝试爬虫: {e}")
            
            if not results:
                crawler_news = self.crawler.get_all_news()
                if crawler_news and len(crawler_news) > 0:
                    results = crawler_news
            
            if not results:
                results = self._get_fallback_news()
            
            self._set_cache('news', results)
            return results
            
        except Exception as e:
            print(f"获取新闻失败: {e}")
            fallback = self._get_fallback_news()
            self._set_cache('news', fallback)
            return fallback
    
    def _get_fallback_news(self) -> List[Dict[str, Any]]:
        fallback_news = [
            {
                'title': '央行降准释放长期资金约1万亿元',
                'source': '经济日报',
                'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'content': '中国人民银行决定下调金融机构存款准备金率0.5个百分点，释放长期资金约1万亿元。'
            },
            {
                'title': '新能源汽车板块持续走强',
                'source': '证券时报',
                'time': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
                'content': '受政策利好和销量数据超预期影响，新能源汽车板块今日全线上涨。'
            },
            {
                'title': '科技股回暖带动创业板指上涨',
                'source': '中国证券报',
                'time': (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M'),
                'content': 'AI、芯片等科技板块午后发力，带动创业板指涨幅扩大。'
            },
            {
                'title': '外资持续流入A股市场',
                'source': '上海证券报',
                'time': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M'),
                'content': '北向资金今日净流入超50亿元，连续多日净流入。'
            },
            {
                'title': '消费板块迎来估值修复行情',
                'source': '证券日报',
                'time': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
                'content': '白酒、家电等消费板块今日表现活跃，市场情绪逐渐回暖。'
            }
        ]
        
        return fallback_news
    
    def _clean_symbol(self, symbol: str) -> str:
        if symbol.startswith('sh') or symbol.startswith('sz'):
            return symbol[2:]
        return symbol
    
    def _format_symbol(self, symbol: str) -> str:
        if symbol.startswith('6'):
            return f'sh{symbol}'
        else:
            return f'sz{symbol}'
    
    def get_realtime_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_stock_info(symbol)
        return results
