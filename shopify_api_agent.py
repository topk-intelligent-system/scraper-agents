import requests
import json
import csv
import time
import logging
import os
import brotli
from urllib.parse import urlparse, urlunparse
from typing import List, Dict, Optional
from base_agent import BaseAgent
from loguru import logger

class ShopifyAPIAgent(BaseAgent):
    def __init__(self, store_url: str, config_path: Optional[str] = None):
        """Initialize Shopify API agent with store URL and optional config."""
        super().__init__(config_path)
        self.store_url = store_url.rstrip('/')
        self._should_stop = False
        self.session = requests.Session()

    def connect(self) -> bool:
        """Initialize connection to the Shopify store."""
        try:
            # Test the connection by making a simple request
            url = self.construct_url(self.store_url)
            if not url:
                logger.error("Failed to construct URL")
                return False
                
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive'
            }
            
            logger.info(f"Attempting to connect to {url}")
            response = self.session.get(url, timeout=30, headers=headers)
            
            # Log response details for debugging
            logger.info(f"Response status code: {response.status_code}")
            
            # Check if we got a successful response
            if response.status_code != 200:
                logger.error(f"Received non-200 status code: {response.status_code}")
                logger.error(f"Response content: {response.text[:500]}...")
                return False
            
            # Try to parse the response as JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {str(e)}")
                logger.error(f"Response content: {response.text[:500]}...")
                return False
            
            # Verify the response structure
            if not isinstance(data, dict):
                logger.error(f"Expected JSON object, got {type(data)}")
                return False
                
            if 'products' not in data:
                logger.error("Response does not contain 'products' key")
                logger.error(f"Response keys: {list(data.keys())}")
                return False
            
            logger.info("Successfully connected to Shopify store")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Shopify store: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during connection: {str(e)}")
            return False

    def construct_url(self, domain: str) -> Optional[str]:
        """Constructs the full https://domain/products.json URL."""
        try:
            # Remove any protocol prefix if present
            domain = domain.replace('https://', '').replace('http://', '').rstrip('/')
            
            # Construct the full URL
            url = f"https://{domain}/products.json"
            logger.info(f"Constructed URL: {url}")
            return url
            
        except Exception as e:
            logger.error(f"Error constructing URL: {str(e)}")
            return None

    def fetch_products(self, url: str) -> List[Dict]:
        """Fetches products from a single store's /products.json endpoint."""
        products = []
        page = 1
        limit = 250  # Max limit for Shopify's /products.json
        
        while True:
            if self._should_stop:
                break
                
            paginated_url = f"{url}?limit={limit}&page={page}"
            logger.info(f"Fetching: {paginated_url}")
            
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
                
                response = self.session.get(paginated_url, timeout=30, headers=headers)
                response.raise_for_status()

                data = response.json()
                if not isinstance(data, dict) or 'products' not in data:
                    logger.error(f"Invalid response format from {paginated_url}")
                    break

                if data["products"]:
                    products.extend(data["products"])
                    logger.info(f"Fetched {len(data['products'])} products from page {page}. Total so far: {len(products)}")
                    
                    if len(data["products"]) < limit:
                        break
                    page += 1
                else:
                    logger.info(f"No more products found on page {page}")
                    break

                time.sleep(1.5)  # Be polite and avoid rate limiting

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching {paginated_url}: {e}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Error decoding JSON from {paginated_url}: {e}")
                logger.error(f"Response text: {response.text[:500]}...")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred for {paginated_url}: {e}")
                break
                
        return products

    def flatten_data(self, all_products_data: List[Dict], store_domain: str) -> List[Dict]:
        """Flattens the product and variant data for CSV writing."""
        flattened_rows = []
        
        for product in all_products_data:
            try:
                product_id = product.get('id')
                first_image_src = product.get('images', [{}])[0].get('src') if product.get('images') else None
                all_image_srcs = '|'.join([img.get('src', '') for img in product.get('images', []) if img.get('src')])

                if not product.get('variants'):
                    row = {
                        'store_domain': store_domain,
                        'product_id': product_id,
                        'title': product.get('title', ''),
                        'handle': product.get('handle', ''),
                        'vendor': product.get('vendor', ''),
                        'product_type': product.get('product_type', ''),
                        'created_at': product.get('created_at', ''),
                        'updated_at': product.get('updated_at', ''),
                        'published_at': product.get('published_at', ''),
                        'tags': ', '.join(product.get('tags', [])),
                        'body_html': product.get('body_html', ''),
                        'variant_id': None,
                        'variant_title': None,
                        'sku': None,
                        'price': None,
                        'compare_at_price': None,
                        'available': None,
                        'variant_created_at': None,
                        'variant_updated_at': None,
                        'image_src': first_image_src,
                        'all_image_srcs': all_image_srcs,
                    }
                    flattened_rows.append(row)
                else:
                    for variant in product.get('variants', []):
                        row = {
                            'store_domain': store_domain,
                            'product_id': product_id,
                            'title': product.get('title', ''),
                            'handle': product.get('handle', ''),
                            'vendor': product.get('vendor', ''),
                            'product_type': product.get('product_type', ''),
                            'created_at': product.get('created_at', ''),
                            'updated_at': product.get('updated_at', ''),
                            'published_at': product.get('published_at', ''),
                            'tags': ', '.join(product.get('tags', [])),
                            'body_html': product.get('body_html', ''),
                            'variant_id': variant.get('id'),
                            'variant_title': variant.get('title', ''),
                            'sku': variant.get('sku', ''),
                            'price': variant.get('price', ''),
                            'compare_at_price': variant.get('compare_at_price', ''),
                            'available': variant.get('available', False),
                            'variant_created_at': variant.get('created_at', ''),
                            'variant_updated_at': variant.get('updated_at', ''),
                            'image_src': first_image_src,
                            'all_image_srcs': all_image_srcs,
                        }
                        flattened_rows.append(row)
            except Exception as e:
                logger.error(f"Error processing product {product.get('id', 'unknown')}: {str(e)}")
                continue
                    
        return flattened_rows

    def save_to_csv(self, data: List[Dict], filename: str, headers: List[str]) -> None:
        """Saves the flattened data to a CSV file."""
        try:
            # Ensure the data directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            file_exists = os.path.isfile(filename)
            with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                if not file_exists or os.path.getsize(filename) == 0:
                    writer.writeheader()
                writer.writerows(data)
            logger.info(f"Successfully appended {len(data)} rows to {filename}")
        except IOError as e:
            logger.error(f"Error writing to CSV file {filename}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during CSV writing: {e}")

    def crawl(self) -> List[Dict]:
        """Crawl products using the Shopify API endpoint."""
        all_products = []
        
        try:
            url = self.construct_url(self.store_url)
            if not url:
                logger.error("Failed to construct URL for crawling")
                return []

            products_data = self.fetch_products(url)
            
            if products_data:
                logger.info(f"Fetched a total of {len(products_data)} product entries for {self.store_url}")
                all_products.extend(products_data)
            else:
                logger.warning(f"No products retrieved for {self.store_url}")
                
        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
            
        return all_products

    def extract_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Process and format the extracted data."""
        try:
            if not raw_data:
                logger.warning("No raw data to process")
                return []
                
            # Get the domain from the store URL
            domain = urlparse(self.store_url).netloc
            
            # Flatten the data
            flattened_data = self.flatten_data(raw_data, domain)
            
            if not flattened_data:
                logger.warning("No data was flattened")
                return raw_data
            
            # Define CSV headers
            headers = [
                'store_domain', 'product_id', 'title', 'handle', 'vendor',
                'product_type', 'created_at', 'updated_at', 'published_at',
                'tags', 'body_html', 'variant_id', 'variant_title', 'sku',
                'price', 'compare_at_price', 'available', 'variant_created_at',
                'variant_updated_at', 'image_src', 'all_image_srcs'
            ]
            
            # Save to CSV
            self.save_to_csv(flattened_data, 'data/shopify_products.csv', headers)
            
            # Return the raw data as a list
            return raw_data
            
        except Exception as e:
            logger.error(f"Error processing extracted data: {str(e)}")
            return [] 