import requests
import json
import csv
import time
import logging
import os
import brotli
from datetime import datetime
from urllib.parse import urlparse, urlunparse
from typing import List, Dict, Optional, Any
from base_agent import BaseAgent
from loguru import logger
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class ShopifyAPIAgent(BaseAgent):
    def __init__(self, store_url: str, api_key: str = None, api_password: str = None):
        """Initialize Shopify API agent with store URL and optional API credentials.
        
        Args:
            store_url: The URL of the Shopify store.
            api_key: The Shopify API key (optional, falls back to environment variable).
            api_password: The Shopify API password (optional, falls back to environment variable).
        """
        super().__init__()
        self.store_url = store_url.rstrip('/')
        self.base_url = f"{self.store_url}/products.json"
        
        # Set API credentials, with fallback to environment variables
        self.api_key = api_key or os.getenv("SHOPIFY_API_KEY")
        self.api_password = api_password or os.getenv("SHOPIFY_API_PASSWORD")
        
        self.mongo_client = None
        self.db = None
        self.products_collection = None
        self.connect_to_mongodb()
        self._should_stop = False
        self.session = requests.Session()

    def connect_to_mongodb(self):
        """Connect to MongoDB and initialize collections."""
        try:
            # Get MongoDB connection string from environment variable
            mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
            logger.info(f"Connecting to MongoDB at: {mongo_uri}")
            
            self.mongo_client = MongoClient(mongo_uri)
            # Test the connection
            self.mongo_client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Initialize database and collection
            self.db = self.mongo_client['shopify_scraper']
            self.products_collection = self.db['products']
            
            # Create indexes for better query performance
            self.products_collection.create_index('id', unique=True)
            self.products_collection.create_index('handle')
            self.products_collection.create_index('created_at')
            self.products_collection.create_index('store_url')
            
            # Log the current collection stats
            try:
                stats = self.db.command("collstats", "products")
                logger.info(f"Current collection stats: {stats}")
            except Exception as e:
                logger.warning(f"Could not get collection stats: {e}")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error initializing MongoDB: {e}")
            raise

    def store_product_in_mongodb(self, product: Dict[str, Any]) -> bool:
        """Store a single product in MongoDB."""
        try:
            # Add timestamp for when the product was scraped
            product['scraped_at'] = datetime.utcnow()
            product['store_url'] = self.store_url
            
            # Use upsert to update existing products or insert new ones
            result = self.products_collection.update_one(
                {'id': product['id'], 'store_url': self.store_url},
                {'$set': product},
                upsert=True
            )
            
            if result.upserted_id:
                logger.debug(f"Inserted new product with ID: {product['id']}")
            else:
                logger.debug(f"Updated existing product with ID: {product['id']}")
            
            return True
        except Exception as e:
            logger.error(f"Error storing product in MongoDB: {e}")
            return False

    def store_products_in_mongodb(self, products: List[Dict[str, Any]]) -> int:
        """Store multiple products in MongoDB."""
        success_count = 0
        for product in products:
            if self.store_product_in_mongodb(product):
                success_count += 1
        return success_count

    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a product from MongoDB by ID."""
        try:
            return self.products_collection.find_one({'id': product_id, 'store_url': self.store_url})
        except Exception as e:
            logger.error(f"Error retrieving product from MongoDB: {e}")
            return None

    def get_all_products(self, limit: int = 0) -> List[Dict[str, Any]]:
        """Retrieve all products from MongoDB for this store."""
        try:
            cursor = self.products_collection.find({'store_url': self.store_url})
            if limit > 0:
                cursor = cursor.limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error retrieving products from MongoDB: {e}")
            return []

    def close_mongodb_connection(self):
        """Close the MongoDB connection."""
        if self.mongo_client:
            self.mongo_client.close()
            logger.info("MongoDB connection closed")

    def scrape_products(self, limit: Optional[int] = None) -> List[Dict]:
        """Scrape products from the Shopify store."""
        products = []
        page = 1
        has_next_page = True
        count = 0

        while has_next_page and (limit is None or count < limit):
            try:
                # Construct the URL with pagination
                url = f"{self.base_url}?page={page}&limit=250"  # Maximum allowed by Shopify

                # Make the API request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive'
                }
                
                # Add authentication if credentials are provided
                auth = None
                if self.api_key and self.api_password:
                    auth = (self.api_key, self.api_password)
                    logger.info(f"Using API authentication for request to {url}")

                response = self.session.get(url, headers=headers, auth=auth)
                response.raise_for_status()
                data = response.json()

                # Extract products and store in MongoDB
                batch_products = data.get('products', [])
                if batch_products:
                    self.store_products_in_mongodb(batch_products)
                    products.extend(batch_products)
                    count += len(batch_products)
                    logger.info(f"Scraped {count} products so far")
                    
                    if len(batch_products) < 250:  # If we got less than the limit, we're done
                        has_next_page = False
                    else:
                        page += 1
                else:
                    has_next_page = False

                # Respect rate limits
                time.sleep(1.5)  # Be polite and avoid rate limiting

            except requests.exceptions.RequestException as e:
                logger.error(f"Error scraping products: {e}")
                break

        logger.info(f"Successfully scraped {len(products)} products")
        return products

    def __del__(self):
        """Cleanup when the object is destroyed."""
        self.close_mongodb_connection()

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