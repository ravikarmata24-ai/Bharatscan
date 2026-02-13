/**
 * 🇮🇳 BharatScan - Camera & Barcode Scanner Module
 * Handles camera access, frame capture, and barcode scanning
 */

let cameraStream = null;
let scanInterval = null;
let isScanning = false;

// ==================== CAMERA FUNCTIONS ====================

async function startCamera() {
    const video = document.getElementById('camera-feed');
    const startBtn = document.getElementById('startCameraBtn');
    const captureBtn = document.getElementById('captureBtn');
    const stopBtn = document.getElementById('stopCameraBtn');
    const status = document.getElementById('camera-status');

    try {
        // Request camera with preference for back camera (better for barcode scanning)
        const constraints = {
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 1280 },
                height: { ideal: 720 },
                focusMode: { ideal: 'continuous' },
            }
        };

        cameraStream = await navigator.mediaDevices.getUserMedia(constraints);
        video.srcObject = cameraStream;
        
        await video.play();

        // Update UI
        startBtn.style.display = 'none';
        captureBtn.style.display = 'inline-block';
        stopBtn.style.display = 'inline-block';
        status.innerHTML = `
            <p class="text-success">
                <i class="bi bi-camera-fill"></i> Camera active - Position barcode in the frame
            </p>
        `;

        // Start auto-scanning every 1.5 seconds
        startAutoScan();

    } catch (err) {
        console.error('Camera error:', err);
        status.innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Camera Error:</strong> ${getCameraErrorMessage(err)}
            </div>
            <p class="text-muted mt-2">
                You can use the <strong>Upload Image</strong> or <strong>Manual Entry</strong> tabs instead.
            </p>
        `;
    }
}

function stopCamera() {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
        cameraStream = null;
    }

    stopAutoScan();

    const video = document.getElementById('camera-feed');
    video.srcObject = null;

    // Reset UI
    document.getElementById('startCameraBtn').style.display = 'inline-block';
    document.getElementById('captureBtn').style.display = 'none';
    document.getElementById('stopCameraBtn').style.display = 'none';
    document.getElementById('camera-status').innerHTML = `
        <p class="text-muted">
            <i class="bi bi-info-circle"></i> Camera stopped. Click "Start Camera" to scan again.
        </p>
    `;
}

function startAutoScan() {
    if (scanInterval) clearInterval(scanInterval);
    isScanning = true;
    
    scanInterval = setInterval(() => {
        if (isScanning) {
            captureFrame(true); // silent mode
        }
    }, 1500);
}

function stopAutoScan() {
    isScanning = false;
    if (scanInterval) {
        clearInterval(scanInterval);
        scanInterval = null;
    }
}

async function captureFrame(silent = false) {
    const video = document.getElementById('camera-feed');
    const canvas = document.getElementById('camera-canvas');
    const status = document.getElementById('camera-status');

    if (!video.srcObject) {
        if (!silent) {
            showNotification('Camera is not active. Please start the camera first.', 'warning');
        }
        return;
    }

    // Draw current frame to canvas
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);

    // Convert to blob
    canvas.toBlob(async (blob) => {
        if (!blob) return;

        const formData = new FormData();
        formData.append('frame', blob, 'frame.jpg');

        try {
            if (!silent) {
                status.innerHTML = `
                    <div class="d-flex align-items-center justify-content-center gap-2">
                        <div class="spinner-border spinner-border-sm text-warning" role="status"></div>
                        <span>Scanning barcode...</span>
                    </div>
                `;
            }

            const response = await fetch('/api/scan/camera', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json();

            if (data.found && data.scan) {
                // Barcode detected!
                stopAutoScan();
                
                const barcode = data.scan.barcode;
                
                status.innerHTML = `
                    <div class="alert alert-success">
                        <i class="bi bi-check-circle-fill"></i>
                        <strong>Barcode Detected!</strong> ${barcode}
                        ${data.scan.is_indian ? '<span class="badge bg-warning text-dark ms-2">🇮🇳 Indian Product</span>' : ''}
                    </div>
                `;

                // Play success sound
                playBeep();

                // Redirect to result page after short delay
                setTimeout(() => {
                    window.location.href = `/result/${barcode}`;
                }, 1000);
            } else if (!silent) {
                status.innerHTML = `
                    <p class="text-warning">
                        <i class="bi bi-exclamation-circle"></i> 
                        No barcode detected. Try adjusting the position or lighting.
                    </p>
                `;
            }
        } catch (err) {
            console.error('Scan error:', err);
            if (!silent) {
                status.innerHTML = `
                    <p class="text-danger">
                        <i class="bi bi-exclamation-triangle"></i> Scan error. Please try again.
                    </p>
                `;
            }
        }
    }, 'image/jpeg', 0.85);
}

// ==================== HELPER FUNCTIONS ====================

function getCameraErrorMessage(error) {
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        return 'Camera permission denied. Please allow camera access in your browser settings.';
    } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        return 'No camera found on this device.';
    } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
        return 'Camera is being used by another application.';
    } else if (error.name === 'OverconstrainedError') {
        return 'Camera does not meet the required constraints.';
    } else if (error.name === 'NotSupportedError') {
        return 'Camera is not supported in this browser. Try using Chrome or Firefox.';
    }
    return `Unexpected error: ${error.message}`;
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
        // Audio not supported, silently ignore
    }
}

function showNotification(message, type = 'info') {
    const container = document.querySelector('main') || document.body;
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-5`;
    alert.style.zIndex = '10000';
    alert.style.maxWidth = '500px';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alert);

    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 300);
    }, 4000);
}

// ==================== CLEANUP ====================

// Stop camera when leaving page
window.addEventListener('beforeunload', () => {
    if (cameraStream) {
        cameraStream.getTracks().forEach(track => track.stop());
    }
});

// Stop camera when tab is hidden (save battery)
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isScanning) {
        stopAutoScan();
    } else if (!document.hidden && cameraStream) {
        startAutoScan();
    }
});