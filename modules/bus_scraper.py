import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
from datetime import datetime

def find_chrome_binary():
    paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.join(os.environ.get('LOCALAPPDATA', ''), r"Google\Chrome\Application\chrome.exe")
    ]
    for path in paths:
        if os.path.exists(path): return path
    return None

def scrape_redbus(source, dest, date):
    print(f"🔄 [Scraper] Extracting LIVE prices: {source} to {dest}...")
    chrome_path = find_chrome_binary()
    if not chrome_path: return []

    options = uc.ChromeOptions()
    options.binary_location = chrome_path
    options.add_argument('--headless')
    
    driver = None
    scraped_data = []
    
    try:
        driver = uc.Chrome(options=options, version_main=144) 
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d-%b-%Y')
        except:
            formatted_date = date

        url = f"https://www.redbus.in/bus-tickets/{source.lower()}-to-{dest.lower()}?date={formatted_date}"
        driver.get(url)
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".fare, .seat-fare")))
        except: pass

        bus_items = driver.find_elements(By.CSS_SELECTOR, ".bus-item, .clearfix.row-one")
        
        for bus in bus_items[:5]: 
            try:
                operator = bus.find_element(By.CSS_SELECTOR, ".travels, .makeFlex hspan").text
                bus_type = bus.find_element(By.CSS_SELECTOR, ".bus-type").text
                depart = bus.find_element(By.CSS_SELECTOR, ".dp-time").text
                price_text = bus.find_element(By.CSS_SELECTOR, ".fare span, .seat-fare").text
                price = price_text.replace('INR', '').replace('₹', '').replace(',', '').strip()
                
                scraped_data.append({
                    "operator": operator + " (LIVE)", "bus_type": bus_type,
                    "depart": depart, "duration": "N/A", "price": price,
                    "rating": "4.2", "punctuality": 80
                })
            except: continue
                
        print(f"✅ [Scraper] Extracted {len(scraped_data)} LIVE bus prices.")
    except Exception as e:
        print(f"❌ [Scraper] Live extraction failed: {e}")
    finally:
        if driver:
            try: driver.quit()
            except: pass
                
    return scraped_data