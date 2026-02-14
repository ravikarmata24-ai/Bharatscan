import io


class ImageBarcodeScanner:
    """
    Server-side barcode scanner.
    Uses pyzbar (powerful, finds barcodes in complex images).
    Falls back to pure Python if pyzbar not available.
    """

    def scan_image_bytes(self, image_bytes):
        """
        Scan image bytes for barcodes.
        Returns (barcode_string, None) on success.
        Returns (None, error_message) on failure.
        """
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
        except ImportError:
            return None, 'Pillow not installed'
        except Exception as e:
            return None, 'Cannot open image: ' + str(e)

        # Try pyzbar first (best barcode scanner)
        barcode = self._try_pyzbar(img)
        if barcode:
            return barcode, None

        # Try pyzbar with preprocessed image
        barcode = self._try_pyzbar_enhanced(img)
        if barcode:
            return barcode, None

        # Try pyzbar on cropped regions
        barcode = self._try_pyzbar_regions(img)
        if barcode:
            return barcode, None

        # Try pyzbar on scaled versions
        barcode = self._try_pyzbar_scaled(img)
        if barcode:
            return barcode, None

        # Try pyzbar on rotated image
        barcode = self._try_pyzbar_rotated(img)
        if barcode:
            return barcode, None

        # Fallback: pure Python line scanner
        barcode = self._try_pure_python(img)
        if barcode:
            return barcode, None

        return None, 'No barcode detected. Try a clearer photo with the barcode more visible.'

    def _try_pyzbar(self, img):
        """Try scanning with pyzbar on original image."""
        try:
            from pyzbar.pyzbar import decode
            from pyzbar.pyzbar import ZBarSymbol

            # Try with all barcode types
            results = decode(img, symbols=[
                ZBarSymbol.EAN13,
                ZBarSymbol.EAN8,
                ZBarSymbol.UPCA,
                ZBarSymbol.UPCE,
                ZBarSymbol.CODE128,
                ZBarSymbol.CODE39,
                ZBarSymbol.QRCODE
            ])

            if results:
                return results[0].data.decode('utf-8')

            # Try without specifying symbols (detect any barcode)
            results = decode(img)
            if results:
                return results[0].data.decode('utf-8')

            return None
        except ImportError:
            return None
        except Exception:
            return None

    def _try_pyzbar_enhanced(self, img):
        """Try scanning with enhanced contrast."""
        try:
            from pyzbar.pyzbar import decode
            from PIL import ImageEnhance, ImageFilter

            # Method 1: High contrast
            enhancer = ImageEnhance.Contrast(img)
            high_contrast = enhancer.enhance(2.0)
            results = decode(high_contrast)
            if results:
                return results[0].data.decode('utf-8')

            # Method 2: Sharpen
            sharpened = img.filter(ImageFilter.SHARPEN)
            results = decode(sharpened)
            if results:
                return results[0].data.decode('utf-8')

            # Method 3: Convert to grayscale and threshold
            gray = img.convert('L')
            # Try multiple thresholds
            for threshold in [100, 120, 140, 160]:
                bw = gray.point(lambda x: 255 if x > threshold else 0, '1')
                results = decode(bw)
                if results:
                    return results[0].data.decode('utf-8')

            # Method 4: High sharpness + contrast
            sharp = img.filter(ImageFilter.SHARPEN)
            sharp = sharp.filter(ImageFilter.SHARPEN)
            enhancer2 = ImageEnhance.Contrast(sharp)
            sharp_contrast = enhancer2.enhance(2.5)
            results = decode(sharp_contrast)
            if results:
                return results[0].data.decode('utf-8')

            # Method 5: Increase brightness then contrast
            bright = ImageEnhance.Brightness(img).enhance(1.3)
            bright_contrast = ImageEnhance.Contrast(bright).enhance(2.0)
            results = decode(bright_contrast)
            if results:
                return results[0].data.decode('utf-8')

            return None
        except ImportError:
            return None
        except Exception:
            return None

    def _try_pyzbar_regions(self, img):
        """Try scanning different cropped regions of the image."""
        try:
            from pyzbar.pyzbar import decode

            width, height = img.size

            # Define regions where barcodes are commonly found
            regions = [
                # Bottom half
                (0, height // 2, width, height),
                # Bottom third
                (0, int(height * 0.65), width, height),
                # Top half
                (0, 0, width, height // 2),
                # Center 60%
                (int(width * 0.1), int(height * 0.2), int(width * 0.9), int(height * 0.8)),
                # Center bottom
                (int(width * 0.1), int(height * 0.4), int(width * 0.9), height),
                # Left half
                (0, 0, width // 2, height),
                # Right half
                (width // 2, 0, width, height),
                # Bottom left quarter
                (0, height // 2, width // 2, height),
                # Bottom right quarter
                (width // 2, height // 2, width, height),
                # Center strip (horizontal)
                (0, int(height * 0.3), width, int(height * 0.7)),
                # Center strip (narrow)
                (int(width * 0.05), int(height * 0.35), int(width * 0.95), int(height * 0.65)),
                # Bottom strip
                (0, int(height * 0.6), width, int(height * 0.9)),
                # Top left quarter
                (0, 0, width // 2, height // 2),
                # Top right quarter
                (width // 2, 0, width, height // 2),
                # Middle third horizontal
                (int(width * 0.15), int(height * 0.25), int(width * 0.85), int(height * 0.75)),
            ]

            for region in regions:
                try:
                    cropped = img.crop(region)
                    results = decode(cropped)
                    if results:
                        return results[0].data.decode('utf-8')

                    # Also try enhanced version of crop
                    from PIL import ImageEnhance
                    enhanced = ImageEnhance.Contrast(cropped).enhance(2.0)
                    results = decode(enhanced)
                    if results:
                        return results[0].data.decode('utf-8')
                except Exception:
                    continue

            return None
        except ImportError:
            return None
        except Exception:
            return None

    def _try_pyzbar_scaled(self, img):
        """Try scanning at different scales (zoom in/out)."""
        try:
            from pyzbar.pyzbar import decode

            width, height = img.size

            # Try scaling up (for small barcodes in large photos)
            for scale in [1.5, 2.0, 2.5, 3.0, 0.75, 0.5]:
                try:
                    new_w = int(width * scale)
                    new_h = int(height * scale)

                    # Don't make image too large
                    if new_w > 4000 or new_h > 4000:
                        continue
                    if new_w < 100 or new_h < 100:
                        continue

                    from PIL import Image
                    scaled = img.resize((new_w, new_h), Image.LANCZOS)
                    results = decode(scaled)
                    if results:
                        return results[0].data.decode('utf-8')
                except Exception:
                    continue

            return None
        except ImportError:
            return None
        except Exception:
            return None

    def _try_pyzbar_rotated(self, img):
        """Try scanning rotated versions."""
        try:
            from pyzbar.pyzbar import decode

            for angle in [90, 180, 270]:
                try:
                    rotated = img.rotate(angle, expand=True)
                    results = decode(rotated)
                    if results:
                        return results[0].data.decode('utf-8')
                except Exception:
                    continue

            return None
        except ImportError:
            return None
        except Exception:
            return None

    def _try_pure_python(self, img):
        """Fallback: Pure Python line-by-line EAN-13 scanner."""
        try:
            gray = img.convert('L')
            width, height = gray.size
            pixels = list(gray.getdata())

            barcodes_found = {}

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

            if barcodes_found:
                return max(barcodes_found, key=barcodes_found.get)

            return None
        except Exception:
            return None

    def _otsu_threshold(self, pixels):
        """Calculate Otsu's threshold."""
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
        """Find EAN-13 barcode in binary line."""
        L = ['0001101', '0011001', '0010011', '0111101', '0100011',
             '0110001', '0101111', '0111011', '0110111', '0001011']
        G = ['0100111', '0110011', '0011011', '0100001', '0011101',
             '0111001', '0000101', '0010001', '0001001', '0010111']
        R = ['1110010', '1100110', '1101100', '1000010', '1011100',
             '1001110', '1010000', '1000100', '1001000', '1110100']
        FIRST = ['LLLLLL', 'LLGLGG', 'LLGGLG', 'LLGGGL', 'LGLLGG',
                 'LGGLLG', 'LGGGLL', 'LGLGLG', 'LGLGGL', 'LGGLGL']

        if len(binary) < 95:
            return None

        for i in range(len(binary) - 95):
            if binary[i] == 1 and binary[i + 1] == 0 and binary[i + 2] == 1:
                result = self._try_decode(binary, i, L, G, R, FIRST)
                if result:
                    return result
        return None

    def _try_decode(self, binary, start, L, G, R, FIRST):
        """Try to decode EAN-13 from position."""
        try:
            pos = start + 3

            if pos + 42 + 5 + 42 + 3 > len(binary):
                return None

            left_digits = []
            left_types = []
            for d in range(6):
                pattern = ''.join(str(binary[pos + j]) for j in range(7))
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

            pos += 5

            right_digits = []
            for d in range(6):
                pattern = ''.join(str(binary[pos + j]) for j in range(7))
                found = False
                for digit in range(10):
                    if R[digit] == pattern:
                        right_digits.append(digit)
                        found = True
                        break
                if not found:
                    return None
                pos += 7

            type_pattern = ''.join(left_types)
            first_digit = None
            for fd in range(10):
                if FIRST[fd] == type_pattern:
                    first_digit = fd
                    break

            if first_digit is None:
                return None

            all_digits = [first_digit] + left_digits + right_digits
            barcode = ''.join(str(d) for d in all_digits)

            if len(barcode) == 13:
                digits = [int(c) for c in barcode]
                total = sum(digits[i] * (1 if i % 2 == 0 else 3) for i in range(12))
                check = (10 - (total % 10)) % 10
                if check == digits[12]:
                    return barcode

            return None
        except Exception:
            return None