from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
import backoff
import time
from base_agent import BaseAgent

class ShopifyAgent(BaseAgent):
    def __init__(self, store_url: str, config_path: Optional[str] = None):
        """Initialize Shopify agent with store URL and optional config."""
        super().__init__(config_path)
        self.store_url = store_url.rstrip('/')
        self.browser = None
        self.page = None

    def connect(self) -> bool:
        """Initialize Playwright browser."""
        try:
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=True)
            
            # Set up browser context with user agent
            context = self.browser.new_context(
                user_agent=self.config.get('browser', {}).get(
                    'user_agent',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                ),
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = context.new_page()
            self.page.set_default_timeout(60000)  # 60 seconds timeout
            logger.info("Successfully initialized Playwright browser")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    def _wait_and_get_element_text(self, selector: str, default: str = '') -> str:
        """Safely wait for and extract text from an element."""
        try:
            element = self.page.wait_for_selector(selector, timeout=5000)
            return element.text_content().strip() if element else default
        except Exception:
            return default

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def _extract_product_details(self, product_url: str) -> Dict:
        """Extract detailed product information from product page."""
        try:
            logger.info(f"Extracting details from: {product_url}")
            self.page.goto(product_url, wait_until='domcontentloaded')
            time.sleep(2)  # Small delay to let dynamic content load
            
            # Try multiple common selectors for each field
            title = self._wait_and_get_element_text('h1, .product-title, .product__title')
            price = self._wait_and_get_element_text('.price, .product-price, [class*="price"]')
            description = self._wait_and_get_element_text('.product-description, .description, [class*="description"]')
            vendor = self._wait_and_get_element_text('.vendor, .product-vendor, [class*="vendor"]')
            
            # Get structured data if available
            structured_data = self.page.evaluate('''() => {
                const scripts = Array.from(document.querySelectorAll('script[type="application/ld+json"]'));
                for (const script of scripts) {
                    try {
                        const data = JSON.parse(script.textContent);
                        if (data["@type"] === "Product") {
                            return data;
                        }
                    } catch (e) {}
                }
                return null;
            }''')
            
            product_data = {
                'title': title,
                'description': description,
                'price': price,
                'vendor': vendor,
                'product_url': product_url,
                'availability': True,
                'currency': 'USD'
            }
            
            # Enhance with structured data if available
            if structured_data:
                product_data.update({
                    'description': structured_data.get('description', product_data['description']),
                    'category': structured_data.get('category', ''),
                    'average_rating': float(structured_data.get('aggregateRating', {}).get('ratingValue', 0)),
                })
            
            logger.info(f"Successfully extracted data for product: {title}")
            return product_data
        except Exception as e:
            logger.error(f"Error extracting product details from {product_url}: {str(e)}")
            return None

    def _find_product_links(self) -> List[str]:
        """Find product links using multiple strategies."""
        try:
            # Try to find a "View All" or similar link first
            view_all_links = self.page.evaluate('''() => {
                const links = Array.from(document.querySelectorAll('a'));
                return links
                    .filter(link => {
                        const text = link.textContent.toLowerCase();
                        return text.includes('view all') || 
                               text.includes('all products') ||
                               text.includes('shop all');
                    })
                    .map(link => link.href);
            }''')
            
            if view_all_links:
                logger.info(f"Found 'View All' link: {view_all_links[0]}")
                self.page.goto(view_all_links[0], wait_until='domcontentloaded')
                time.sleep(2)
            
            # Find all product links
            product_links = self.page.evaluate('''() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(link => link.href)
                    .filter(href => href.includes('/products/'))
                    .filter((href, index, self) => self.indexOf(href) === index);
            }''')
            
            return product_links
        except Exception as e:
            logger.error(f"Error finding product links: {str(e)}")
            return []

    @backoff.on_exception(backoff.expo, Exception, max_tries=3)
    def crawl(self) -> List[Dict]:
        """Crawl products using Playwright."""
        all_products = []
        try:
            # Try different entry points
            entry_points = [
                f"{self.store_url}/collections/all",
                f"{self.store_url}/collections/best-sellers",
                f"{self.store_url}/products"
            ]
            
            for entry_point in entry_points:
                try:
                    logger.info(f"Trying entry point: {entry_point}")
                    self.page.goto(entry_point, wait_until='domcontentloaded')
                    time.sleep(2)
                    
                    product_links = self._find_product_links()
                    if product_links:
                        logger.info(f"Found {len(product_links)} product links")
                        break
                except Exception as e:
                    logger.warning(f"Failed to access {entry_point}: {str(e)}")
                    continue
            
            # Limit the number of products to scrape
            max_products = min(len(product_links), self.config.get('scraping', {}).get('max_products', 10))
            product_links = product_links[:max_products]
            
            # Extract details from each product page
            for product_url in product_links:
                try:
                    product_data = self._extract_product_details(product_url)
                    if product_data:
                        all_products.append(product_data)
                    # Add delay between requests
                    time.sleep(self.config.get('scraping', {}).get('wait_time', 2))
                except Exception as e:
                    logger.error(f"Failed to extract product data from {product_url}: {str(e)}")
                    continue
                
            logger.info(f"Successfully scraped {len(all_products)} products")
            
        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
        finally:
            if self.browser:
                self.browser.close()
        
        return all_products

    def extract_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Clean and normalize product data."""
        normalized_data = []
        
        for product in raw_data:
            try:
                # Clean up price string
                price = product.get('price', '')
                if price:
                    # Remove currency symbols and normalize format
                    price = ''.join(c for c in price if c.isdigit() or c in '.,')
                    try:
                        price = float(price.replace(',', '.'))
                    except:
                        price = ''
                
                normalized_product = {
                    'title': product.get('title', '').strip(),
                    'description': product.get('description', '').strip(),
                    'price': str(price) if price else '',
                    'currency': product.get('currency', 'USD'),
                    'availability': product.get('availability', True),
                    'average_rating': product.get('average_rating', None),
                    'vendor': product.get('vendor', '').strip(),
                    'category': product.get('category', '').strip(),
                    'product_url': product.get('product_url', '')
                }
                normalized_data.append(normalized_product)
            except Exception as e:
                logger.error(f"Error normalizing product data: {str(e)}")
                continue
        
        return normalized_data 