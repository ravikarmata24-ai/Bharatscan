/**
 * 🇮🇳 BharatScan - Main Application JavaScript
 * Handles upload scanning, manual entry, search, and UI interactions
 */

document.addEventListener('DOMContentLoaded', function () {
    initUploadHandlers();
    initManualSearch();
    initDragAndDrop();
});

// ==================== IMAGE UPLOAD SCANNING ====================

function initUploadHandlers() {
    const uploadForm = document.getElementById('uploadForm');
    const imageInput = document.getElementById('imageInput');

    if (imageInput) {
        imageInput.addEventListener('change', function (e) {
            handleFileSelect(e.target.files[0]);
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitUploadScan();
        });
    }
}

function handleFileSelect(file) {
    if (!file) return;

    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        showNotification('Invalid file type. Please upload an image (PNG, JPG, GIF, BMP, WebP).', 'danger');
        return;
    }

    if (file.size > 16 * 1024 * 1024) {
        showNotification('File too large. Maximum size is 16MB.', 'danger');
        return;
    }

    // Show preview
    const reader = new FileReader();
    reader.onload = function (e) {
        const preview = document.getElementById('imagePreview');
        const previewImg = document.getElementById('previewImg');
        if (preview && previewImg) {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
        }
        // Hide upload zone
        const dropZone = document.getElementById('dropZone');
        if (dropZone) dropZone.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

function clearUpload() {
    const imageInput = document.getElementById('imageInput');
    const preview = document.getElementById('imagePreview');
    const dropZone = document.getElementById('dropZone');

    if (imageInput) imageInput.value = '';
    if (preview) preview.style.display = 'none';
    if (dropZone) dropZone.style.display = 'block';
}

async function submitUploadScan() {
    const imageInput = document.getElementById('imageInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const resultDiv = document.getElementById('uploadResult');

    if (!imageInput || !imageInput.files[0]) {
        showNotification('Please select an image first.', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('image', imageInput.files[0]);

    // Show loading state
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status"></span>
            Scanning...
        `;
    }

    try {
        const response = await fetch('/api/scan/upload', {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (response.ok && data.scan) {
            const barcode = data.scan.barcode;
            
            showNotification(`✅ Barcode detected: ${barcode}`, 'success');
            playBeep();

            // Redirect to result
            setTimeout(() => {
                window.location.href = `/result/${barcode}`;
            }, 800);
        } else {
            const errorMsg = data.error || 'Could not detect barcode in the image.';
            
            if (resultDiv) {
                resultDiv.innerHTML = `
                    <div class="alert alert-warning mt-3">
                        <i class="bi bi-exclamation-triangle"></i>
                        <strong>Scan Failed:</strong> ${errorMsg}
                        <br><small class="text-muted mt-1 d-block">
                            Tips: Ensure the barcode is clearly visible, well-lit, and not blurry.
                        </small>
                    </div>
                `;
                resultDiv.style.display = 'block';
            } else {
                showNotification(errorMsg, 'warning');
            }
        }
    } catch (err) {
        console.error('Upload scan error:', err);
        showNotification('Network error. Please check your connection and try again.', 'danger');
    } finally {
        if (uploadBtn) {
            uploadBtn.disabled = false;
            uploadBtn.innerHTML = '<i class="bi bi-search"></i> Scan Barcode from Image';
        }
    }
}

// ==================== DRAG AND DROP ====================

function initDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            const imageInput = document.getElementById('imageInput');
            if (imageInput) {
                // Create a new DataTransfer to set files
                const dt = new DataTransfer();
                dt.items.add(files[0]);
                imageInput.files = dt.files;
            }
            handleFileSelect(files[0]);
        }
    }, false);

    // Click to upload
    dropZone.addEventListener('click', () => {
        const imageInput = document.getElementById('imageInput');
        if (imageInput) imageInput.click();
    });
}

// ==================== MANUAL BARCODE ENTRY ====================

function initManualSearch() {
    const manualForm = document.getElementById('manualForm');
    if (manualForm) {
        manualForm.addEventListener('submit', function (e) {
            e.preventDefault();
            submitManualSearch();
        });
    }
}

async function submitManualSearch() {
    const barcodeInput = document.getElementById('manualBarcode');
    const searchBtn = document.getElementById('manualSearchBtn');
    const resultDiv = document.getElementById('manualResult');

    if (!barcodeInput) return;

    const barcode = barcodeInput.value.trim();

    if (!barcode) {
        showNotification('Please enter a barcode number.', 'warning');
        barcodeInput.focus();
        return;
    }

    // Validate basic format
    if (!/^[A-Za-z0-9\-\.]+$/.test(barcode)) {
        showNotification('Invalid barcode format. Use only numbers, letters, hyphens, and dots.', 'danger');
        return;
    }

    // Show loading
    if (searchBtn) {
        searchBtn.disabled = true;
        searchBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm" role="status"></span>
            Searching...
        `;
    }

    try {
        const response = await fetch('/api/scan/manual', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ barcode: barcode }),
        });

        const data = await response.json();

        if (response.ok) {
            if (data.product && data.product.found) {
                // Redirect to result page
                window.location.href = `/result/${barcode}`;
            } else {
                // Show not found with barcode info
                displayManualResult(data, barcode, resultDiv);
            }
        } else {
            showNotification(data.error || 'Error looking up barcode.', 'danger');
        }
    } catch (err) {
        console.error('Manual search error:', err);
        showNotification('Network error. Please check your connection.', 'danger');
    } finally {
        if (searchBtn) {
            searchBtn.disabled = false;
            searchBtn.innerHTML = '<i class="bi bi-search"></i> Search Product';
        }
    }
}

