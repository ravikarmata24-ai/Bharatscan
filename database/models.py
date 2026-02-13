from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Product(db.Model):
    """Main product model for Indian products"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    barcode = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    brand = db.Column(db.String(255))
    category = db.Column(db.String(100))  # food, medicine, nutraceutical, skincare, haircare
    subcategory = db.Column(db.String(100))
    description = db.Column(db.Text)

    # Indian regulatory info
    fssai_license = db.Column(db.String(50))
    fssai_category = db.Column(db.String(100))
    manufacturing_license = db.Column(db.String(50))
    drug_license_number = db.Column(db.String(50))
    ayush_license = db.Column(db.String(50))
    bis_standard = db.Column(db.String(50))
    isi_mark = db.Column(db.Boolean, default=False)
    agmark = db.Column(db.Boolean, default=False)

    # Manufacturer info
    manufacturer = db.Column(db.String(255))
    manufacturer_address = db.Column(db.Text)
    country_of_origin = db.Column(db.String(100), default='India')
    manufactured_in = db.Column(db.String(100))

    # Product details
    mrp = db.Column(db.Float)
    net_weight = db.Column(db.String(50))
    net_volume = db.Column(db.String(50))
    shelf_life = db.Column(db.String(50))
    storage_instructions = db.Column(db.Text)
    usage_instructions = db.Column(db.Text)

    # Nutritional information (for food/nutraceuticals)
    serving_size = db.Column(db.String(50))
    energy_kcal = db.Column(db.Float)
    protein_g = db.Column(db.Float)
    carbohydrates_g = db.Column(db.Float)
    sugar_g = db.Column(db.Float)
    fat_g = db.Column(db.Float)
    saturated_fat_g = db.Column(db.Float)
    trans_fat_g = db.Column(db.Float)
    fiber_g = db.Column(db.Float)
    sodium_mg = db.Column(db.Float)
    cholesterol_mg = db.Column(db.Float)

    # Medicine specific
    composition = db.Column(db.Text)
    dosage = db.Column(db.Text)
    side_effects = db.Column(db.Text)
    contraindications = db.Column(db.Text)
    prescription_required = db.Column(db.Boolean, default=False)
    schedule = db.Column(db.String(10))  # H, H1, X, etc.

    # Cosmetic/Skincare specific
    ingredients_list = db.Column(db.Text)
    skin_type = db.Column(db.String(100))
    spf_value = db.Column(db.Integer)
    cruelty_free = db.Column(db.Boolean)
    paraben_free = db.Column(db.Boolean)
    sulphate_free = db.Column(db.Boolean)

    # Allergens & dietary info
    allergens = db.Column(db.Text)
    is_vegetarian = db.Column(db.Boolean)
    is_vegan = db.Column(db.Boolean)
    is_organic = db.Column(db.Boolean)
    is_gluten_free = db.Column(db.Boolean)
    contains_nuts = db.Column(db.Boolean)
    contains_dairy = db.Column(db.Boolean)

    # Veg/Non-Veg (Indian specific marking)
    veg_nonveg_mark = db.Column(db.String(20))  # 'green_dot', 'brown_dot', 'red_dot'

    # Ratings and reviews
    average_rating = db.Column(db.Float, default=0.0)
    total_reviews = db.Column(db.Integer, default=0)

    # Metadata
    image_url = db.Column(db.String(500))
    data_source = db.Column(db.String(100))
    last_verified = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    scan_history = db.relationship('ScanHistory', backref='product', lazy=True)
    warnings = db.relationship('ProductWarning', backref='product', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'barcode': self.barcode,
            'name': self.name,
            'brand': self.brand,
            'category': self.category,
            'subcategory': self.subcategory,
            'description': self.description,
            'fssai_license': self.fssai_license,
            'fssai_category': self.fssai_category,
            'drug_license_number': self.drug_license_number,
            'manufacturer': self.manufacturer,
            'manufacturer_address': self.manufacturer_address,
            'country_of_origin': self.country_of_origin,
            'mrp': self.mrp,
            'net_weight': self.net_weight,
            'shelf_life': self.shelf_life,
            'storage_instructions': self.storage_instructions,
            'usage_instructions': self.usage_instructions,
            'nutritional_info': self._get_nutritional_info(),
            'medicine_info': self._get_medicine_info(),
            'cosmetic_info': self._get_cosmetic_info(),
            'dietary_info': self._get_dietary_info(),
            'veg_nonveg_mark': self.veg_nonveg_mark,
            'ingredients_list': self.ingredients_list,
            'allergens': self.allergens,
            'average_rating': self.average_rating,
            'image_url': self.image_url,
            'warnings': [w.to_dict() for w in self.warnings],
            'is_indian_product': self._is_indian_barcode(),
        }

    def _get_nutritional_info(self):
        if self.category not in ['food', 'nutraceutical']:
            return None
        return {
            'serving_size': self.serving_size,
            'energy_kcal': self.energy_kcal,
            'protein_g': self.protein_g,
            'carbohydrates_g': self.carbohydrates_g,
            'sugar_g': self.sugar_g,
            'fat_g': self.fat_g,
            'saturated_fat_g': self.saturated_fat_g,
            'trans_fat_g': self.trans_fat_g,
            'fiber_g': self.fiber_g,
            'sodium_mg': self.sodium_mg,
            'cholesterol_mg': self.cholesterol_mg,
        }

    def _get_medicine_info(self):
        if self.category != 'medicine':
            return None
        return {
            'composition': self.composition,
            'dosage': self.dosage,
            'side_effects': self.side_effects,
            'contraindications': self.contraindications,
            'prescription_required': self.prescription_required,
            'schedule': self.schedule,
            'drug_license_number': self.drug_license_number,
        }

    def _get_cosmetic_info(self):
        if self.category not in ['skincare', 'haircare']:
            return None
        return {
            'ingredients_list': self.ingredients_list,
            'skin_type': self.skin_type,
            'spf_value': self.spf_value,
            'cruelty_free': self.cruelty_free,
            'paraben_free': self.paraben_free,
            'sulphate_free': self.sulphate_free,
        }

    def _get_dietary_info(self):
        return {
            'is_vegetarian': self.is_vegetarian,
            'is_vegan': self.is_vegan,
            'is_organic': self.is_organic,
            'is_gluten_free': self.is_gluten_free,
            'contains_nuts': self.contains_nuts,
            'contains_dairy': self.contains_dairy,
        }

    def _is_indian_barcode(self):
        if self.barcode and len(self.barcode) >= 3:
            return self.barcode[:3] in ['890']
        return False


class ProductWarning(db.Model):
    """Warnings associated with products"""
    __tablename__ = 'product_warnings'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    warning_type = db.Column(db.String(50))  # allergen, recall, advisory, banned_ingredient
    severity = db.Column(db.String(20))  # low, medium, high, critical
    message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100))
    issued_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'warning_type': self.warning_type,
            'severity': self.severity,
            'message': self.message,
            'source': self.source,
            'issued_date': self.issued_date.isoformat() if self.issued_date else None,
        }


class ScanHistory(db.Model):
    """User scan history"""
    __tablename__ = 'scan_history'

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    barcode_scanned = db.Column(db.String(50), nullable=False)
    scan_method = db.Column(db.String(20))  # camera, upload, manual
    product_found = db.Column(db.Boolean, default=False)
    data_source = db.Column(db.String(100))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'barcode_scanned': self.barcode_scanned,
            'product_found': self.product_found,
            'scan_method': self.scan_method,
            'data_source': self.data_source,
            'scanned_at': self.scanned_at.isoformat(),
            'product': self.product.to_dict() if self.product else None,
        }


class BannedIngredient(db.Model):
    """Ingredients banned/restricted by Indian authorities"""
    __tablename__ = 'banned_ingredients'

    id = db.Column(db.Integer, primary_key=True)
    ingredient_name = db.Column(db.String(255), nullable=False)
    cas_number = db.Column(db.String(50))
    category = db.Column(db.String(50))  # food, cosmetic, drug
    ban_type = db.Column(db.String(50))  # banned, restricted, limit
    max_allowed = db.Column(db.String(100))
    regulatory_body = db.Column(db.String(100))  # FSSAI, CDSCO, BIS
    regulation_reference = db.Column(db.String(255))
    reason = db.Column(db.Text)
    effective_date = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'ingredient_name': self.ingredient_name,
            'category': self.category,
            'ban_type': self.ban_type,
            'max_allowed': self.max_allowed,
            'regulatory_body': self.regulatory_body,
            'reason': self.reason,
        }