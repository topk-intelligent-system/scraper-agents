import argparse
from pathlib import Path
from typing import Optional
from loguru import logger
from shopify_agent import ShopifyAgent

def run_shopify_agent(store_url: str, config_path: Optional[str] = None) -> None:
    """Run the Shopify agent on a specific store."""
    agent = ShopifyAgent(store_url, config_path)
    agent.run("shopify_products.json")

def main():
    parser = argparse.ArgumentParser(description='Shopify Product Scraper')
    parser.add_argument('--store-url', required=True, 
                      help='URL of the Shopify store to scrape')
    parser.add_argument('--config', help='Path to config file (optional)')
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    try:
        logger.info(f"Starting Shopify scraper for {args.store_url}")
        run_shopify_agent(args.store_url, args.config)
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}")
        raise

if __name__ == "__main__":
    main() 