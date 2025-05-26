import os
import argparse
from dotenv import load_dotenv
from loguru import logger
from shopify_api_agent import ShopifyAPIAgent

def main():
    # Load environment variables
    load_dotenv()
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Scrape products from a Shopify store')
    parser.add_argument('store_url', help='URL of the Shopify store to scrape (e.g., https://store-name.myshopify.com)')
    parser.add_argument('--limit', type=int, help='Limit the number of products to scrape')
    args = parser.parse_args()
    
    try:
        # Initialize the agent
        agent = ShopifyAPIAgent(store_url=args.store_url)
        
        # Scrape products (they will be automatically stored in MongoDB)
        products = agent.scrape_products(limit=args.limit)
        
        # Print summary
        logger.info(f"Successfully scraped and stored {len(products)} products in MongoDB")
        
        # Example of retrieving products from MongoDB
        stored_products = agent.get_all_products(limit=5)
        logger.info(f"Retrieved {len(stored_products)} products from MongoDB")
        
    except Exception as e:
        logger.error(f"An error occurred: {e}")
    finally:
        # Cleanup
        if 'agent' in locals():
            agent.close_mongodb_connection()

if __name__ == "__main__":
    main() 