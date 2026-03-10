// Global variables
let loadingModal;
let autoUpdateInterval;
let isAutoCapturing = false;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    
    // Mode switching
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', switchMode);
    });
    
    // Capture mode switching
    document.querySelectorAll('input[name="captureMode"]').forEach(radio => {
        radio.addEventListener('change', switchCaptureMode);
    });
    
    // Load initial counts
    updateCounters();
    
    // Check initial status
    checkAutoStatus();
    
    // Check Arduino status
    checkArduinoStatus();
});

function switchMode() {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const cameraControls = document.getElementById('cameraControls');
    const uploadControls = document.getElementById('uploadControls');
    
    if (mode === 'camera') {
        cameraControls.style.display = 'block';
        uploadControls.style.display = 'none';
    } else {
        cameraControls.style.display = 'none';
        uploadControls.style.display = 'block';
        // Stop auto capture if switching away from camera mode
        if (isAutoCapturing) {
            stopAutoCapture();
        }
    }
}

function switchCaptureMode() {
    const mode = document.querySelector('input[name="captureMode"]:checked').value;
    const manualControls = document.getElementById('manualControls');
    const autoControls = document.getElementById('autoControls');
    
    if (mode === 'manual') {
        manualControls.style.display = 'block';
        autoControls.style.display = 'none';
        // Stop auto capture if switching to manual
        if (isAutoCapturing) {
            stopAutoCapture();
        }
    } else {
        manualControls.style.display = 'none';
        autoControls.style.display = 'block';
    }
}

function showStatus(message, type = 'info') {
    const statusDiv = document.getElementById('statusMessage');
    statusDiv.className = `alert alert-${type}`;
    statusDiv.innerHTML = `<i class="fas fa-${getIcon(type)}"></i> ${message}`;
}

function getIcon(type) {
    const icons = {
        'info': 'info-circle',
        'success': 'check-circle',
        'danger': 'exclamation-circle',
        'warning': 'exclamation-triangle'
    };
    return icons[type] || 'info-circle';
}

