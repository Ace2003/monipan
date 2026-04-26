import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import random

class StockCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        })
        self.cache = {}
        self.cache_expiry = {}
    
    def get_baidu_finance_news(self) -> List[Dict[str, Any]]:
        try:
            url = 'https://finance.sina.com.cn/stock/'
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            news_list = []
            
            news_items = soup.find_all('a', href=True)
            for item in news_items[:30]:
                href = item.get('href', '')
                title = item.get_text(strip=True)
                
                if (href and ('finance' in href or 'stock' in href or 'news' in href) 
                    and title and len(title) > 10 and len(title) < 80):
                    news_item = {
                        'title': title,
                        'url': href if href.startswith('http') else f'https://finance.sina.com.cn{href}',
                        'source': '新浪财经',
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'content': ''
                    }
                    if news_item not in news_list:
                        news_list.append(news_item)
            
            return news_list[:10]
        except Exception as e:
            print(f"爬取新浪财经新闻失败: {e}")
            return []
    
    def get_eastmoney_news(self) -> List[Dict[str, Any]]:
        try:
            url = 'https://stock.eastmoney.com/'
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            news_list = []
            
            news_items = soup.find_all('a', href=True)
            for item in news_items[:30]:
                href = item.get('href', '')
                title = item.get_text(strip=True)
                
                if (href and ('eastmoney' in href or 'news' in href or 'stock' in href)
                    and title and len(title) > 10 and len(title) < 80):
                    news_item = {
                        'title': title,
                        'url': href if href.startswith('http') else f'https://stock.eastmoney.com{href}',
                        'source': '东方财富',
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M'),
                        'content': ''
                    }
                    if news_item not in news_list:
                        news_list.append(news_item)
            
            return news_list[:10]
        except Exception as e:
            print(f"爬取东方财富新闻失败: {e}")
            return []
    
    def get_hot_stocks_from_sina(self) -> List[Dict[str, Any]]:
        try:
            url = 'http://vip.stock.finance.sina.com.cn/q/go.php/vRPD/kind/1.phtml'
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            soup = BeautifulSoup(response.text, 'lxml')
            
            hot_stocks = []
            
            table = soup.find('table', {'class': 'list_table'})
            if table:
                rows = table.find_all('tr')[1:11]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        code = cols[1].get_text(strip=True)
                        name = cols[2].get_text(strip=True)
                        change = cols[3].get_text(strip=True).replace('%', '')
                        price = cols[4].get_text(strip=True)
                        
                        try:
                            change_float = float(change)
                            price_float = float(price)
                        except:
                            change_float = 0.0
                            price_float = 0.0
                        
                        hot_stocks.append({
                            'symbol': f'sh{code}' if code.startswith('6') else f'sz{code}',
                            'name': name,
                            'current': price_float,
                            'change': change_float
                        })
            
            return hot_stocks
        except Exception as e:
            print(f"爬取新浪热门股票失败: {e}")
            return []
    
    def get_market_sentiment(self) -> Dict[str, Any]:
        try:
            url = 'https://hq.sinajs.cn/list=sh000001,sz399001,sz399006'
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            
            sentiment_data = {
                'sh_index': {},
                'sz_index': {},
                'cy_index': {},
                'overall_sentiment': 'neutral',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            lines = response.text.strip().split('\n')
            
            for i, line in enumerate(lines[:3]):
                match = re.search(r'="([^"]+)"', line)
                if match:
                    data = match.group(1).split(',')
                    if len(data) >= 33:
                        name = data[0]
                        open_price = float(data[1])
                        prev_close = float(data[2])
                        current = float(data[3])
                        high = float(data[4])
                        low = float(data[5])
                        volume = float(data[8])
                        amount = float(data[9])
                        
                        change = (current - prev_close) / prev_close * 100 if prev_close > 0 else 0
                        change_point = current - prev_close
                        
                        index_data = {
                            'name': name,
                            'current': current,
                            'change': change,
                            'change_point': change_point,
                            'open': open_price,
                            'high': high,
                            'low': low,
                            'prev_close': prev_close,
                            'volume': volume,
                            'amount': amount
                        }
                        
                        if i == 0:
                            sentiment_data['sh_index'] = index_data
                        elif i == 1:
                            sentiment_data['sz_index'] = index_data
                        else:
                            sentiment_data['cy_index'] = index_data
            
            changes = []
            if 'change' in sentiment_data['sh_index']:
                changes.append(sentiment_data['sh_index']['change'])
            if 'change' in sentiment_data['sz_index']:
                changes.append(sentiment_data['sz_index']['change'])
            if 'change' in sentiment_data['cy_index']:
                changes.append(sentiment_data['cy_index']['change'])
            
            if changes:
                avg_change = sum(changes) / len(changes)
                if avg_change > 1:
                    sentiment_data['overall_sentiment'] = 'bullish'
                elif avg_change > 0:
                    sentiment_data['overall_sentiment'] = 'slightly_bullish'
                elif avg_change > -1:
                    sentiment_data['overall_sentiment'] = 'slightly_bearish'
                else:
                    sentiment_data['overall_sentiment'] = 'bearish'
            
            return sentiment_data
        except Exception as e:
            print(f"获取市场情绪失败: {e}")
            return {
                'sh_index': {},
                'sz_index': {},
                'cy_index': {},
                'overall_sentiment': 'neutral',
                'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def get_stock_detail_from_sina(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            clean_symbol = symbol.replace('sh', '').replace('sz', '')
            if symbol.startswith('sh'):
                market = 'sh'
            else:
                market = 'sz'
            
            url = f'https://hq.sinajs.cn/list={market}{clean_symbol}'
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            
            match = re.search(r'="([^"]+)"', response.text)
            if match:
                data = match.group(1).split(',')
                if len(data) >= 33:
                    name = data[0]
                    open_price = float(data[1]) if data[1] else 0.0
                    prev_close = float(data[2]) if data[2] else 0.0
                    current = float(data[3]) if data[3] else 0.0
                    high = float(data[4]) if data[4] else 0.0
                    low = float(data[5]) if data[5] else 0.0
                    bid1 = float(data[6]) if data[6] else 0.0
                    ask1 = float(data[7]) if data[7] else 0.0
                    volume = float(data[8]) if data[8] else 0.0
                    amount = float(data[9]) if data[9] else 0.0
                    
                    change = (current - prev_close) / prev_close * 100 if prev_close > 0 else 0.0
                    change_point = current - prev_close
                    
                    buy_volumes = []
                    buy_prices = []
                    sell_volumes = []
                    sell_prices = []
                    
                    for i in range(5):
                        buy_vol = float(data[10 + i*2]) if data[10 + i*2] else 0.0
                        buy_price = float(data[11 + i*2]) if data[11 + i*2] else 0.0
                        sell_vol = float(data[20 + i*2]) if data[20 + i*2] else 0.0
                        sell_price = float(data[21 + i*2]) if data[21 + i*2] else 0.0
                        
                        buy_volumes.append(buy_vol)
                        buy_prices.append(buy_price)
                        sell_volumes.append(sell_vol)
                        sell_prices.append(sell_price)
                    
                    return {
                        'symbol': f'{market}{clean_symbol}',
                        'name': name,
                        'current': current,
                        'change': round(change, 2),
                        'change_point': round(change_point, 2),
                        'open': open_price,
                        'high': high,
                        'low': low,
                        'prev_close': prev_close,
                        'volume': volume,
                        'amount': amount,
                        'bid1': bid1,
                        'ask1': ask1,
                        'buy_volumes': buy_volumes,
                        'buy_prices': buy_prices,
                        'sell_volumes': sell_volumes,
                        'sell_prices': sell_prices,
                        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            
            return None
        except Exception as e:
            print(f"爬取股票详情失败: {e}")
            return None
    
    def get_all_news(self) -> List[Dict[str, Any]]:
        news = []
        
        sina_news = self.get_baidu_finance_news()
        eastmoney_news = self.get_eastmoney_news()
        
        news.extend(sina_news)
        news.extend(eastmoney_news)
        
        seen_titles = set()
        unique_news = []
        for item in news:
            if item['title'] not in seen_titles:
                seen_titles.add(item['title'])
                unique_news.append(item)
        
        return unique_news[:10]
    
    def get_realtime_quotes_batch(self, symbols: List[str]) -> Dict[str, Any]:
        results = {}
        
        for symbol in symbols:
            detail = self.get_stock_detail_from_sina(symbol)
            if detail:
                results[symbol] = detail
            
            time.sleep(random.uniform(0.1, 0.3))
        
        return results
    
    def search_stocks_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        try:
            url = f'https://suggest3.sinajs.cn/suggest/type=11&key={keyword}'
            response = self.session.get(url, timeout=10)
            response.encoding = 'gbk'
            
            results = []
            
            match = re.search(r'="([^"]+)"', response.text)
            if match:
                items = match.group(1).split(';')
                for item in items[:10]:
                    parts = item.split(',')
                    if len(parts) >= 5:
                        code = parts[2]
                        name = parts[3]
                        market = parts[4]
                        
                        symbol = f'{market}{code}'
                        results.append({
                            'symbol': symbol,
                            'name': name,
                            'current': 0.0,
                            'change': 0.0
                        })
            
            return results
        except Exception as e:
            print(f"搜索股票失败: {e}")
            return []
    
    def get_stock_history_from_sina(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        try:
            clean_symbol = symbol.replace('sh', '').replace('sz', '')
            if symbol.startswith('sh'):
                market = 1
            else:
                market = 0
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            url = f'http://money.finance.sina.com.cn/quotes_service/api/jsonp_v2.php/var=/CN_MarketData.getKLineData?symbol={symbol}&scale=240&ma=no&datalen={days}'
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            
            history_data = []
            
            match = re.search(r'\[(.*?)\]', response.text, re.DOTALL)
            if match:
                json_str = f'[{match.group(1)}]'
                try:
                    import json
                    data = json.loads(json_str)
                    
                    for item in data:
                        history_data.append({
                            'date': item.get('day', ''),
                            'open': float(item.get('open', 0)),
                            'high': float(item.get('high', 0)),
                            'low': float(item.get('low', 0)),
                            'close': float(item.get('close', 0)),
                            'volume': float(item.get('volume', 0)),
                            'amount': float(item.get('close', 0)) * float(item.get('volume', 0))
                        })
                except Exception as e:
                    print(f"解析历史数据失败: {e}")
            
            return history_data
        except Exception as e:
            print(f"获取历史数据失败: {e}")
            return []
