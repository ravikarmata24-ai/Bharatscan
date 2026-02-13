import cv2
import numpy as np
from pyzbar import pyzbar
from PIL import Image
import io
import re


class BarcodeReader:
    """Handles barcode reading from images and camera feed"""

    SUPPORTED_FORMATS = [
        'EAN13', 'EAN8', 'UPCA', 'UPCE',
        'CODE128', 'CODE39', 'CODE93',
        'QRCODE', 'DATAMATRIX', 'PDF417'
    ]

    INDIA_GS1_PREFIXES = ['890']

    def __init__(self):
        self.last_scan_result = None

    def read_from_image(self, image_data):
        """Read barcode from uploaded image data"""
        try:
            # Convert bytes to numpy array
            if isinstance(image_data, bytes):
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif isinstance(image_data, np.ndarray):
                image = image_data
            elif isinstance(image_data, Image.Image):
                image = cv2.cvtColor(np.array(image_data), cv2.COLOR_RGB2BGR)
            else:
                return None, "Unsupported image format"

            if image is None:
                return None, "Could not decode image"

            # Try multiple preprocessing techniques
            results = self._scan_with_preprocessing(image)

            if results:
                best_result = results[0]
                barcode_data = best_result.data.decode('utf-8')
                barcode_type = best_result.type

                self.last_scan_result = {
                    'barcode': barcode_data,
                    'format': barcode_type,
                    'is_indian': self._is_indian_barcode(barcode_data),
                    'quality': self._assess_quality(best_result),
                }

                return self.last_scan_result, None
            else:
                return None, "No barcode detected in the image. Please try again with a clearer image."

        except Exception as e:
            return None, f"Error reading barcode: {str(e)}"

    def _scan_with_preprocessing(self, image):
        """Try multiple preprocessing methods to detect barcode"""
        all_results = []

        # Method 1: Direct scan
        results = pyzbar.decode(image)
        all_results.extend(results)

        if not all_results:
            # Method 2: Grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            results = pyzbar.decode(gray)
            all_results.extend(results)

        if not all_results:
            # Method 3: Threshold
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            results = pyzbar.decode(thresh)
            all_results.extend(results)

        if not all_results:
            # Method 4: Adaptive threshold
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            adaptive = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            results = pyzbar.decode(adaptive)
            all_results.extend(results)

        if not all_results:
            # Method 5: Enhanced contrast
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            results = pyzbar.decode(enhanced)
            all_results.extend(results)

        if not all_results:
            # Method 6: Resized image (scale up)
            height, width = image.shape[:2]
            scaled = cv2.resize(image, (width * 2, height * 2), interpolation=cv2.INTER_CUBIC)
            results = pyzbar.decode(scaled)
            all_results.extend(results)

        if not all_results:
            # Method 7: Blur then scan (removes noise)
            blurred = cv2.GaussianBlur(image, (5, 5), 0)
            results = pyzbar.decode(blurred)
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
        import time

        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None, "Could not open camera"

        start_time = time.time()
        result = None

        try:
            while time.time() - start_time < timeout:
                ret, frame = cap.read()
                if not ret:
                    continue

                barcodes = pyzbar.decode(frame)
                if barcodes:
                    barcode = barcodes[0]
                    barcode_data = barcode.data.decode('utf-8')

                    result = {
                        'barcode': barcode_data,
                        'format': barcode.type,
                        'is_indian': self._is_indian_barcode(barcode_data),
                    }
                    break

                # Display frame with guide
                cv2.rectangle(frame, (100, 100), (540, 380), (0, 255, 0), 2)
                cv2.putText(frame, "Place barcode inside the box",
                           (110, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow('Barcode Scanner', frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

        finally:
            cap.release()
            cv2.destroyAllWindows()

        if result:
            return result, None
        return None, "No barcode detected within timeout period"

    def _is_indian_barcode(self, barcode):
        """Check if barcode belongs to Indian GS1 prefix (890)"""
        if barcode and len(barcode) >= 3:
            return barcode[:3] in self.INDIA_GS1_PREFIXES
        return False

    def _assess_quality(self, barcode_result):
        """Assess the quality of barcode scan"""
        rect = barcode_result.rect
        area = rect.width * rect.height

        if area > 10000:
            return 'high'
        elif area > 5000:
            return 'medium'
        else:
            return 'low'

    def validate_barcode(self, barcode):
        """Validate barcode format"""
        if not barcode:
            return False, "Barcode is empty"

        # EAN-13 validation
        if len(barcode) == 13 and barcode.isdigit():
            if self._validate_ean13_checksum(barcode):
                return True, "Valid EAN-13 barcode"
            return False, "Invalid EAN-13 checksum"

        # EAN-8 validation
        if len(barcode) == 8 and barcode.isdigit():
            return True, "Valid EAN-8 barcode"

        # UPC-A validation
        if len(barcode) == 12 and barcode.isdigit():
            return True, "Valid UPC-A barcode"

        # General alphanumeric barcode
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
            '000': 'USA', '001': 'USA', '019': 'USA',
            '300': 'France', '379': 'France',
            '400': 'Germany', '440': 'Germany',
            '450': 'Japan', '459': 'Japan',
            '460': 'Russia', '469': 'Russia',
            '471': 'Taiwan',
            '480': 'Philippines',
            '489': 'Hong Kong',
            '500': 'UK', '509': 'UK',
            '539': 'Ireland',
            '540': 'Belgium',
            '560': 'Portugal',
            '569': 'Iceland',
            '570': 'Denmark',
            '590': 'Poland',
            '599': 'Hungary',
            '600': 'South Africa',
            '609': 'Mauritius',
            '690': 'China', '699': 'China',
            '729': 'Israel',
            '730': 'Sweden',
            '740': 'Guatemala',
            '750': 'Mexico',
            '770': 'Colombia',
            '773': 'Uruguay',
            '775': 'Peru',
            '779': 'Argentina',
            '780': 'Chile',
            '786': 'Ecuador',
            '789': 'Brazil',
            '800': 'Italy',
            '840': 'Spain',
            '850': 'Cuba',
            '858': 'Slovakia',
            '859': 'Czech Republic',
            '860': 'Serbia',
            '869': 'Turkey',
            '870': 'Netherlands',
            '880': 'South Korea',
            '885': 'Thailand',
            '893': 'Vietnam',
            '899': 'Indonesia',
            '930': 'Australia',
            '940': 'New Zealand',
            '955': 'Malaysia',
            '958': 'Macau',
        }
        return country_map.get(prefix, 'Unknown')