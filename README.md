# Shopify Product Scraper

A Python-based solution for extracting product data from Shopify stores using the Storefront API with fallback to web scraping.

## Features

- 🛍️ **Primary Features**
  - GraphQL Storefront API support
  - Automatic fallback to Playwright-based scraping if API is unavailable
  - Pagination handling for complete product catalog extraction
  - Rate limiting and error handling
  - Configurable user agent and timeout settings

- 🧱 **Technical Features**
  - YAML-based configuration
  - Comprehensive logging
  - Automatic retries with exponential backoff
  - Consistent JSON output format

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd scraper-agents
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

## Configuration

1. Copy the example configuration file:
```bash
cp config.example.yml config.yml
```

2. Edit `config.yml` with your settings:
- Add your Shopify Storefront API access token (required for API access)
- Configure fallback behavior, rate limits, and other settings
- Customize user agent if needed

Example configuration:
```yaml
shopify:
  access_token: "your_access_token_here"
  rate_limit: 2
  max_retries: 3
  fallback_to_scraping: true

general:
  log_level: "INFO"
  timeout: 30
  user_agent: "Mozilla/5.0 ..."
```

## Usage

Run the scraper using the `main.py` script:

```bash
python main.py --store-url https://your-store.myshopify.com --config config.yml
```

### Output

The scraper creates a JSON file in the `data/` directory:
- `shopify_products.json`: Contains all extracted product data

Output format:
```json
{
  "title": "Product Name",
  "description": "Product Description",
  "price": "99.99",
  "currency": "USD",
  "availability": true,
  "average_rating": 4.5,
  "vendor": "Vendor Name",
  "category": "Category Name",
  "product_url": "https://store.com/product"
}
```

## Error Handling

- Automatic retries with exponential backoff for API requests
- Fallback to web scraping if API access fails (configurable)
- All errors are logged to `data/scraper.log`
- Detailed error messages and stack traces for debugging

## Development

The codebase is organized into:
- `base_agent.py`: Base scraping functionality
- `shopify_agent.py`: Shopify-specific implementation
- `main.py`: Command-line interface

## License

MIT License - feel free to use this code for any purpose.

## Disclaimer

Ensure you have permission to access and extract data from Shopify stores and comply with their terms of service and robots.txt directives.
