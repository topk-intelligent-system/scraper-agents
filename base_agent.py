from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import yaml

class BaseAgent(ABC):
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the base agent with optional config file."""
        self.config = {}
        if config_path:
            self.load_config(config_path)
        
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)
        
        # Setup logging
        logger.add("data/scraper.log", rotation="500 MB")
    
    def load_config(self, config_path: str) -> None:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to the e-commerce platform."""
        pass
    
    @abstractmethod
    def crawl(self) -> List[Dict]:
        """Crawl the e-commerce platform and return raw data."""
        pass
    
    @abstractmethod
    def extract_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Extract and normalize product data from raw data."""
        pass
    
    def save_json(self, data: List[Dict], filename: str) -> None:
        """Save extracted data to JSON file."""
        try:
            # Convert filename to Path object and resolve it
            output_path = Path(filename).resolve()
            
            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.success(f"Data saved to {output_path}")
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            raise
    
    def run(self, output_filename: str) -> None:
        """Main execution flow."""
        try:
            logger.info("Starting scraping process")
            self.connect()
            raw_data = self.crawl()
            processed_data = self.extract_data(raw_data)
            self.save_json(processed_data, output_filename)
            logger.success("Scraping process completed successfully")
        except Exception as e:
            logger.error(f"Error during scraping process: {str(e)}")
            raise 