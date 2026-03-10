from flask import Flask, render_template, request, jsonify, Response
import cv2
import numpy as np
from PIL import Image
import base64
import io
import json
from ultralytics import YOLO
import threading
import time
import serial

app = Flask(__name__)

# Global variables
model = None
camera = None
camera_running = False
auto_capture_running = False
auto_capture_thread = None
selected_camera_index = 0
detection_counts = {'good': 0, 'defective': 0, 'total': 0}
latest_detection_data = {}

# Detection state management
detection_state = {
    'last_detection': None,  # 'good', 'defective', or None
    'detection_active': False,  # True when bolt is in zone
    'frames_without_detection': 0,  # Count frames with no detection
    'reset_threshold': 2,  # Frames to wait before allowing new detection (ultra-fast reset)
    'last_confidence': 0.0,  # Store confidence of last detection
    'arduino_signal_sent': False,  # Track if Arduino signal was sent for current detection
    'detection_history': [],  # Store recent detections for stability
    'stability_threshold': 2,  # Number of consistent detections needed (reduced for faster detection)
    'confirmed_detection': None,  # Final confirmed detection type
    'frames_with_object': 0,  # Count frames with unclassified object
    'object_timeout': 10  # Frames to wait before showing "unknown object"
}

# Arduino Serial Communication
arduino_serial = None
arduino_connected = False
arduino_port = 'COM4'  # Default port
arduino_enabled = False

def load_model():
    """Load the YOLO model"""
    global model
    try:
        model = YOLO('bestFinal.pt')
        print(f"Model loaded successfully! Classes: {model.names}")
        return True
    except Exception as e:
        print(f"Failed to load model: {e}")
        return False

def connect_arduino(port='COM4'):
    """Connect to Arduino via serial"""
    global arduino_serial, arduino_connected
    try:
        arduino_serial = serial.Serial(port, 9600, timeout=1)
        time.sleep(2)  # Wait for connection
        arduino_connected = True
        print(f"✅ Connected to Arduino on {port}")
        return True
    except Exception as e:
        arduino_connected = False
        print(f"❌ Failed to connect to Arduino on {port}: {e}")
        return False

def disconnect_arduino():
    """Disconnect from Arduino"""
    global arduino_serial, arduino_connected
    if arduino_serial:
        try:
            arduino_serial.close()
            arduino_connected = False
            print("🛑 Disconnected from Arduino")
            return True
        except Exception as e:
            print(f"Error disconnecting Arduino: {e}")
            return False
    return True

def send_to_arduino(signal):
    """Send signal to Arduino"""
    global arduino_serial, arduino_connected, arduino_enabled
    
    if not arduino_enabled or not arduino_connected or not arduino_serial:
        return False
    
    try:
        if signal == "HIGH":
            arduino_serial.write(b"HIGH\n")
            print("⚠️ Defective bolt detected — Sent HIGH to Arduino")
        else:
            arduino_serial.write(b"LOW\n")
            print("✅ All bolts OK — Sent LOW to Arduino")
        return True
    except Exception as e:
        print(f"Error sending to Arduino: {e}")
        arduino_connected = False
        return False

def detect_cameras():
    """Detect available cameras"""
    available_cameras = []
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                available_cameras.append(i)
            cap.release()
    return available_cameras



def enhance_frame_quality(frame):
    """Fast frame enhancement for better detection"""
    try:
        # Simple contrast enhancement for speed
        enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=10)
        return enhanced
    except Exception as e:
        print(f"Frame enhancement failed: {e}")
        return frame