function displayManualResult(data, barcode, container) {
    if (!container) {
        // Redirect anyway - the result page handles not-found state
        window.location.href = `/result/${barcode}`;
        return;
    }

    const barcodeInfo = data.barcode_info || {};
    const isIndian = barcodeInfo.is_indian || false;

    container.innerHTML = `
        <div class="card mt-3 border-warning">
            <div class="card-body">
                <h5 class="card-title text-warning">
                    <i class="bi bi-exclamation-circle"></i> Product Not Found
                </h5>
                <p>No product found for barcode: <strong>${barcode}</strong></p>
                <div class="row g-2 mb-3">
                    <div class="col-auto">
                        <span class="badge bg-secondary">Length: ${barcodeInfo.length || barcode.length}</span>
                    </div>
                    ${barcodeInfo.country ? `
                        <div class="col-auto">
                            <span class="badge ${isIndian ? 'bg-warning text-dark' : 'bg-info'}">
                                ${isIndian ? '🇮🇳' : '🌍'} ${barcodeInfo.country}
                            </span>
                        </div>
                    ` : ''}
                    ${barcodeInfo.gs1_prefix ? `
                        <div class="col-auto">
                            <span class="badge bg-light text-dark">GS1: ${barcodeInfo.gs1_prefix}</span>
                        </div>
                    ` : ''}
                </div>
                <a href="/result/${barcode}" class="btn btn-sm btn-outline-warning">
                    View Details →
                </a>
            </div>
        </div>
    `;
    container.style.display = 'block';
}

// ==================== PRODUCT SEARCH ====================

async function searchProducts(query, category = null) {
    try {
        let url = `/api/search?q=${encodeURIComponent(query)}`;
        if (category) url += `&category=${encodeURIComponent(category)}`;

        const response = await fetch(url);
        const data = await response.json();
        return data.results || [];
    } catch (err) {
        console.error('Search error:', err);
        return [];
    }
}

// ==================== FSSAI LICENSE VERIFICATION ====================

async function verifyFSSAI(licenseNumber) {
    try {
        const response = await fetch(`/api/fssai/verify/${licenseNumber}`);
        const data = await response.json();
        return data;
    } catch (err) {
        console.error('FSSAI verification error:', err);
        return null;
    }
}

// ==================== MEDICINE ALTERNATIVES ====================

async function findAlternatives(brand, composition) {
    try {
        const response = await fetch('/api/medicine/alternatives', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand, composition }),
        });
        const data = await response.json();
        return data;
    } catch (err) {
        console.error('Alternatives search error:', err);
        return null;
    }
}

// ==================== UTILITY FUNCTIONS ====================

function showNotification(message, type = 'info') {
    // Prevent duplicate
    const existing = document.querySelector('.floating-notification');
    if (existing) existing.remove();

    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show floating-notification`;
    alert.style.cssText = `
        position: fixed;
        top: 80px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 10000;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        animation: slideDown 0.3s ease;
    `;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(alert);

    setTimeout(() => {
        if (alert.parentNode) {
            alert.classList.remove('show');
            setTimeout(() => alert.remove(), 300);
        }
    }, 5000);
}

function playBeep() {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.frequency.value = 1200;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3;

        oscillator.start();
        setTimeout(() => {
            oscillator.stop();
            audioCtx.close();
        }, 200);
    } catch (e) {
        // Silent fail
    }
}

function formatPrice(price) {
    if (price === null || price === undefined) return 'N/A';
    return `₹${parseFloat(price).toFixed(2)}`;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function getCategoryIcon(category) {
    const icons = {
        'food': '🍽️',
        'medicine': '💊',
        'nutraceutical': '🌿',
        'skincare': '🧴',
        'haircare': '💇',
    };
    return icons[category] || '📦';
}

function getCategoryColor(category) {
    const colors = {
        'food': 'success',
        'medicine': 'primary',
        'nutraceutical': 'info',
        'skincare': 'warning',
        'haircare': 'secondary',
    };
    return colors[category] || 'dark';
}

// Add slide down animation CSS dynamically
const style = document.createElement('style');
style.textContent = `
    @keyframes slideDown {
        from {
            opacity: 0;
            transform: translateX(-50%) translateY(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
    }
`;
document.head.appendChild(style);