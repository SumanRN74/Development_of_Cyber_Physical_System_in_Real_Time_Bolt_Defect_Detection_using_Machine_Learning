import torch
import numpy as np

def inspect_model():
    """Inspect the YOLO model"""
    try:
        from ultralytics import YOLO
        
        print("Loading YOLO model...")
        model = YOLO('bestFinal.pt')
        
        print(f"Model names: {model.names}")
        print(f"Model task: {model.task}")
        
        # Test with a dummy image
        print("\nTesting model inference...")
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
        
        results = model(dummy_image, verbose=False)
        print(f"Results type: {type(results)}")
        print(f"Number of results: {len(results)}")
        
        if results:
            result = results[0]
            print(f"Result boxes: {result.boxes}")
            if result.boxes is not None:
                print(f"Number of detections: {len(result.boxes)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_model()