function showPrediction(prediction, confidence) {
    const resultDiv = document.getElementById('predictionResult');
    let className, icon;
    
    if (prediction.includes('Good_Bolt')) {
        className = 'prediction-good';
        icon = 'check-circle';
    } else if (prediction.includes('Defective_Bolt')) {
        className = 'prediction-defective';
        icon = 'exclamation-triangle';
    } else {
        className = 'prediction-none';
        icon = 'info-circle';
    }
    
    resultDiv.className = `prediction-result ${className}`;
    resultDiv.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <strong>Prediction:</strong> ${prediction}
        ${confidence > 0 ? `<br><strong>Confidence:</strong> ${(confidence * 100).toFixed(1)}%` : ''}
    `;
    resultDiv.style.display = 'block';
}

function updateCounters() {
    fetch('/get_counts')
        .then(response => response.json())
        .then(data => {
            document.getElementById('goodCount').textContent = data.good;
            document.getElementById('defectiveCount').textContent = data.defective;
            document.getElementById('totalCount').textContent = data.total;
        })
        .catch(error => {
            console.error('Error updating counters:', error);
        });
}

function updateCountersFromData(data) {
    document.getElementById('goodCount').textContent = data.total_good;
    document.getElementById('defectiveCount').textContent = data.total_defective;
        if (data.total_count !== undefined) document.getElementById('totalCount').textContent = data.total_count;
    if (data.total_count !== undefined) {
        document.getElementById('totalCount').textContent = data.total_count;
    }
}

function testCamera() {
    const cameraIndex = document.getElementById('cameraSelect').value;
    
    showStatus('Testing camera...', 'info');
    
    fetch('/test_camera', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: parseInt(cameraIndex)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus(data.message, 'success');
        } else {
            showStatus(data.message, 'danger');
        }
    })
    .catch(error => {
        showStatus('Error testing camera: ' + error.message, 'danger');
    });
}

function captureFrame() {
    const cameraIndex = document.getElementById('cameraSelect').value;
    
    loadingModal.show();
    showStatus('Capturing from camera...', 'info');
    
    fetch('/capture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: parseInt(cameraIndex)
        })
    })
    .then(response => response.json())
    .then(data => {
        loadingModal.hide();
        
        if (data.error) {
            showStatus('Error: ' + data.error, 'danger');
            return;
        }
        
        // Display images
        displayImages(data.original_image, data.processed_image);
        
        // Show prediction
        showPrediction(data.prediction, data.confidence);
        
        // Update counters
        document.getElementById('goodCount').textContent = data.total_good;
        document.getElementById('defectiveCount').textContent = data.total_defective;
        if (data.total_count !== undefined) document.getElementById('totalCount').textContent = data.total_count;
        
        // Show detection summary
        let summary = 'Detection completed. ';
        if (data.good_count > 0) {
            summary += `Found ${data.good_count} good bolt(s). `;
        }
        if (data.defective_count > 0) {
            summary += `Found ${data.defective_count} defective bolt(s). `;
        }
        if (data.good_count === 0 && data.defective_count === 0) {
            summary += 'No bolts detected.';
        }
        
        showStatus(summary, 'success');
    })
    .catch(error => {
        loadingModal.hide();
        showStatus('Error capturing frame: ' + error.message, 'danger');
    });
}

function uploadImage() {
    const fileInput = document.getElementById('imageUpload');
    const file = fileInput.files[0];
    
    if (!file) {
        showStatus('Please select an image file', 'warning');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    loadingModal.show();
    showStatus('Processing uploaded image...', 'info');
    
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loadingModal.hide();
        
        if (data.error) {
            showStatus('Error: ' + data.error, 'danger');
            return;
        }
        
        // Display images
        displayImages(data.original_image, data.processed_image);
        
        // Show prediction
        showPrediction(data.prediction, data.confidence);
        
        // Update counters
        document.getElementById('goodCount').textContent = data.total_good;
        document.getElementById('defectiveCount').textContent = data.total_defective;
        if (data.total_count !== undefined) document.getElementById('totalCount').textContent = data.total_count;
        
        // Show detection summary
        let summary = 'Detection completed. ';
        if (data.good_count > 0) {
            summary += `Found ${data.good_count} good bolt(s). `;
        }
        if (data.defective_count > 0) {
            summary += `Found ${data.defective_count} defective bolt(s). `;
        }
        if (data.good_count === 0 && data.defective_count === 0) {
            summary += 'No bolts detected.';
        }
        
        showStatus(summary, 'success');
    })
    .catch(error => {
        loadingModal.hide();
        showStatus('Error processing image: ' + error.message, 'danger');
    });
}

function displayImages(originalBase64, processedBase64) {
    // Display original image
    const originalContainer = document.getElementById('originalImageContainer');
    originalContainer.innerHTML = `<img src="${originalBase64}" alt="Original Image" class="img-fluid">`;
    
    // Display processed image
    const processedContainer = document.getElementById('processedImageContainer');
    processedContainer.innerHTML = `<img src="${processedBase64}" alt="Detection Result" class="img-fluid">`;
}

function startAutoCapture() {
    const cameraIndex = document.getElementById('cameraSelect').value;
    
    showStatus('Starting auto capture...', 'info');
    
    fetch('/start_auto_capture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            camera_index: parseInt(cameraIndex)
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            isAutoCapturing = true;
            document.getElementById('startAutoBtn').style.display = 'none';
            document.getElementById('stopAutoBtn').style.display = 'block';
            document.getElementById('autoStatus').style.display = 'block';
            
            showStatus('Auto capturing started', 'success');
            
            // Start polling for updates
            startAutoUpdate();
        } else {
            showStatus('Error: ' + (data.error || 'Failed to start auto capture'), 'danger');
        }
    })
    .catch(error => {
        showStatus('Error starting auto capture: ' + error.message, 'danger');
    });
}

function stopAutoCapture() {
    showStatus('Stopping auto capture...', 'info');
    
    fetch('/stop_auto_capture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            isAutoCapturing = false;
            document.getElementById('startAutoBtn').style.display = 'block';
            document.getElementById('stopAutoBtn').style.display = 'none';
            document.getElementById('autoStatus').style.display = 'none';
            
            showStatus('Auto capture stopped', 'info');
            
            // Stop polling for updates
            stopAutoUpdate();
        } else {
            showStatus('Error: ' + (data.error || 'Failed to stop auto capture'), 'danger');
        }
    })
    .catch(error => {
        showStatus('Error stopping auto capture: ' + error.message, 'danger');
    });
}

function startAutoUpdate() {
    // Poll for new detection data every 0.5 seconds
    autoUpdateInterval = setInterval(() => {
        if (isAutoCapturing) {
            fetch('/get_latest_detection')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        // Update images
                        displayImages(data.original_image, data.processed_image);
                        
                        // Show prediction
                        showPrediction(data.prediction, data.confidence);
                        
                        // Update counters
                        document.getElementById('goodCount').textContent = data.total_good;
                        document.getElementById('defectiveCount').textContent = data.total_defective;
        if (data.total_count !== undefined) document.getElementById('totalCount').textContent = data.total_count;
                        
                        // Show detection summary with timestamp
                        const timestamp = new Date(data.timestamp * 1000).toLocaleTimeString();
                        let summary = `Last detection (${timestamp}): `;
                        
                        if (data.good_count > 0) {
                            summary += `${data.good_count} good bolt(s) `;
                        }
                        if (data.defective_count > 0) {
                            summary += `${data.defective_count} defective bolt(s) `;
                        }
                        if (data.good_count === 0 && data.defective_count === 0) {
                            summary += 'No bolts detected';
                        }
                        
                        showStatus(summary, 'success');
                    }
                })
                .catch(error => {
                    console.error('Error getting latest detection:', error);
                });
        }
    }, 500);
}

function stopAutoUpdate() {
    if (autoUpdateInterval) {
        clearInterval(autoUpdateInterval);
        autoUpdateInterval = null;
    }
}

function checkAutoStatus() {
    fetch('/get_status')
        .then(response => response.json())
        .then(data => {
            if (data.auto_capture_running) {
                isAutoCapturing = true;
                document.getElementById('autoMode').checked = true;
                switchCaptureMode();
                document.getElementById('startAutoBtn').style.display = 'none';
                document.getElementById('stopAutoBtn').style.display = 'block';
                document.getElementById('autoStatus').style.display = 'block';
                startAutoUpdate();
                showStatus('Auto capture is running', 'success');
            }
        })
        .catch(error => {
            console.error('Error checking auto status:', error);
        });
}

function connectArduino() {
    const port = document.getElementById('arduinoPort').value;
    
    showStatus('Connecting to Arduino...', 'info');
    
    fetch('/connect_arduino', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            port: port
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus(data.message, 'success');
            updateArduinoStatus(true, port);
        } else {
            showStatus(data.message, 'danger');
            updateArduinoStatus(false, port);
        }
    })
    .catch(error => {
        showStatus('Error connecting to Arduino: ' + error.message, 'danger');
    });
}

function disconnectArduino() {
    showStatus('Disconnecting from Arduino...', 'info');
    
    fetch('/disconnect_arduino', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus(data.message, 'info');
            updateArduinoStatus(false);
            document.getElementById('enableArduino').checked = false;
        } else {
            showStatus(data.message, 'danger');
        }
    })
    .catch(error => {
        showStatus('Error disconnecting from Arduino: ' + error.message, 'danger');
    });
}

function toggleArduino() {
    const enabled = document.getElementById('enableArduino').checked;
    
    fetch('/toggle_arduino', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            enable: enabled
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const status = enabled ? 'enabled' : 'disabled';
            showStatus(`Arduino communication ${status}`, 'info');
        }
    })
    .catch(error => {
        showStatus('Error toggling Arduino: ' + error.message, 'danger');
    });
}

function testArduino(signal) {
    fetch('/test_arduino', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            signal: signal
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus(data.message, 'success');
        } else {
            showStatus(data.message, 'danger');
        }
    })
    .catch(error => {
        showStatus('Error testing Arduino: ' + error.message, 'danger');
    });
}

function updateArduinoStatus(connected, port = '') {
    const statusDiv = document.getElementById('arduinoStatus');
    
    if (connected) {
        statusDiv.className = 'alert alert-success py-2';
        statusDiv.innerHTML = `<small><i class="fas fa-circle text-success"></i> Connected to ${port}</small>`;
    } else {
        statusDiv.className = 'alert alert-secondary py-2';
        statusDiv.innerHTML = '<small><i class="fas fa-circle text-secondary"></i> Not Connected</small>';
    }
}

function checkArduinoStatus() {
    fetch('/get_arduino_status')
        .then(response => response.json())
        .then(data => {
            updateArduinoStatus(data.connected, data.port);
            document.getElementById('enableArduino').checked = data.enabled;
            if (data.port) {
                document.getElementById('arduinoPort').value = data.port;
            }
        })
        .catch(error => {
            console.error('Error checking Arduino status:', error);
        });
}

function resetCounters() {
    if (confirm('Are you sure you want to reset the counters?')) {
        fetch('/reset_counters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('goodCount').textContent = '0';
                document.getElementById('defectiveCount').textContent = '0';
                document.getElementById('totalCount').textContent = '0';
                showStatus('Counters reset successfully', 'success');
            }
        })
        .catch(error => {
            showStatus('Error resetting counters: ' + error.message, 'danger');
        });
    }
}