import argparse
import sys
from loguru import logger
from shopify_api_agent import ShopifyAPIAgent
from pathlib import Path

def main():
    try:
        parser = argparse.ArgumentParser(description='Shopify Product Scraper')
        parser.add_argument('--store-url', required=True, help='URL of the Shopify store to scrape')
        parser.add_argument('--config', help='Path to configuration file')
        args = parser.parse_args()

        # Configure logger
        logger.remove()  # Remove default handler
        logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
        logger.add("data/shopify_scraper.log", rotation="1 day", retention="7 days")

        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        logger.info(f"Starting Shopify API scraper for {args.store_url}")
        
        # Initialize and run the API agent
        agent = ShopifyAPIAgent(args.store_url, args.config)
        
        # Connect to the store
        if not agent.connect():
            logger.error("Failed to connect to the store. Please check the URL and try again.")
            sys.exit(1)
            
        # Run the scraper
        try:
            agent.run("data/shopify_products.json")
            logger.info("Scraping completed successfully")
        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("Scraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 