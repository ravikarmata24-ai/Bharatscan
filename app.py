import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from werkzeug.utils import secure_filename
from config import config
from database.models import db, Product, ScanHistory
from scanners.barcode_reader import BarcodeReader
from services.product_service import ProductService
from database.seed_data import seed_database


def create_app(config_name='default'):
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    CORS(app)

    # Ensure upload folder exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # Initialize services
    barcode_reader = BarcodeReader()
    product_service = ProductService()

    def allowed_file(filename):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    # ==================== WEB ROUTES ====================

    @app.route('/')
    def index():
        """Home page"""
        stats = {
            'total_products': Product.query.count(),
            'total_scans': ScanHistory.query.count(),
            'food_products': Product.query.filter_by(category='food').count(),
            'medicines': Product.query.filter_by(category='medicine').count(),
            'skincare': Product.query.filter_by(category='skincare').count(),
            'haircare': Product.query.filter_by(category='haircare').count(),
            'nutraceuticals': Product.query.filter_by(category='nutraceutical').count(),
        }
        return render_template('index.html', stats=stats)

    @app.route('/scan')
    def scan_page():
        """Barcode scanning page"""
        return render_template('scan.html')

    @app.route('/result/<barcode>')
    def result_page(barcode):
        """Product result page"""
        result = product_service.lookup_product(barcode, scan_method='web', request=request)
        return render_template('result.html', result=result, barcode=barcode)

    @app.route('/history')
    def history_page():
        """Scan history page"""
        history = product_service.get_scan_history(limit=100)
        return render_template('history.html', history=history)

    # ==================== API ROUTES ====================

    @app.route('/api/scan/upload', methods=['POST'])
    def api_scan_upload():
        """API: Scan barcode from uploaded image"""
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if file and allowed_file(file.filename):
            image_data = file.read()
            scan_result, error = barcode_reader.read_from_image(image_data)

            if error:
                return jsonify({'error': error}), 400

            barcode = scan_result['barcode']
            product_result = product_service.lookup_product(
                barcode, scan_method='upload', request=request
            )

            return jsonify({
                'scan': scan_result,
                'product': product_result,
            })
        else:
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, bmp, webp'}), 400

    @app.route('/api/scan/manual', methods=['POST'])
    def api_scan_manual():
        """API: Look up product by manual barcode entry"""
        data = request.get_json()
        if not data or 'barcode' not in data:
            return jsonify({'error': 'Barcode number is required'}), 400

        barcode = data['barcode'].strip()

        is_valid, message = barcode_reader.validate_barcode(barcode)
        if not is_valid:
            return jsonify({'error': message}), 400

        result = product_service.lookup_product(
            barcode, scan_method='manual', request=request
        )

        barcode_info = barcode_reader.get_barcode_info(barcode)

        return jsonify({
            'barcode_info': barcode_info,
            'product': result,
        })

    @app.route('/api/scan/camera', methods=['POST'])
    def api_scan_camera():
        """API: Process camera frame for barcode"""
        if 'frame' not in request.files:
            return jsonify({'error': 'No frame data provided'}), 400

        frame_file = request.files['frame']
        image_data = frame_file.read()
        scan_result, error = barcode_reader.read_from_image(image_data)

        if error:
            return jsonify({'found': False, 'error': error}), 200

        barcode = scan_result['barcode']
        product_result = product_service.lookup_product(
            barcode, scan_method='camera', request=request
        )

        return jsonify({
            'found': True,
            'scan': scan_result,
            'product': product_result,
        })

    @app.route('/api/product/<barcode>')
    def api_get_product(barcode):
        """API: Get product details by barcode"""
        result = product_service.lookup_product(barcode, request=request)
        return jsonify(result)

    @app.route('/api/search')
    def api_search():
        """API: Search products"""
        query = request.args.get('q', '')
        category = request.args.get('category', None)

        if not query and not category:
            return jsonify({'error': 'Search query or category required'}), 400

        products = product_service.search_products(query, category)
        return jsonify({'results': products, 'count': len(products)})

    @app.route('/api/fssai/verify/<license_number>')
    def api_verify_fssai(license_number):
        """API: Verify FSSAI license"""
        result = product_service.get_fssai_info(license_number)
        return jsonify(result)

    @app.route('/api/medicine/alternatives', methods=['POST'])
    def api_medicine_alternatives():
        """API: Find generic medicine alternatives"""
        data = request.get_json()
        brand = data.get('brand', '')
        composition = data.get('composition', '')

        from services.cdsco_service import CDSCOService
        cdsco = CDSCOService()
        alternatives = cdsco.find_generic_alternatives(brand, composition)

        return jsonify({
            'alternatives': alternatives,
            'jan_aushadhi_info': {
                'scheme_name': 'Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP)',
                'website': 'https://janaushadhi.gov.in',
                'total_stores': '10,000+ across India',
                'description': 'Government scheme providing quality generic medicines at affordable prices',
            }
        })

    @app.route('/api/history')
    def api_get_history():
        """API: Get scan history"""
        limit = request.args.get('limit', 50, type=int)
        history = product_service.get_scan_history(limit)
        return jsonify({'history': history})

    @app.route('/api/stats')
    def api_stats():
        """API: Get application statistics"""
        stats = {
            'total_products': Product.query.count(),
            'total_scans': ScanHistory.query.count(),
            'categories': {
                'food': Product.query.filter_by(category='food').count(),
                'medicine': Product.query.filter_by(category='medicine').count(),
                'nutraceutical': Product.query.filter_by(category='nutraceutical').count(),
                'skincare': Product.query.filter_by(category='skincare').count(),
                'haircare': Product.query.filter_by(category='haircare').count(),
            },
            'indian_products': Product.query.filter(
                Product.country_of_origin == 'India'
            ).count(),
        }
        return jsonify(stats)

    # ==================== ERROR HANDLERS ====================

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Not found'}), 404
        return render_template('base.html', error='Page not found'), 404

    @app.errorhandler(500)
    def server_error(error):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('base.html', error='Server error'), 500

    # ==================== DATABASE INITIALIZATION ====================

    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            seed_database()
            print("Database initialized with Indian product data")

    return app


app = create_app(os.environ.get('FLASK_ENV', 'development'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)