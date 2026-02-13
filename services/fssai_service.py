import requests
from config import Config
from datetime import datetime


class FSSAIService:
    """
    Service to interact with FSSAI (Food Safety and Standards Authority of India)
    
    Note: FSSAI doesn't have a fully public API. This service provides:
    1. License verification simulation
    2. Known product database lookup
    3. Food recall/alert checking
    
    In production, you would integrate with:
    - FoSCoS (Food Safety Compliance System): https://foscos.fssai.gov.in
    - FSSAI Food Recall Portal
    """

    FSSAI_LICENSE_PATTERNS = {
        14: 'State License',
        10: 'Central License (Manufacturer)',
        11: 'Central License (Importer)',
    }

    # Known FSSAI food categories
    FOOD_CATEGORIES = {
        '01': 'Dairy Products and Analogues',
        '02': 'Fats and Oils',
        '03': 'Edible Ices',
        '04': 'Fruits and Vegetables',
        '05': 'Confectionery',
        '06': 'Cereals and Cereal Products',
        '07': 'Bakery Products',
        '08': 'Meat and Meat Products',
        '09': 'Fish and Fish Products',
        '10': 'Eggs and Egg Products',
        '11': 'Sweeteners including Honey',
        '12': 'Salt, Spices, Soups, Sauces',
        '13': 'Foodstuffs for Special Nutritional Uses',
        '14': 'Beverages',
        '15': 'Ready to Eat Savories',
        '16': 'Composite Foods',
    }

    # Simulated FSSAI product database (for demo purposes)
    KNOWN_FSSAI_PRODUCTS = {
        '10013041000157': {
            'license_holder': 'Parle Products Pvt Ltd',
            'license_type': 'Central License',
            'state': 'Maharashtra',
            'status': 'Active',
            'valid_until': '2026-03-15',
            'food_categories': ['07', '05'],
        },
        '10013061006476': {
            'license_holder': 'Nestle India Ltd',
            'license_type': 'Central License',
            'state': 'Haryana',
            'status': 'Active',
            'valid_until': '2025-12-31',
            'food_categories': ['06', '01', '14'],
        },
        '10011011000234': {
            'license_holder': 'GCMMF (Amul)',
            'license_type': 'Central License',
            'state': 'Gujarat',
            'status': 'Active',
            'valid_until': '2025-09-30',
            'food_categories': ['01', '03'],
        },
        '10014011000215': {
            'license_holder': 'Haldiram Snacks Pvt Ltd',
            'license_type': 'Central License',
            'state': 'Delhi',
            'status': 'Active',
            'valid_until': '2025-06-30',
            'food_categories': ['15', '05'],
        },
        '10014011000198': {
            'license_holder': 'Dabur India Ltd',
            'license_type': 'Central License',
            'state': 'Delhi',
            'status': 'Active',
            'valid_until': '2026-01-15',
            'food_categories': ['13', '11'],
        },
        '10016011003127': {
            'license_holder': 'The Himalaya Drug Company',
            'license_type': 'Central License',
            'state': 'Karnataka',
            'status': 'Active',
            'valid_until': '2025-11-30',
            'food_categories': ['13'],
        },
    }

    # Recent FSSAI alerts/recalls (simulated)
    RECENT_ALERTS = [
        {
            'alert_id': 'FSSAI-2024-001',
            'type': 'recall',
            'product': 'Certain spice brands',
            'reason': 'Ethylene oxide contamination above permissible limits',
            'date': '2024-01-15',
            'severity': 'high',
            'affected_brands': ['MDH', 'Everest'],
        },
        {
            'alert_id': 'FSSAI-2024-002',
            'type': 'advisory',
            'product': 'Honey brands',
            'reason': 'Sugar syrup adulteration detected in NMR testing',
            'date': '2024-02-20',
            'severity': 'medium',
        },
    ]

    def __init__(self):
        self.base_url = Config.FSSAI_API_BASE
        self.session = requests.Session()

    def verify_license(self, license_number):
        """
        Verify FSSAI license number
        
        FSSAI License format:
        - 14 digits: State license
        - Starts with 1: Central license
        - Starts with 2: State license
        """
        if not license_number:
            return {'valid': False, 'message': 'No license number provided'}

        # Clean the license number
        license_number = license_number.strip().replace(' ', '')

        # Check format
        if not license_number.isdigit():
            return {'valid': False, 'message': 'FSSAI license must contain only digits'}

        if len(license_number) != 14:
            return {
                'valid': False,
                'message': f'FSSAI license must be 14 digits. Got {len(license_number)} digits.'
            }

        # Check in known database
        if license_number in self.KNOWN_FSSAI_PRODUCTS:
            info = self.KNOWN_FSSAI_PRODUCTS[license_number]
            return {
                'valid': True,
                'license_number': license_number,
                'license_holder': info['license_holder'],
                'license_type': info['license_type'],
                'state': info['state'],
                'status': info['status'],
                'valid_until': info['valid_until'],
                'food_categories': [
                    self.FOOD_CATEGORIES.get(cat, 'Unknown')
                    for cat in info.get('food_categories', [])
                ],
                'source': 'FSSAI Database (Demo)',
            }

        # Try real FSSAI API (if available)
        try:
            result = self._query_fssai_api(license_number)
            if result:
                return result
        except Exception as e:
            print(f"FSSAI API query failed: {e}")

        # Parse license number for basic info
        return self._parse_license_format(license_number)

    def _parse_license_format(self, license_number):
        """Parse FSSAI license number format for basic information"""
        result = {
            'valid': None,  # Cannot confirm without API
            'license_number': license_number,
            'message': 'License format appears valid but could not be verified online',
        }

        # First 2 digits: License type
        type_code = license_number[:2]
        if type_code.startswith('1'):
            result['license_type'] = 'Central License'
        elif type_code.startswith('2'):
            result['license_type'] = 'State License'
        else:
            result['license_type'] = 'Registration'

        # Digits 3-4: State code
        state_code = license_number[2:4]
        result['state'] = self._get_state_from_code(state_code)

        # Digits 5-6: Year
        year_code = license_number[4:6]
        result['issue_year'] = f"20{year_code}" if int(year_code) < 50 else f"19{year_code}"

        return result

    def _get_state_from_code(self, code):
        """Get Indian state from FSSAI state code"""
        state_map = {
            '01': 'Jammu & Kashmir',
            '02': 'Himachal Pradesh',
            '03': 'Punjab',
            '04': 'Chandigarh',
            '05': 'Uttarakhand',
            '06': 'Haryana',
            '07': 'Delhi',
            '08': 'Rajasthan',
            '09': 'Uttar Pradesh',
            '10': 'Bihar',
            '11': 'Sikkim',
            '12': 'Arunachal Pradesh',
            '13': 'Nagaland',
            '14': 'Manipur',
            '15': 'Mizoram',
            '16': 'Tripura',
            '17': 'Meghalaya',
            '18': 'Assam',
            '19': 'West Bengal',
            '20': 'Jharkhand',
            '21': 'Odisha',
            '22': 'Chhattisgarh',
            '23': 'Madhya Pradesh',
            '24': 'Gujarat',
            '25': 'Daman & Diu',
            '26': 'Dadra & Nagar Haveli',
            '27': 'Maharashtra',
            '28': 'Andhra Pradesh',
            '29': 'Karnataka',
            '30': 'Goa',
            '31': 'Lakshadweep',
            '32': 'Kerala',
            '33': 'Tamil Nadu',
            '34': 'Puducherry',
            '35': 'Andaman & Nicobar',
            '36': 'Telangana',
            '37': 'Andhra Pradesh (new)',
        }
        return state_map.get(code, f'Unknown (Code: {code})')

    def _query_fssai_api(self, license_number):
        """
        Query actual FSSAI FoSCoS API
        Note: This is a placeholder - actual integration requires FSSAI API access
        """
        try:
            # Placeholder for actual FSSAI API call
            # url = f"{self.base_url}/license/verify/{license_number}"
            # response = self.session.get(url, timeout=10)
            # if response.status_code == 200:
            #     return response.json()
            return None
        except Exception:
            return None

    def search_product(self, barcode):
        """
        Search for a food product in FSSAI database
        Note: FSSAI doesn't have a direct barcode lookup API
        This is a placeholder for future integration
        """
        try:
            # In production, you would query FSSAI's product database
            # For now, return None to fall through to other services
            return None
        except Exception as e:
            print(f"FSSAI product search error: {e}")
            return None

    def check_food_recalls(self, product_name=None, brand=None):
        """Check if a product has been recalled by FSSAI"""
        alerts = []

        for alert in self.RECENT_ALERTS:
            if brand and 'affected_brands' in alert:
                if brand in alert['affected_brands']:
                    alerts.append(alert)
            elif product_name:
                if product_name.lower() in alert.get('product', '').lower():
                    alerts.append(alert)

        return alerts

    def get_food_standards(self, category_code):
        """Get FSSAI food standards for a category"""
        standards = {
            '01': {
                'category': 'Dairy Products',
                'key_standards': [
                    'Fat content as per FSSAI specification',
                    'Pasteurization requirements',
                    'Microbial limits as per FSS Regulations 2011',
                    'No added melamine or urea',
                ],
                'regulation': 'Food Safety and Standards (Food Products Standards and Food Additives) Regulations, 2011',
            },
            '06': {
                'category': 'Cereals',
                'key_standards': [
                    'No potassium bromate as flour improver',
                    'Fortification requirements under FSSAI',
                    'Pesticide residue limits',
                    'Aflatoxin limits',
                ],
                'regulation': 'FSS (Food Products Standards and Food Additives) Regulations, 2011',
            },
            '14': {
                'category': 'Beverages',
                'key_standards': [
                    'Carbonated water standards',
                    'Fruit juice minimum content',
                    'Sugar/sweetener limits',
                    'Preservative limits',
                ],
                'regulation': 'FSS (Food Products Standards and Food Additives) Regulations, 2011',
            },
        }
        return standards.get(category_code, None)