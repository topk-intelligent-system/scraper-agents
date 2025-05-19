# Shopify Product Scraper

A Python-based scraper for extracting product data from Shopify stores using their public API.

## Features

- Efficient API-based data extraction
- Automatic pagination handling
- Product variant support
- JSON and CSV output formats
- Robust error handling
- Detailed logging

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

## Usage

Run the scraper with a store URL:

```bash
python main.py --store-url https://store-name.myshopify.com
```

### Output Files

The scraper generates two output files in the `data` directory:

1. `shopify_products.json`: Raw product data in JSON format
2. `shopify_products.csv`: Flattened product data with variants in CSV format

### CSV Format

The CSV file includes the following columns:
- store_domain
- product_id
- title
- handle
- vendor
- product_type
- created_at
- updated_at
- published_at
- tags
- body_html
- variant_id
- variant_title
- sku
- price
- compare_at_price
- available
- variant_created_at
- variant_updated_at
- image_src
- all_image_srcs

## Performance

The scraper is optimized for performance:
- Uses connection pooling
- Implements efficient pagination
- Handles compression automatically
- Processes data in memory efficiently

## Error Handling

The scraper includes comprehensive error handling:
- Connection errors
- API response validation
- Data processing errors
- File I/O errors

## Logging

Logs are stored in `data/scraper.log` with rotation enabled.

## License

[Your License Here]
