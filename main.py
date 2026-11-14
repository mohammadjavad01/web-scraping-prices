import sqlite3
import time 
from requests import get 
from bs4 import BeautifulSoup

# Constants
URL = 'https://www.tgju.org/'
HEADERS = {
    'User-Agent' : (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36'
    )
}
DB_NAME = 'data.db'  # database name
REQUEST_TIMEFRAME = 10 * 60  # 10 minutes


def get_html_page() -> str:
    ''''گرفتن متن html از صفحه مورد نظر و نمایش خطا در صورت وجود'''
    try:
        response = get(url= URL, headers= HEADERS, timeout= 10)
        if response.status_code == 200: 
            return response.text
    except Exception as e:  
        print(f'Network Error:\n{e}')
        return None


def extract_currencies(soup: BeautifulSoup) -> dict:
    '''استخراج ارز ها از صفحه'''   
    try:
        tbody = soup.select_one(
            '#main div:nth-child(5) div.home-fs-row div.index-tabs.index-tabs-line div '
            'div.index-tabs-content.currency-overview-content.active.currency-min-font div.index-tabs-data.bootstrap-fix '
            'div div.col-12.col-lg-12.col-xl-6.index-tabs-data-col-1 table tbody'
        )
        trs = tbody.find_all('tr')
        
        extracted_data = {}
        for tr in trs: 
            currency_name = tr.select_one('th').get_text(strip= True)
            currency_price = tr.select_one('td.market-price').get_text(strip= True)
            extracted_data[currency_name] = currency_price   
        return extracted_data
    
    except Exception as e: 
        print(f'Error extracting currencies: {e}')
        return {}
    

def extract_digital_currencies(soup: BeautifulSoup) -> dict[ str : dict ]:
    '''استخراج رمز ارز ها از صفحه'''
    try:
        tbody = soup.select_one(
            '#main div.home-crypto-wrapper div div div.index-tabs-content.crypto-overview-content.active '
            'div.index-tabs-data.crypto-tabs-mobile2 table tbody'
        )
        trs = tbody.find_all('tr')

        extracted_data = {}
        for tr in trs: 
            dc_name = tr.find(name= 'th', attrs={'onclick': "window.location='profile/' + this.parentElement.getAttribute('data-market-nameslug').replace('disabled_', '');"}).get_text(strip=True)
            price_in_rials = tr.select_one('td.market-price-irr').get_text(strip= True)
            price_in_dollar = tr.select_one('td.market-price').get_text(strip= True)
            extracted_data[dc_name] = {'price_in_rials': price_in_rials, 'price_in_dollar': price_in_dollar}
        return extracted_data
    
    except Exception as e: 
        print(f'Error extracting digital currencies: {e}')   
        return {}


def extract_gold(soup: BeautifulSoup) -> dict: 
    '''استخراج طلا از صفحه'''
    try:
        tbody = soup.select_one('#main div:nth-child(5) div:nth-child(3) div:nth-child(2) table tbody')
        trs = tbody.find_all('tr')

        extracted_data = {}
        for tr in trs: 
            gold_name = tr.find('th').get_text(strip= True)
            gold_price = tr.select_one('td.nf').get_text(strip= True)
            extracted_data[gold_name] = gold_price
        return extracted_data
    
    except Exception as e: 
        print(f'Error extracting gold: {e}')
        return {}


def create_database() -> None: 
    '''ایجاد پایگاه داده و جدول های آن در صورت عدم وجود'''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    # table for currencies
    cur.execute('''
        CREATE TABLE IF NOT EXISTS currencies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price TEXT
        )
    ''')    
    # table for digital currencies
    cur.execute('''
        CREATE TABLE IF NOT EXISTS digital_currencies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price_in_rials TEXT,
            price_in_dollar TEXT
        )
    ''')
    # table for gold
    cur.execute('''
        CREATE TABLE IF NOT EXISTS gold(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            price TEXT
        )
    ''')
    conn.commit()
    conn.close()


def save_to_database(currencies: dict, digital_currencies: dict, gold: dict) -> None: 
    '''ذخیره کردن داده های جدید در پایگاه داده با استفاده از UPSERT'''
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        # Adding (currencies)
        for name, price in currencies.items():
            cur.execute('''
                INSERT INTO currencies (name, price)
                VALUES (?, ?)
                ON CONFLICT (name) DO UPDATE SET 
                    price = excluded.price
            ''', (name, price))

        # Adding (digital currencies)
        for name, values in digital_currencies.items():
            cur.execute('''
                INSERT INTO digital_currencies (name, price_in_rials, price_in_dollar)
                VALUES (?, ?, ?)
                ON CONFLICT (name) DO UPDATE SET 
                    price_in_rials = excluded.price_in_rials,
                    price_in_dollar = excluded.price_in_dollar
            ''', (name, values['price_in_rials'], values['price_in_dollar']))
        
        # Adding (gold)
        for name, price in gold.items(): 
            cur.execute('''
                INSERT INTO gold (name, price)
                VALUES (?, ?)
                ON CONFLICT (name) DO UPDATE SET
                    price = excluded.price
            ''', (name, price))

        conn.commit()

    except Exception as e:
        print(f"Database Error: {e}")
        conn.rollback() 
    finally:
        conn.close()


def main() -> None:
    create_database()
    while True: 
        html_text = get_html_page()

        if html_text:
            soup = BeautifulSoup(html_text, 'html.parser')
            currencies = extract_currencies(soup)
            digital_currencies = extract_digital_currencies(soup)
            gold = extract_gold(soup)

            save_to_database(currencies, digital_currencies, gold)
            print(f'''New data has been saved. Date: {time.strftime('%Y-%m-%d %H:%M:%S')}''')

        time.sleep(REQUEST_TIMEFRAME) # 10 minutes


if __name__ == "__main__": 
    main()
