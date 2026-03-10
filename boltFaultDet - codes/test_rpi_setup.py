#!/usr/bin/env python3
"""
Test script to verify all libraries are working on Raspberry Pi
"""

def test_imports():
    """Test all required imports"""
    try:
        print("Testing imports...")
        
        import flask
        print(f"✅ Flask: {flask.__version__}")
        
        import cv2
        print(f"✅ OpenCV: {cv2.__version__}")
        
        import numpy as np
        print(f"✅ NumPy: {np.__version__}")
        
        import PIL
        print(f"✅ Pillow: {PIL.__version__}")
        
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        
        import torchvision
        print(f"✅ TorchVision: {torchvision.__version__}")
        
        from ultralytics import YOLO
        print("✅ Ultralytics YOLO imported successfully")
        
        import serial
        print("✅ PySerial imported successfully")
        
        print("\n🎉 All libraries imported successfully!")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_camera():
    """Test camera functionality"""
    try:
        print("\nTesting camera...")
        import cv2
        
        # Test camera 0
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"✅ Camera working - Frame shape: {frame.shape}")
                cap.release()
                return True
            else:
                print("❌ Camera opened but couldn't read frame")
        else:
            print("❌ Could not open camera")
        
        cap.release()
        return False
        
    except Exception as e:
        print(f"❌ Camera test error: {e}")
        return False

def test_torch():
    """Test PyTorch functionality"""
    try:
        print("\nTesting PyTorch...")
        import torch
        
        # Create a simple tensor
        x = torch.randn(3, 3)
        print(f"✅ PyTorch tensor created: {x.shape}")
        
        # Test if CUDA is available (should be False on Pi)
        print(f"CUDA available: {torch.cuda.is_available()}")
        
        return True
        
    except Exception as e:
        print(f"❌ PyTorch test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Raspberry Pi Setup Test ===\n")
    
    import_success = test_imports()
    camera_success = test_camera()
    torch_success = test_torch()
    
    print(f"\n=== Test Results ===")
    print(f"Imports: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"Camera: {'✅ PASS' if camera_success else '❌ FAIL'}")
    print(f"PyTorch: {'✅ PASS' if torch_success else '❌ FAIL'}")
    
    if import_success and torch_success:
        print(f"\n🎉 Your Raspberry Pi is ready to run the bolt detection system!")
        if not camera_success:
            print("⚠️  Camera test failed - check camera connection")
    else:
        print(f"\n❌ Some tests failed - check installation")

if __name__ == "__main__":
    main()