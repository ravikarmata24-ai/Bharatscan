import io
import re
import numpy as np


class BarcodeReader:
    """Handles barcode reading - simplified version without pyzbar"""

    SUPPORTED_FORMATS = [
        'EAN13', 'EAN8', 'UPCA', 'UPCE',
        'CODE128', 'CODE39', 'CODE93',
        'QRCODE', 'DATAMATRIX', 'PDF417'
    ]

    INDIA_GS1_PREFIXES = ['890']

    def __init__(self):
        self.last_scan_result = None
        self.pyzbar_available = False
        self.cv2_available = False

        # Try importing pyzbar
        try:
            from pyzbar import pyzbar
            self.pyzbar_available = True
        except (ImportError, FileNotFoundError):
            print("WARNING: pyzbar not available. Camera/image scanning disabled.")
            print("Manual barcode entry will still work.")

        # Try importing opencv
        try:
            import cv2
            self.cv2_available = True
        except ImportError:
            print("WARNING: opencv not available.")

    def read_from_image(self, image_data):
        """Read barcode from uploaded image data"""
        if not self.pyzbar_available:
            return None, "Barcode scanning from images is not available. Please use manual entry."

        try:
            from pyzbar import pyzbar
            import cv2

            if isinstance(image_data, bytes):
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_data, np.ndarray):
                image = image_data
            else:
                return None, "Unsupported image format"

            if image is None:
                return None, "Could not decode image"

            results = self._scan_with_preprocessing(image)

            if results:
                best_result = results[0]
                barcode_data = best_result.data.decode('utf-8')
                barcode_type = best_result.type

                self.last_scan_result = {
                    'barcode': barcode_data,
                    'format': barcode_type,
                    'is_indian': self._is_indian_barcode(barcode_data),
                    'quality': 'high',
                }

                return self.last_scan_result, None
            else:
                return None, "No barcode detected in the image. Please try again with a clearer image."

        except Exception as e:
            return None, f"Error reading barcode: {str(e)}"

    def _scan_with_preprocessing(self, image):
        """Try multiple preprocessing methods to detect barcode"""
        from pyzbar import pyzbar
        import cv2

        all_results = []

        # Method 1: Direct scan
        results = pyzbar.decode(image)
        all_results.extend(results)

        if not all_results:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = pyzbar.decode(gray)
            all_results.extend(results)

        if not all_results:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results = pyzbar.decode(thresh)
            all_results.extend(results)

        if not all_results:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            results = pyzbar.decode(enhanced)
            all_results.extend(results)

        if not all_results:
            height, width = image.shape[:2]
            scaled = cv2.resize(image, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
            results = pyzbar.decode(scaled)
            all_results.extend(results)

        # Remove duplicates
        seen = set()
        unique_results = []
        for r in all_results:
            key = r.data.decode('utf-8')
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        return unique_results

    def read_from_camera(self, camera_index=0, timeout=30):
        """Read barcode from camera feed"""
        if not self.pyzbar_available or not self.cv2_available:
            return None, "Camera scanning not available. Please use manual entry."
        return None, "Camera scanning is handled by the browser."

    def _is_indian_barcode(self, barcode):
        """Check if barcode belongs to Indian GS1 prefix (890)"""
        if barcode and len(barcode) >= 3:
            return barcode[:3] in self.INDIA_GS1_PREFIXES
        return False

    def validate_barcode(self, barcode):
        """Validate barcode format"""
        if not barcode:
            return False, "Barcode is empty"

        if len(barcode) == 13 and barcode.isdigit():
            if self._validate_ean13_checksum(barcode):
                return True, "Valid EAN-13 barcode"
            return False, "Invalid EAN-13 checksum"

        if len(barcode) == 8 and barcode.isdigit():
            return True, "Valid EAN-8 barcode"

        if len(barcode) == 12 and barcode.isdigit():
            return True, "Valid UPC-A barcode"

        if re.match(r'^[A-Za-z0-9\-\.]+$', barcode):
            return True, "Valid barcode format"

        return False, "Unrecognized barcode format"

    def _validate_ean13_checksum(self, barcode):
        """Validate EAN-13 checksum"""
        try:
            digits = [int(d) for d in barcode]
            odd_sum = sum(digits[i] for i in range(0, 12, 2))
            even_sum = sum(digits[i] for i in range(1, 12, 2))
            check = (10 - (odd_sum + even_sum * 3) % 10) % 10
            return check == digits[12]
        except (ValueError, IndexError):
            return False

    def get_barcode_info(self, barcode):
        """Get basic info from barcode number"""
        info = {
            'barcode': barcode,
            'length': len(barcode),
            'is_indian': self._is_indian_barcode(barcode),
        }

        if len(barcode) >= 3:
            prefix = barcode[:3]
            info['gs1_prefix'] = prefix
            info['country'] = self._get_country_from_prefix(prefix)

        return info

    def _get_country_from_prefix(self, prefix):
        """Get country name from GS1 prefix"""
        country_map = {
            '890': 'India',
            '000': 'USA', '001': 'USA',
            '300': 'France',
            '400': 'Germany',
            '450': 'Japan',
            '460': 'Russia',
            '471': 'Taiwan',
            '489': 'Hong Kong',
            '500': 'UK',
            '690': 'China', '699': 'China',
            '729': 'Israel',
            '750': 'Mexico',
            '789': 'Brazil',
            '800': 'Italy',
            '840': 'Spain',
            '880': 'South Korea',
            '885': 'Thailand',
            '893': 'Vietnam',
            '899': 'Indonesia',
            '930': 'Australia',
            '955': 'Malaysia',
        }
        return country_map.get(prefix, 'Unknown')