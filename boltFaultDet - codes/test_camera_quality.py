import cv2
import numpy as np

def configure_camera(cap):
    """Configure camera for better quality"""
    try:
        # Set resolution to HD (1280x720) for better clarity
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Set FPS for smoother capture
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Improve image quality settings
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
        cap.set(cv2.CAP_PROP_CONTRAST, 0.6)
        cap.set(cv2.CAP_PROP_SATURATION, 0.6)
        cap.set(cv2.CAP_PROP_SHARPNESS, 0.7)
        
        # Auto-focus and exposure settings
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)
        
        # Buffer size to reduce latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        print(f"Camera configured: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} @ {int(cap.get(cv2.CAP_PROP_FPS))}fps")
        
    except Exception as e:
        print(f"Warning: Could not configure all camera settings: {e}")
    
    return cap

def enhance_image_quality(frame):
    """Enhance image quality through post-processing"""
    try:
        # Convert to LAB color space for better processing
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        # Merge channels and convert back to BGR
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        # Apply slight sharpening
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        enhanced = cv2.filter2D(enhanced, -1, kernel)
        
        # Reduce noise while preserving edges
        enhanced = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        return enhanced
    except Exception as e:
        print(f"Image enhancement failed: {e}")
        return frame

def test_camera_quality():
    """Test camera with quality improvements"""
    print("Testing camera quality improvements...")
    
    # Try camera 0 first
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open camera")
        return
    
    # Configure camera
    cap = configure_camera(cap)
    
    print("Press 'q' to quit, 's' to save current frame")
    print("Press 'e' to toggle enhancement on/off")
    
    enhancement_enabled = True
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not read frame")
            break
        
        # Show original and enhanced side by side
        if enhancement_enabled:
            enhanced = enhance_image_quality(frame)
            # Resize for display
            frame_small = cv2.resize(frame, (640, 360))
            enhanced_small = cv2.resize(enhanced, (640, 360))
            
            # Add labels
            cv2.putText(frame_small, "Original", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            cv2.putText(enhanced_small, "Enhanced", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Combine images
            combined = np.hstack((frame_small, enhanced_small))
            cv2.imshow('Camera Quality Test - Original vs Enhanced', combined)
        else:
            cv2.imshow('Camera Quality Test - Original Only', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            if enhancement_enabled:
                enhanced = enhance_image_quality(frame)
                cv2.imwrite('enhanced_sample.jpg', enhanced)
                print("Enhanced frame saved as 'enhanced_sample.jpg'")
            cv2.imwrite('original_sample.jpg', frame)
            print("Original frame saved as 'original_sample.jpg'")
        elif key == ord('e'):
            enhancement_enabled = not enhancement_enabled
            print(f"Enhancement {'enabled' if enhancement_enabled else 'disabled'}")
    
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    test_camera_quality()