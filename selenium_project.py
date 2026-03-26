import time
from selenium import webdriver
from selenium.webdriver.common.by import By

CURRENCY_RATES = {
    '₹': 0.016,
    '$': 1.36,
    'SGD': 1.0
}

def get_price_in_sgd(price_str):
    for symbol, rate in CURRENCY_RATES.items():
        if symbol in price_str:
            price = float(''.join(filter(str.isdigit, price_str)))
            return price * rate
    return 0.0

options = webdriver.ChromeOptions()
options.headless = False

driver = webdriver.Chrome(options=options)
driver.get('https://www.amazon.in/ref=nav_logo')

for _ in range(5):
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

items = driver.find_elements(By.CSS_SELECTOR, 'div.s-main-slot div.s-result-item')
total_sgd = 0.0

for item in items:
    try:
        title = item.find_element(By.CSS_SELECTOR, 'h2 a span').text
        price_whole = item.find_element(By.CSS_SELECTOR, 'span.a-price-whole').text
        price_symbol = item.find_element(By.CSS_SELECTOR, 'span.a-price-symbol').text
        price = f"{price_symbol}{price_whole}"
        converted = get_price_in_sgd(price)
        print(f"Item: {title}\nOriginal: {price}\nConverted: SGD {converted:.2f}\n")
        total_sgd += converted
    except Exception:
        continue


print(f"Total value in SGD: {total_sgd:.2f}")
driver.quit()