def process_frame(frame):
    """Process frame with fixed detection zone and enhanced accuracy"""
    global model, detection_state
    if model is None:
        return frame, "Model not loaded", 0.0, 0, 0
    
    try:
        # Skip frame enhancement for maximum speed
        enhanced_frame = frame
        
        # Get frame dimensions
        frame_height, frame_width = frame.shape[:2]
        
        # Define fixed detection zone (center of frame)
        zone_width = 450  # Increased from 300
        zone_height = 400  # Increased height for better bottom coverage
        zone_x1 = (frame_width - zone_width) // 2
        zone_y1 = (frame_height - zone_height) // 2
        zone_x2 = zone_x1 + zone_width
        zone_y2 = zone_y1 + zone_height
        
        # Default detection zone color (white)
        zone_color = (255, 255, 255)  # White border
        zone_status = ""
        max_confidence = 0.0
        good_count = 0
        defective_count = 0
        defect_detected = False
        current_detection = None
        
        # Run AI detection with primary parameters
        results = model(enhanced_frame, 
                       conf=0.5,       # Moderate confidence for better detection
                       iou=0.5,        # Standard IoU for better accuracy
                       imgsz=416,      # Slightly larger input for better accuracy
                       verbose=False,
                       device='cpu')   # Ensure CPU usage for consistency
        
        # If no detections found, try with lower confidence as fallback
        if not results or len(results) == 0 or results[0].boxes is None or len(results[0].boxes) == 0:
            print("🔍 No detections with standard confidence, trying fallback...")
            results = model(enhanced_frame, 
                           conf=0.25,      # Much lower confidence fallback
                           iou=0.4,        # Lower IoU for more detections
                           imgsz=640,      # Larger input for better detection
                           verbose=False,
                           device='cpu')
            
            # If still no detections, try on original frame
            if not results or len(results) == 0 or results[0].boxes is None or len(results[0].boxes) == 0:
                print("🔍 Trying detection on original frame...")
                results = model(frame, 
                               conf=0.2,       # Very low confidence
                               iou=0.4,        
                               imgsz=640,      
                               verbose=False,
                               device='cpu')
        
        bolt_in_zone = False
        best_detection_type = None
        
        print(f"🔍 AI Results: {len(results) if results else 0} result(s)")
        if results and len(results) > 0:
            result = results[0]
            print(f"🔍 Boxes found: {len(result.boxes) if result.boxes is not None else 0}")
            if result.boxes is not None and len(result.boxes) > 0:
                for box in result.boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = box.conf[0].cpu().numpy()
                    class_id = int(box.cls[0].cpu().numpy())
                    
                    if confidence > 0.4:  # Moderate threshold to catch more detections
                        class_name = model.names[class_id]
                        
                        # Check if detection is inside the fixed zone
                        detection_center_x = (x1 + x2) / 2
                        detection_center_y = (y1 + y2) / 2
                        
                        # Strict boundary checking - bolt must be INSIDE the zone
                        margin = 10  # Add small margin for precision
                        if (zone_x1 + margin <= detection_center_x <= zone_x2 - margin and 
                            zone_y1 + margin <= detection_center_y <= zone_y2 - margin):
                            
                            bolt_in_zone = True
                            
                            # Only update detection type if this has higher confidence
                            if confidence > max_confidence:
                                max_confidence = confidence
                                
                                # Determine detection type based on class ID for reliability
                                if class_id == 0:  # Defective_Bolt
                                    best_detection_type = "defective"
                                elif class_id == 1:  # Good_Bolt
                                    best_detection_type = "good"
                        else:
                            # Detection outside zone - ignore it
                            print(f"🚫 Detection OUTSIDE zone ignored: {class_name} at ({detection_center_x:.0f}, {detection_center_y:.0f})")
        
        # Add detection stability - require consistent detections
        if bolt_in_zone and best_detection_type:
            # Add current detection to history
            detection_state['detection_history'].append(best_detection_type)
            
            # Keep only recent detections (last 5 frames)
            if len(detection_state['detection_history']) > 5:
                detection_state['detection_history'].pop(0)
            
            # Check for consistent detection
            if len(detection_state['detection_history']) >= detection_state['stability_threshold']:
                recent_detections = detection_state['detection_history'][-detection_state['stability_threshold']:]
                
                # Count occurrences of each type
                good_count_history = recent_detections.count('good')
                defective_count_history = recent_detections.count('defective')
                
                # Use majority vote for stable detection
                if good_count_history > defective_count_history:
                    current_detection = "good"
                elif defective_count_history > good_count_history:
                    current_detection = "defective"
                else:
                    # If tied, use the most recent detection
                    current_detection = recent_detections[-1]
                
                # Store confirmed detection
                detection_state['confirmed_detection'] = current_detection
            else:
                # Not enough history yet, use confirmed detection if available
                current_detection = detection_state.get('confirmed_detection', best_detection_type)
        else:
            current_detection = best_detection_type
            
            # Check if there might be something in the zone even without AI detection
            if not bolt_in_zone:
                # Simple motion/change detection as fallback
                frame_gray = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2GRAY)
                zone_roi = frame_gray[zone_y1:zone_y2, zone_x1:zone_x2]
                
                # Check if there's significant content in the zone
                mean_intensity = np.mean(zone_roi)
                std_intensity = np.std(zone_roi)
                
                # If there's variation in the zone, something might be there
                if std_intensity > 15:  # Threshold for detecting "something" in zone
                    detection_state['frames_with_object'] += 1
                    print(f"🔍 Something detected in zone but AI couldn't classify it (std: {std_intensity:.1f}, frames: {detection_state['frames_with_object']})")
                    
                    if detection_state['frames_with_object'] >= detection_state['object_timeout']:
                        zone_status = "Unknown object in zone - try repositioning"
                        zone_color = (255, 165, 0)  # Orange for "unknown object"
                    else:
                        zone_status = "Analyzing object in zone..."
                        zone_color = (255, 255, 0)  # Yellow for "analyzing"
                else:
                    detection_state['frames_with_object'] = 0
        
        # Detection state logic - only count once per bolt
        if bolt_in_zone:
            detection_state['frames_without_detection'] = 0
            
            # If this is a new detection (no active detection currently)
            if (not detection_state['detection_active'] and current_detection):
                
                # Count this detection
                if current_detection == "good":
                    good_count = 1
                    zone_color = (0, 255, 0)  # Green
                    zone_status = f"GOOD BOLT DETECTED! ({max_confidence:.2f})"
                    print(f"✅ NEW DETECTION: Good bolt with confidence {max_confidence:.2f}")
                elif current_detection == "defective":
                    defective_count = 1
                    defect_detected = True
                    zone_color = (0, 0, 255)  # Red
                    zone_status = f"DEFECTIVE BOLT DETECTED! ({max_confidence:.2f})"
                    print(f"❌ NEW DETECTION: Defective bolt with confidence {max_confidence:.2f}")
                
                # Update detection state
                detection_state['detection_active'] = True
                detection_state['last_detection'] = current_detection
                detection_state['last_confidence'] = max_confidence
                detection_state['arduino_signal_sent'] = False  # Reset signal flag for new detection
                
            else:
                # Bolt still in zone, show status but don't count again
                if detection_state['last_detection'] == "good":
                    zone_color = (0, 255, 0)  # Green
                    zone_status = f"Good bolt in zone ({detection_state['last_confidence']:.2f}) - already counted"
                elif detection_state['last_detection'] == "defective":
                    zone_color = (0, 0, 255)  # Red
                    zone_status = f"Defective bolt in zone ({detection_state['last_confidence']:.2f}) - already counted"

        else:
            # No bolt in zone
            detection_state['frames_without_detection'] += 1
            
            # Reset detection state after threshold frames without detection
            if detection_state['frames_without_detection'] >= detection_state['reset_threshold']:
                detection_state['detection_active'] = False
                detection_state['last_detection'] = None
                detection_state['last_confidence'] = 0.0
                detection_state['arduino_signal_sent'] = False
                detection_state['detection_history'] = []  # Clear detection history
                detection_state['confirmed_detection'] = None  # Clear confirmed detection
                detection_state['frames_with_object'] = 0  # Reset object counter
                zone_status = "Ready for next bolt"
            else:
                # Show last detection status briefly
                if detection_state['last_detection'] == "good":
                    zone_color = (0, 255, 0)  # Green
                    zone_status = f"Good bolt detected ({detection_state['last_confidence']:.2f}) - remove bolt"
                elif detection_state['last_detection'] == "defective":
                    zone_color = (0, 0, 255)  # Red
                    zone_status = f"Defective bolt detected ({detection_state['last_confidence']:.2f}) - remove bolt"
        
        # Draw the fixed detection zone
        cv2.rectangle(frame, (zone_x1, zone_y1), (zone_x2, zone_y2), zone_color, 4)
        
        # Add zone label background
        label_bg_y1 = zone_y1 - 35
        label_bg_y2 = zone_y1 - 5
        cv2.rectangle(frame, (zone_x1, label_bg_y1), (zone_x2, label_bg_y2), zone_color, -1)
        
        # Add zone status text
        cv2.putText(frame, zone_status, (zone_x1 + 10, zone_y1 - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        

        
        # Send Arduino signal only for defective bolts
        if defective_count > 0:
            if not detection_state['arduino_signal_sent']:
                send_to_arduino("HIGH")
                detection_state['arduino_signal_sent'] = True
                print("🔴 Arduino HIGH signal sent for defective bolt detection")
        elif good_count > 0:
            if not detection_state['arduino_signal_sent']:
                detection_state['arduino_signal_sent'] = True
                print("✅ Good bolt detected - no Arduino signal sent")
        
        return frame, zone_status, max_confidence, good_count, defective_count
        
    except Exception as e:
        return frame, f"Error: {str(e)}", 0.0, 0



def frame_to_base64(frame):
    """Convert frame to base64 string with speed optimization"""
    # Use lower quality for faster encoding
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, 70]  # Lower quality for speed
    _, buffer = cv2.imencode('.jpg', frame, encode_params)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{frame_base64}"

@app.route('/')
def index():
    """Main page"""
    available_cameras = detect_cameras()
    return render_template('index.html', cameras=available_cameras)

@app.route('/capture', methods=['POST'])
def capture():
    """Capture single frame from camera"""
    global detection_counts
    
    camera_index = int(request.json.get('camera_index', 0))
    
    # Try to capture frame
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return jsonify({'error': 'Failed to open camera'})
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return jsonify({'error': 'Failed to capture frame'})
    
    # Process frame
    processed_frame, prediction, confidence, good_new, defective_new = process_frame(frame)
    
    # Update counters
    detection_counts['good'] += good_new
    detection_counts['defective'] += defective_new
    detection_counts['total'] += (good_new + defective_new)
    
    # Convert frames to base64
    original_b64 = frame_to_base64(frame)
    processed_b64 = frame_to_base64(processed_frame)
    
    return jsonify({
        'original_image': original_b64,
        'processed_image': processed_b64,
        'prediction': prediction,
        'confidence': float(confidence),
        'good_count': good_new,
        'defective_count': defective_new,
        'total_good': detection_counts['good'],
        'total_defective': detection_counts['defective'],
        'total_count': detection_counts['total']
    })

@app.route('/upload', methods=['POST'])
def upload():
    """Upload and process image"""
    global detection_counts
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    
    try:
        # Read uploaded image
        image = Image.open(file.stream)
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process frame
        processed_frame, prediction, confidence, good_new, defective_new = process_frame(frame)
        
        # Update counters
        detection_counts['good'] += good_new
        detection_counts['defective'] += defective_new
        detection_counts['total'] += (good_new + defective_new)
        
        # Convert frames to base64
        original_b64 = frame_to_base64(frame)
        processed_b64 = frame_to_base64(processed_frame)
        
        return jsonify({
            'original_image': original_b64,
            'processed_image': processed_b64,
            'prediction': prediction,
            'confidence': float(confidence),
            'good_count': good_new,
            'defective_count': defective_new,
            'total_good': detection_counts['good'],
            'total_defective': detection_counts['defective'],
            'total_count': detection_counts['total']
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to process image: {str(e)}'})

@app.route('/reset_counters', methods=['POST'])
def reset_counters():
    """Reset detection counters"""
    global detection_counts
    detection_counts = {'good': 0, 'defective': 0, 'total': 0}
    return jsonify({'success': True, 'message': 'Counters reset'})

@app.route('/test_camera', methods=['POST'])
def test_camera():
    """Test if camera is working"""
    camera_index = int(request.json.get('camera_index', 0))
    
    cap = cv2.VideoCapture(camera_index)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            return jsonify({'success': True, 'message': f'Camera {camera_index} is working'})
    
    return jsonify({'success': False, 'message': f'Camera {camera_index} not working'})

def auto_capture_loop():
    """Maximum speed continuous streaming capture loop"""
    global auto_capture_running, selected_camera_index, detection_counts, latest_detection_data
    
    # Initialize camera with maximum speed settings
    cap = cv2.VideoCapture(selected_camera_index)
    
    if not cap.isOpened():
        print("❌ Failed to open camera for streaming")
        return
    
    # Optimize camera settings for maximum speed
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)      # Minimum buffer for lowest latency
    cap.set(cv2.CAP_PROP_FPS, 60)            # High FPS if supported
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Lower resolution for speed
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Lower resolution for speed
    
    print("📹 Starting maximum speed continuous streaming...")
    
    while auto_capture_running:
        # Capture and process every frame without skipping
        ret, frame = cap.read()
        
        if ret:
            # Process every frame for maximum responsiveness
            processed_frame, prediction, confidence, good_new, defective_new = process_frame(frame)
            
            # Update counters only when detection occurs
            if good_new > 0 or defective_new > 0:
                detection_counts['good'] += good_new
                detection_counts['defective'] += defective_new
                detection_counts['total'] += (good_new + defective_new)
                print(f"Detection: {prediction} (Confidence: {confidence:.2f})")
            
            # Store latest detection data
            latest_detection_data = {
                'original_image': frame_to_base64(frame),
                'processed_image': frame_to_base64(processed_frame),
                'prediction': prediction,
                'confidence': float(confidence),
                'good_count': good_new,
                'defective_count': defective_new,
                'total_good': detection_counts['good'],
                'total_defective': detection_counts['defective'],
                'total_count': detection_counts['total'],
                'timestamp': time.time()
            }
    
    # Clean up camera when stopping
    cap.release()
    print("📹 Maximum speed streaming stopped")

@app.route('/start_auto_capture', methods=['POST'])
def start_auto_capture():
    """Start continuous streaming"""
    global auto_capture_running, auto_capture_thread, selected_camera_index
    
    if auto_capture_running:
        return jsonify({'error': 'Auto capture already running'})
    
    camera_index = int(request.json.get('camera_index', 0))
    selected_camera_index = camera_index
    
    # Test camera first
    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return jsonify({'error': f'Failed to open camera {camera_index}'})
    
    ret, _ = cap.read()
    cap.release()
    
    if not ret:
        return jsonify({'error': f'Camera {camera_index} not responding'})
    
    # Start auto capture thread
    auto_capture_running = True
    auto_capture_thread = threading.Thread(target=auto_capture_loop, daemon=True)
    auto_capture_thread.start()
    
    return jsonify({'success': True, 'message': f'Continuous streaming started on camera {camera_index}'})

@app.route('/stop_auto_capture', methods=['POST'])
def stop_auto_capture():
    """Stop continuous streaming"""
    global auto_capture_running, auto_capture_thread
    
    if not auto_capture_running:
        return jsonify({'error': 'Auto capture not running'})
    
    auto_capture_running = False
    
    # Wait for thread to finish
    if auto_capture_thread:
        auto_capture_thread.join(timeout=1)
    
    return jsonify({'success': True, 'message': 'Continuous streaming stopped'})

@app.route('/get_latest_detection')
def get_latest_detection():
    """Get latest detection data from auto capture"""
    global latest_detection_data
    
    if latest_detection_data:
        return jsonify(latest_detection_data)
    else:
        return jsonify({'error': 'No detection data available'})

@app.route('/get_status')
def get_status():
    """Get current system status"""
    return jsonify({
        'auto_capture_running': auto_capture_running,
        'selected_camera': selected_camera_index,
        'counts': detection_counts
    })

@app.route('/connect_arduino', methods=['POST'])
def connect_arduino_route():
    """Connect to Arduino"""
    global arduino_enabled, arduino_port
    
    port = request.json.get('port', 'COM4')
    arduino_port = port
    
    if connect_arduino(port):
        arduino_enabled = True
        return jsonify({'success': True, 'message': f'Connected to Arduino on {port}'})
    else:
        return jsonify({'success': False, 'message': f'Failed to connect to Arduino on {port}'})

@app.route('/disconnect_arduino', methods=['POST'])
def disconnect_arduino_route():
    """Disconnect from Arduino"""
    global arduino_enabled
    
    if disconnect_arduino():
        arduino_enabled = False
        return jsonify({'success': True, 'message': 'Disconnected from Arduino'})
    else:
        return jsonify({'success': False, 'message': 'Failed to disconnect from Arduino'})

@app.route('/toggle_arduino', methods=['POST'])
def toggle_arduino():
    """Enable/disable Arduino communication"""
    global arduino_enabled
    
    enable = request.json.get('enable', False)
    arduino_enabled = enable
    
    status = "enabled" if enable else "disabled"
    return jsonify({'success': True, 'message': f'Arduino communication {status}', 'enabled': arduino_enabled})

@app.route('/test_arduino', methods=['POST'])
def test_arduino():
    """Test Arduino connection by sending a test signal"""
    if not arduino_connected:
        return jsonify({'success': False, 'message': 'Arduino not connected'})
    
    test_signal = request.json.get('signal', 'HIGH')
    
    if send_to_arduino(test_signal):
        return jsonify({'success': True, 'message': f'Test signal {test_signal} sent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send test signal'})

@app.route('/get_arduino_status')
def get_arduino_status():
    """Get Arduino connection status"""
    return jsonify({
        'connected': arduino_connected,
        'enabled': arduino_enabled,
        'port': arduino_port
    })

@app.route('/get_counts')
def get_counts():
    """Get current detection counts"""
    return jsonify(detection_counts)

if __name__ == '__main__':
    # Load model on startup
    if load_model():
        print("Starting Flask app...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Failed to load model. Exiting...")