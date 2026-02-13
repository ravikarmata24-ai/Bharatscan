import requests
from config import Config


class OpenFoodFactsService:
    """Service to interact with Open Food Facts API for product data"""

    BASE_URL = "https://world.openfoodfacts.org/api/v2"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'IndianBarcodeScanner/1.0 (contact@example.com)'
        })

    def get_product(self, barcode):
        """Get product details by barcode from Open Food Facts"""
        try:
            url = f"{self.BASE_URL}/product/{barcode}.json"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 1:
                    product = data.get('product', {})
                    return self._format_product(product)
            return None

        except requests.RequestException as e:
            print(f"Open Food Facts API error: {e}")
            return None

    def search_products(self, query, country='india', page=1, page_size=20):
        """Search products on Open Food Facts"""
        try:
            url = f"{self.BASE_URL}/search"
            params = {
                'search_terms': query,
                'search_simple': 1,
                'json': 1,
                'page': page,
                'page_size': page_size,
                'countries_tags_en': country,
            }
            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                return [self._format_product(p) for p in products]
            return []

        except requests.RequestException as e:
            print(f"Open Food Facts search error: {e}")
            return []

    def _format_product(self, product_data):
        """Format Open Food Facts product data"""
        return {
            'product_name': product_data.get('product_name', 'Unknown'),
            'brands': product_data.get('brands', ''),
            'generic_name': product_data.get('generic_name', ''),
            'quantity': product_data.get('quantity', ''),
            'categories': product_data.get('categories', ''),
            'countries': product_data.get('countries', ''),
            'manufacturing_places': product_data.get('manufacturing_places', ''),
            'ingredients_text': product_data.get('ingredients_text', ''),
            'allergens': product_data.get('allergens', ''),
            'nutriments': product_data.get('nutriments', {}),
            'nutrition_grades': product_data.get('nutrition_grades', ''),
            'nova_group': product_data.get('nova_group', ''),
            'ecoscore_grade': product_data.get('ecoscore_grade', ''),
            'image_url': product_data.get('image_url', ''),
            'image_front_url': product_data.get('image_front_url', ''),
            'labels': product_data.get('labels', ''),
            'stores': product_data.get('stores', ''),
            'code': product_data.get('code', ''),
        }

    def get_indian_products(self, category=None, page=1):
        """Get products specifically from India"""
        try:
            url = f"https://world.openfoodfacts.org/country/india.json"
            params = {'page': page}
            if category:
                url = f"https://world.openfoodfacts.org/country/
    def get_indian_products(self, category=None, page=1):
        """Get products specifically from India"""
        try:
            url = f"https://world.openfoodfacts.org/country/india.json"
            params = {'page': page}
            if category:
                url = f"https://world.openfoodfacts.org/country/india/category/{category}.json"

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                products = data.get('products', [])
                return {
                    'products': [self._format_product(p) for p in products],
                    'count': data.get('count', 0),
                    'page': data.get('page', 1),
                    'page_size': data.get('page_size', 20),
                }
            return {'products': [], 'count': 0}

        except requests.RequestException as e:
            print(f"Error fetching Indian products: {e}")
            return {'products': [], 'count': 0}