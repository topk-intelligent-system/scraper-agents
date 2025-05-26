from pymongo import MongoClient
from loguru import logger
import os
from dotenv import load_dotenv

def check_mongodb_data():
    try:
        # Load environment variables
        load_dotenv()
        
        # Get MongoDB URI from environment variable or use default
        mongo_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27018/')
        logger.info(f"Connecting to MongoDB at: {mongo_uri}")
        
        # Connect to MongoDB
        client = MongoClient(mongo_uri)
        db = client['shopify_scraper']
        collection = db['products']

        # Count total documents
        total_products = collection.count_documents({})
        logger.info(f"Total products in database: {total_products}")

        # Get unique store URLs
        store_urls = collection.distinct('store_url')
        logger.info(f"Stores in database: {store_urls}")

        # Get a sample product
        sample_product = collection.find_one()
        if sample_product:
            logger.info("Sample product fields:")
            for key in sample_product.keys():
                logger.info(f"- {key}")
            
            # Print some sample data
            logger.info("\nSample product data:")
            logger.info(f"Title: {sample_product.get('title', 'N/A')}")
            logger.info(f"Store URL: {sample_product.get('store_url', 'N/A')}")
            logger.info(f"Scraped at: {sample_product.get('scraped_at', 'N/A')}")
        else:
            logger.warning("No products found in the database")

        # Count products per store
        for store_url in store_urls:
            count = collection.count_documents({'store_url': store_url})
            logger.info(f"Products from {store_url}: {count}")

    except Exception as e:
        logger.error(f"Error checking MongoDB data: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    check_mongodb_data() 