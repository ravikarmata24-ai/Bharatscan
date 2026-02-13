import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'indian-barcode-scanner-2024')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///indian_products.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API Keys
    OPEN_FOOD_FACTS_API = "https://world.openfoodfacts.org/api/v2"
    FSSAI_API_BASE = os.environ.get('FSSAI_API_BASE', 'https://foscos.fssai.gov.in/api')
    CDSCO_API_BASE = os.environ.get('CDSCO_API_BASE', 'https://cdsco.gov.in/api')

    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

    # Indian specific settings
    COUNTRY_CODE = 'IN'
    BARCODE_PREFIX_INDIA = ['890']  # GS1 India prefix

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}