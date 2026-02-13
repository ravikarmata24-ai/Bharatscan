from database.models import db, Product, ScanHistory, BannedIngredient
from services.openfoodfacts import OpenFoodFactsService
from services.fssai_service import FSSAIService
from services.cdsco_service import CDSCOService
from datetime import datetime


class ProductService:
    """Main service for product lookup from multiple Indian databases"""

    def __init__(self):
        self.off_service = OpenFoodFactsService()
        self.fssai_service = FSSAIService()
        self.cdsco_service = CDSCOService()

    def lookup_product(self, barcode, scan_method='manual', request=None):
        """
        Look up product from multiple sources:
        1. Local database (pre-seeded Indian products)
        2. Open Food Facts API (international + Indian products)
        3. FSSAI database (food products)
        4. CDSCO database (medicines)
        """
        result = {
            'found': False,
            'product': None,
            'source': None,
            'warnings': [],
            'alternatives': [],
        }

        # Step 1: Check local database first
        product = Product.query.filter_by(barcode=barcode).first()
        if product:
            result['found'] = True
            result['product'] = product.to_dict()
            result['source'] = 'Local Indian Database'
            # Check for banned ingredients
            result['warnings'] = self._check_banned_ingredients(product)
            self._log_scan(barcode, product.id, scan_method, True, 'local_db', request)
            return result

        # Step 2: Try Open Food Facts API
        off_product = self.off_service.get_product(barcode)
        if off_product:
            # Save to local database for future lookups
            saved_product = self._save_off_product(barcode, off_product)
            result['found'] = True
            result['product'] = saved_product.to_dict() if saved_product else off_product
            result['source'] = 'Open Food Facts'
            self._log_scan(barcode, saved_product.id if saved_product else None,
                          scan_method, True, 'openfoodfacts', request)
            return result

        # Step 3: Try FSSAI service
        fssai_product = self.fssai_service.search_product(barcode)
        if fssai_product:
            saved_product = self._save_fssai_product(barcode, fssai_product)
            result['found'] = True
            result['product'] = saved_product.to_dict() if saved_product else fssai_product
            result['source'] = 'FSSAI Database'
            self._log_scan(barcode, saved_product.id if saved_product else None,
                          scan_method, True, 'fssai', request)
            return result

        # Step 4: Try CDSCO service (for medicines)
        cdsco_product = self.cdsco_service.search_medicine(barcode)
        if cdsco_product:
            saved_product = self._save_cdsco_product(barcode, cdsco_product)
            result['found'] = True
            result['product'] = saved_product.to_dict() if saved_product else cdsco_product
            result['source'] = 'CDSCO Database'
            self._log_scan(barcode, saved_product.id if saved_product else None,
                          scan_method, True, 'cdsco', request)
            return result

        # Product not found
        self._log_scan(barcode, None, scan_method, False, None, request)
        result['found'] = False
        result['message'] = 'Product not found in any Indian database'
        result['barcode_info'] = self._get_barcode_details(barcode)

        return result

    def _check_banned_ingredients(self, product):
        """Check if product contains any banned/restricted ingredients in India"""
        warnings = []

        if not product.ingredients_list:
            return warnings

        ingredients_lower = product.ingredients_list.lower()

        # Determine category for banned ingredient check
        categories_to_check = ['food', 'cosmetic', 'drug']
        if product.category in ['skincare', 'haircare']:
            categories_to_check = ['cosmetic']
        elif product.category == 'medicine':
            categories_to_check = ['drug']
        elif product.category in ['food', 'nutraceutical']:
            categories_to_check = ['food']

        banned = BannedIngredient.query.filter(
            BannedIngredient.category.in_(categories_to_check)
        ).all()

        for item in banned:
            if item.ingredient_name.lower() in ingredients_lower:
                warnings.append({
                    'type': 'banned_ingredient',
                    'severity': 'critical' if item.ban_type == 'banned' else 'high',
                    'message': f"⚠️ Contains {item.ingredient_name} which is {item.ban_type} by {item.regulatory_body}",
                    'reason': item.reason,
                    'regulation': item.regulation_reference,
                })

        # Additional health warnings
        if product.category == 'food':
            if product.sodium_mg and product.sodium_mg > 600:
                warnings.append({
                    'type': 'health_advisory',
                    'severity': 'medium',
                    'message': '⚠️ High sodium content. WHO recommends less than 2000mg sodium per day.',
                })
            if product.sugar_g and product.sugar_g > 12:
                warnings.append({
                    'type': 'health_advisory',
                    'severity': 'medium',
                    'message': '⚠️ High sugar content per serving.',
                })
            if product.trans_fat_g and product.trans_fat_g > 0:
                warnings.append({
                    'type': 'health_advisory',
                    'severity': 'high',
                    'message': '⚠️ Contains trans fat. FSSAI recommends zero trans fat intake.',
                })

        return warnings

    def _save_off_product(self, barcode, off_data):
        """Save Open Food Facts product to local database"""
        try:
            product = Product(
                barcode=barcode,
                name=off_data.get('product_name', 'Unknown Product'),
                brand=off_data.get('brands', ''),
                category='food',
                description=off_data.get('generic_name', ''),
                manufacturer=off_data.get('manufacturing_places', ''),
                country_of_origin=off_data.get('countries', ''),
                net_weight=off_data.get('quantity', ''),
                ingredients_list=off_data.get('ingredients_text', ''),
                allergens=off_data.get('allergens', ''),
                image_url=off_data.get('image_url', ''),
                data_source='openfoodfacts',
                last_verified=datetime.utcnow(),
            )

            # Nutritional info
            nutriments = off_data.get('nutriments', {})
            if nutriments:
                product.energy_kcal = nutriments.get('energy-kcal_100g')
                product.protein_g = nutriments.get('proteins_100g')
                product.carbohydrates_g = nutriments.get('carbohydrates_100g')
                product.sugar_g = nutriments.get('sugars_100g')
                product.fat_g = nutriments.get('fat_100g')
                product.saturated_fat_g = nutriments.get('saturated-fat_100g')
                product.fiber_g = nutriments.get('fiber_100g')
                product.sodium_mg = nutriments.get('sodium_100g', 0) * 1000 if nutriments.get('sodium_100g') else None

            db.session.add(product)
            db.session.commit()
            return product
        except Exception as e:
            db.session.rollback()
            print(f"Error saving OFF product: {e}")
            return None

    def _save_fssai_product(self, barcode, fssai_data):
        """Save FSSAI product to local database"""
        try:
            product = Product(
                barcode=barcode,
                name=fssai_data.get('product_name', 'Unknown'),
                brand=fssai_data.get('brand', ''),
                category='food',
                fssai_license=fssai_data.get('fssai_license', ''),
                fssai_category=fssai_data.get('category', ''),
                manufacturer=fssai_data.get('manufacturer', ''),
                manufacturer_address=fssai_data.get('address', ''),
                data_source='fssai',
                last_verified=datetime.utcnow(),
            )
            db.session.add(product)
            db.session.commit()
            return product
        except Exception as e:
            db.session.rollback()
            print(f"Error saving FSSAI product: {e}")
            return None

    def _save_cdsco_product(self, barcode, cdsco_data):
        """Save CDSCO medicine to local database"""
        try:
            product = Product(
                barcode=barcode,
                name=cdsco_data.get('product_name', 'Unknown'),
                brand=cdsco_data.get('brand', ''),
                category='medicine',
                drug_license_number=cdsco_data.get('drug_license', ''),
                composition=cdsco_data.get('composition', ''),
                manufacturer=cdsco_data.get('manufacturer', ''),
                prescription_required=cdsco_data.get('prescription_required', False),
                schedule=cdsco_data.get('schedule', ''),
                data_source='cdsco',
                last_verified=datetime.utcnow(),
            )
            db.session.add(product)
            db.session.commit()
            return product
        except Exception as e:
            db.session.rollback()
            print(f"Error saving CDSCO product: {e}")
            return None

    def _log_scan(self, barcode, product_id, scan_method, found, source, request):
        """Log scan to history"""
        try:
            scan = ScanHistory(
                barcode_scanned=barcode,
                product_id=product_id,
                scan_method=scan_method,
                product_found=found,
                data_source=source,
                ip_address=request.remote_addr if request else None,
                user_agent=request.user_agent.string if request else None,
            )
            db.session.add(scan)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error logging scan: {e}")

    def _get_barcode_details(self, barcode):
        """Get basic barcode information"""
        from scanners.barcode_reader import BarcodeReader
        reader = BarcodeReader()
        return reader.get_barcode_info(barcode)

    def get_scan_history(self, limit=50):
        """Get recent scan history"""
        scans = ScanHistory.query.order_by(
            ScanHistory.scanned_at.desc()
        ).limit(limit).all()
        return [scan.to_dict() for scan in scans]

    def search_products(self, query, category=None):
        """Search products by name or brand"""
        filters = []
        if query:
            search_term = f"%{query}%"
            filters.append(
                db.or_(
                    Product.name.ilike(search_term),
                    Product.brand.ilike(search_term),
                    Product.manufacturer.ilike(search_term),
                )
            )
        if category:
            filters.append(Product.category == category)

        products = Product.query.filter(*filters).limit(20).all()
        return [p.to_dict() for p in products]

    def get_fssai_info(self, license_number):
        """Get FSSAI license information"""
        return self.fssai_service.verify_license(license_number)