import requests
import time
import json
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Product:
    title: str
    platform: str
    price: float
    currency: str = "USD"
    sales_count: Optional[int] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller_info: Optional[str] = None
    product_url: Optional[str] = None
    image_urls: List[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = None

class EcommerceScraper:
    def __init__(self):
        self.setup_selenium()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def setup_selenium(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def random_delay(self, min_delay=1, max_delay=3):
        time.sleep(random.uniform(min_delay, max_delay))

class EbayScraper(EcommerceScraper):
    def search_products(self, keywords: str, category: str = "", limit: int = 50) -> List[Product]:
        products = []
        base_url = "https://www.ebay.com/sch/i.html"
        
        params = {
            '_nkw': keywords,
            '_sop': 12,  # Sort by best match
            'LH_Sold': 1,  # Sold listings
            'LH_Complete': 1
        }
        
        try:
            response = self.session.get(base_url, params=params)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            items = soup.find_all('div', class_='s-item__wrapper')[:limit]
            
            for item in items:
                try:
                    title_elem = item.find('h3', class_='s-item__title')
                    price_elem = item.find('span', class_='s-item__price')
                    link_elem = item.find('a', class_='s-item__link')
                    
                    if title_elem and price_elem:
                        title = title_elem.get_text().strip()
                        price_text = price_elem.get_text().strip()
                        price = self.extract_price(price_text)
                        url = link_elem.get('href') if link_elem else ""
                        
                        # Get additional details
                        sold_elem = item.find('span', class_='s-item__quantity-sold')
                        sales_count = self.extract_sales_count(sold_elem.get_text() if sold_elem else "")
                        
                        product = Product(
                            title=title,
                            platform="eBay",
                            price=price,
                            sales_count=sales_count,
                            product_url=url,
                            category=category
                        )
                        products.append(product)
                        
                except Exception as e:
                    continue
                    
                self.random_delay(0.5, 1.5)
                
        except Exception as e:
            print(f"Error scraping eBay: {e}")
            
        return products
    
    def extract_price(self, price_text: str) -> float:
        import re
        price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
        return float(price_match.group()) if price_match else 0.0
    
    def extract_sales_count(self, text: str) -> int:
        import re
        match = re.search(r'(\d+)\s*sold', text.lower())
        return int(match.group(1)) if match else 0

class EtsyScraper(EcommerceScraper):
    def search_products(self, keywords: str, category: str = "", limit: int = 50) -> List[Product]:
        products = []
        search_url = f"https://www.etsy.com/search?q={keywords.replace(' ', '%20')}"
        
        try:
            self.driver.get(search_url)
            self.random_delay(2, 4)
            
            # Wait for products to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="listing-card"]'))
            )
            
            listings = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id="listing-card"]')[:limit]
            
            for listing in listings:
                try:
                    title_elem = listing.find_element(By.CSS_SELECTOR, 'h3[data-test-id="listing-card-title"] a')
                    price_elem = listing.find_element(By.CSS_SELECTOR, '[data-test-id="listing-card-price"]')
                    
                    title = title_elem.get_attribute('title')
                    price_text = price_elem.text
                    url = title_elem.get_attribute('href')
                    price = self.extract_price(price_text)
                    
                    # Try to get rating and reviews
                    rating = None
                    review_count = None
                    try:
                        rating_elem = listing.find_element(By.CSS_SELECTOR, '[data-test-id="listing-card-rating"]')
                        rating_text = rating_elem.get_attribute('aria-label')
                        rating = float(rating_text.split()[0]) if rating_text else None
                    except:
                        pass
                    
                    product = Product(
                        title=title,
                        platform="Etsy",
                        price=price,
                        rating=rating,
                        review_count=review_count,
                        product_url=url,
                        category=category
                    )
                    products.append(product)
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Error scraping Etsy: {e}")
            
        return products

