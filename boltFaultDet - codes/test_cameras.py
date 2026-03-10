import cv2

def test_cameras():
    """Test available cameras"""
    available_cameras = []
    
    print("Testing cameras...")
    for i in range(5):  # Test first 5 camera indices
        print(f"Testing camera {i}...")
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"  ✓ Camera {i} is working")
                available_cameras.append(f"Camera {i}")
            else:
                print(f"  ✗ Camera {i} opened but can't read frames")
            cap.release()
        else:
            print(f"  ✗ Camera {i} not available")
    
    print(f"\nAvailable cameras: {available_cameras}")
    return available_cameras

if __name__ == "__main__":
    test_cameras()