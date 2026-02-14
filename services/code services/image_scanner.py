import io


class ImageBarcodeScanner:
    """Server-side barcode detection from uploaded images using Pillow."""

    def scan_image_bytes(self, image_bytes):
        """
        Try to find a barcode in the image bytes.
        Returns (barcode_string, None) on success or (None, error_message) on failure.
        """
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(image_bytes))
            gray = img.convert('L')
            width, height = gray.size
            pixels = list(gray.getdata())

            barcodes_found = {}

            # Scan many horizontal lines
            for line_pct in range(15, 85, 2):
                y = int(height * line_pct / 100)
                row = pixels[y * width:(y + 1) * width]

                if len(row) < 100:
                    continue

                threshold = self._otsu_threshold(row)
                binary = [0 if p < threshold else 1 for p in row]

                barcode = self._find_ean13(binary)
                if barcode:
                    barcodes_found[barcode] = barcodes_found.get(barcode, 0) + 1

            # Try different thresholds
            if not barcodes_found:
                for thresh in [80, 100, 120, 140, 160]:
                    for line_pct in range(20, 80, 5):
                        y = int(height * line_pct / 100)
                        row = pixels[y * width:(y + 1) * width]
                        binary = [0 if p < thresh else 1 for p in row]
                        barcode = self._find_ean13(binary)
                        if barcode:
                            barcodes_found[barcode] = barcodes_found.get(barcode, 0) + 1

            # Try rotated 90 degrees
            if not barcodes_found:
                rotated = gray.rotate(90, expand=True)
                rw, rh = rotated.size
                rpixels = list(rotated.getdata())
                for line_pct in range(20, 80, 3):
                    y = int(rh * line_pct / 100)
                    row = rpixels[y * rw:(y + 1) * rw]
                    if len(row) < 100:
                        continue
                    threshold = self._otsu_threshold(row)
                    binary = [0 if p < threshold else 1 for p in row]
                    barcode = self._find_ean13(binary)
                    if barcode:
                        barcodes_found[barcode] = barcodes_found.get(barcode, 0) + 1

            # Try scaled versions
            if not barcodes_found:
                for scale in [0.5, 2.0]:
                    scaled = gray.resize((int(width * scale), int(height * scale)))
                    sw, sh = scaled.size
                    spixels = list(scaled.getdata())
                    for line_pct in range(20, 80, 5):
                        y = int(sh * line_pct / 100)
                        row = spixels[y * sw:(y + 1) * sw]
                        if len(row) < 50:
                            continue
                        threshold = self._otsu_threshold(row)
                        binary = [0 if p < threshold else 1 for p in row]
                        barcode = self._find_ean13(binary)
                        if barcode:
                            barcodes_found[barcode] = barcodes_found.get(barcode, 0) + 1

            if barcodes_found:
                best = max(barcodes_found, key=barcodes_found.get)
                return best, None
            else:
                return None, 'No barcode detected in image'

        except ImportError:
            return None, 'Pillow not installed on server'
        except Exception as e:
            return None, 'Error: ' + str(e)

    def _otsu_threshold(self, pixels):
        """Calculate best threshold for black/white conversion."""
        if not pixels:
            return 128

        histogram = [0] * 256
        for p in pixels:
            histogram[min(255, max(0, int(p)))] += 1

        total = len(pixels)
        sum_total = sum(i * histogram[i] for i in range(256))
        sum_bg = 0
        weight_bg = 0
        max_variance = 0
        threshold = 128

        for i in range(256):
            weight_bg += histogram[i]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break
            sum_bg += i * histogram[i]
            mean_bg = sum_bg / weight_bg
            mean_fg = (sum_total - sum_bg) / weight_fg
            variance = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if variance > max_variance:
                max_variance = variance
                threshold = i

        return threshold

    def _find_ean13(self, binary):
        """Try to find and decode EAN-13 barcode in binary line."""
        if len(binary) < 95:
            return None

        # Look for start guard pattern: 1,0,1
        for i in range(len(binary) - 95):
            if binary[i] == 1 and binary[i + 1] == 0 and binary[i + 2] == 1:
                result = self._try_decode_ean13(binary, i)
                if result:
                    return result
        return None

    def _try_decode_ean13(self, binary, start):
        """Try decoding EAN-13 from a start position."""
        L = ['0001101', '0011001', '0010011', '0111101', '0100011',
             '0110001', '0101111', '0111011', '0110111', '0001011']
        G = ['0100111', '0110011', '0011011', '0100001', '0011101',
             '0111001', '0000101', '0010001', '0001001', '0010111']
        R = ['1110010', '1100110', '1101100', '1000010', '1011100',
             '1001110', '1010000', '1000100', '1001000', '1110100']
        FIRST = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG',
                 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']

        try:
            # Calculate module width from start guard
            pos = start

            # Skip start guard (3 modules)
            pos += 3

            # Check if we have enough data
            if pos + 42 + 5 + 42 + 3 > len(binary):
                return None

            # Read left 6 digits
            left_digits = []
            left_types = []
            for d in range(6):
                segment = binary[pos:pos + 7]
                if len(segment) < 7:
                    return None
                pattern = ''.join(str(b) for b in segment)

                found = False
                for digit in range(10):
                    if L[digit] == pattern:
                        left_digits.append(digit)
                        left_types.append('L')
                        found = True
                        break
                    if G[digit] == pattern:
                        left_digits.append(digit)
                        left_types.append('G')
                        found = True
                        break

                if not found:
                    return None
                pos += 7

            # Skip middle guard (5 modules: 01010)
            pos += 5

            # Read right 6 digits
            right_digits = []
            for d in range(6):
                segment = binary[pos:pos + 7]
                if len(segment) < 7:
                    return None
                pattern = ''.join(str(b) for b in segment)

                found = False
                for digit in range(10):
                    if R[digit] == pattern:
                        right_digits.append(digit)
                        found = True
                        break

                if not found:
                    return None
                pos += 7

            # Get first digit from encoding pattern
            type_pattern = ''.join(left_types)
            first_digit = None
            for fd in range(10):
                if FIRST[fd] == type_pattern:
                    first_digit = fd
                    break

            if first_digit is None:
                return None

            # Build barcode
            all_digits = [first_digit] + left_digits + right_digits
            barcode = ''.join(str(d) for d in all_digits)

            # Verify checksum
            if len(barcode) == 13:
                digits = [int(c) for c in barcode]
                total = sum(digits[i] * (1 if i % 2 == 0 else 3) for i in range(12))
                check = (10 - (total % 10)) % 10
                if check == digits[12]:
                    return barcode

            return None
        except Exception:
            return None