class AmazonAPIScraper:
    """
    Note: This uses Amazon's affiliate API approach
    For real implementation, you'd need Amazon API credentials
    """
    def __init__(self, access_key: str = "", secret_key: str = "", associate_tag: str = ""):
        self.access_key = access_key
        self.secret_key = secret_key
        self.associate_tag = associate_tag
    
    def search_products(self, keywords: str, category: str = "", limit: int = 50) -> List[Product]:
        # Placeholder for Amazon Product Advertising API integration
        # You would implement the actual API calls here
        products = []
        
        # For demonstration, return mock data structure
        # In real implementation, replace with actual API calls
        mock_product = Product(
            title=f"Sample Amazon Product for {keywords}",
            platform="Amazon",
            price=29.99,
            rating=4.5,
            review_count=1250,
            category=category
        )
        
        return [mock_product]  # Replace with actual API results

class ShopifyScraper(EcommerceScraper):
    def search_trending_stores(self, niche: str = "", limit: int = 20) -> List[Dict]:
        """
        Scrape trending Shopify stores using various discovery methods
        """
        stores = []
        
        # Method 1: Use Shopify's built-in endpoints
        try:
            # Search for .myshopify.com domains
            search_queries = [
                f"site:myshopify.com {niche}",
                f"{niche} store site:myshopify.com"
            ]
            
            # This would typically use Google Search API or similar
            # For now, return sample data structure
            sample_store = {
                'store_name': f'Sample {niche} Store',
                'url': 'https://example.myshopify.com',
                'niche': niche,
                'estimated_revenue': 'Unknown'
            }
            stores.append(sample_store)
            
        except Exception as e:
            print(f"Error finding Shopify stores: {e}")
            
        return stores
    
    def analyze_store_products(self, store_url: str) -> List[Product]:
        """
        Analyze products from a specific Shopify store
        """
        products = []
        
        try:
            # Try to access the store's product JSON endpoint
            products_url = f"{store_url.rstrip('/')}/products.json"
            response = self.session.get(products_url)
            
            if response.status_code == 200:
                data = response.json()
                
                for product_data in data.get('products', []):
                    title = product_data.get('title', '')
                    price = 0.0
                    
                    # Get the first variant's price
                    variants = product_data.get('variants', [])
                    if variants:
                        price = float(variants[0].get('price', 0))
                    
                    product = Product(
                        title=title,
                        platform="Shopify",
                        price=price,
                        product_url=f"{store_url}/products/{product_data.get('handle', '')}",
                        description=product_data.get('body_html', ''),
                        tags=product_data.get('tags', [])
                    )
                    products.append(product)
                    
        except Exception as e:
            print(f"Error analyzing Shopify store {store_url}: {e}")
            
        return products

class ProductDataManager:
    def __init__(self):
        self.scrapers = {
            'ebay': EbayScraper(),
            'etsy': EtsyScraper(),
            'amazon': AmazonAPIScraper(),
            'shopify': ShopifyScraper()
        }
    
    def search_all_platforms(self, keywords: str, category: str = "", limit_per_platform: int = 25) -> Dict[str, List[Product]]:
        """
        Search across all platforms and return organized results
        """
        all_results = {}
        
        for platform_name, scraper in self.scrapers.items():
            try:
                print(f"Searching {platform_name} for: {keywords}")
                
                if platform_name == "shopify":
                    # Special handling for Shopify
                    stores = scraper.search_trending_stores(keywords, limit=5)
                    products = []
                    for store in stores[:3]:  # Analyze top 3 stores
                        store_products = scraper.analyze_store_products(store['url'])
                        products.extend(store_products)
                else:
                    products = scraper.search_products(keywords, category, limit_per_platform)
                
                all_results[platform_name] = products
                print(f"Found {len(products)} products on {platform_name}")
                
            except Exception as e:
                print(f"Error searching {platform_name}: {e}")
                all_results[platform_name] = []
        
        return all_results
    
    def cleanup(self):
        """Clean up selenium drivers"""
        for scraper in self.scrapers.values():
            if hasattr(scraper, 'driver'):
                scraper.driver.quit()

# Usage example
if __name__ == "__main__":
    manager = ProductDataManager()
    
    try:
        # Search for trending products
        results = manager.search_all_platforms(
            keywords="wireless headphones",
            category="Electronics",
            limit_per_platform=20
        )
        
        # Print results summary
        for platform, products in results.items():
            print(f"\n{platform.upper()}: {len(products)} products found")
            for product in products[:3]:  # Show first 3
                print(f"  - {product.title[:50]}... | ${product.price}")
                
    finally:
        manager.cleanup()