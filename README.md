# Shopify Product Scraper

A Python-based scraper for extracting product data from public Shopify stores.

## Features

- Scrapes product data from public Shopify stores
- Stores data in MongoDB for persistent storage
- Handles pagination automatically
- Implements rate limiting to respect store constraints
- Provides detailed logging
- Supports dynamic store URL input
- Exports data to CSV format
- Includes data validation and checking utilities
- Automatic MongoDB connection management and error recovery

## Prerequisites

- Python 3.8 or higher
- MongoDB server (local or remote)
- Docker (optional, for running MongoDB in a container)

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

4. Create a `.env` file in the project root with the following variables:
```env
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27018/  # Default port is 27018 for Docker setup
```

## MongoDB Setup

### Option 1: Using Docker (Recommended)

1. Pull and run MongoDB container:
```bash
docker run -d -p 27018:27017 --name shopify_scraper_mongodb mongo:latest
```

2. Verify the container is running:
```bash
docker ps | grep mongodb
```

### Option 2: Local Installation

1. Install MongoDB:
   - For Ubuntu:
     ```bash
     sudo apt-get install mongodb
     ```
   - For macOS (using Homebrew):
     ```bash
     brew tap mongodb/brew
     brew install mongodb-community
     ```
   - For Windows: Download and install from [MongoDB website](https://www.mongodb.com/try/download/community)

2. Start MongoDB service:
   - Ubuntu:
     ```bash
     sudo service mongodb start
     ```
   - macOS:
     ```bash
     brew services start mongodb-community
     ```
   - Windows: MongoDB runs as a service automatically

3. Verify MongoDB is running:
```bash
mongosh
```

## Usage

1. Make sure MongoDB is running
2. Run the scraper with a store URL:
```bash
python main.py https://store-name.myshopify.com
```

Optional arguments:
- `--limit`: Limit the number of products to scrape
  ```bash
  python main.py https://store-name.myshopify.com --limit 100
  ```

The scraper will:
- Connect to the specified Shopify store
- Scrape all products (or up to the limit if specified)
- Store them in MongoDB
- Export data to CSV format
- Provide progress updates in the console

## Data Management

### Checking Stored Data

Use the provided utility script to check the data in MongoDB:
```bash
python check_data.py
```

This will show:
- Total number of products
- List of stores in the database
- Sample product data
- Products count per store

### Data Structure

Products are stored in MongoDB with the following structure:
- Database: `shopify_scraper`
- Collection: `products`
- Indexes:
  - `id` (unique)
  - `handle`
  - `created_at`
  - `store_url`

Each product document includes:
- All Shopify product data
- `scraped_at` timestamp
- `store_url` for tracking which store the product came from

### Data Export

The scraper automatically exports data to CSV format in the `data` directory:
- File: `data/shopify_products.csv`
- Includes all product and variant information
- Supports incremental updates

## Error Handling

The scraper includes comprehensive error handling for:
- Store connection issues
- Rate limiting
- Data parsing errors
- MongoDB connection issues
- CSV export errors
- Data validation errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
