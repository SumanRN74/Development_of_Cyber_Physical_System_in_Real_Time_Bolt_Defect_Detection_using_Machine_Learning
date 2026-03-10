import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np
import threading
import time

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Ultralytics not found. Please install: pip install ultralytics")

class BoltFaultDetectionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bolt Fault Detection System")
        self.root.geometry("800x520")
        
        # Initialize variables
        self.cap = None
        self.is_camera_running = False
        self.model = None
        self.available_cameras = []
        self.selected_camera = tk.StringVar()
        
        # Counters for bolt detection
        self.good_bolt_count = 0
        self.defective_bolt_count = 0
        
        # Detect available cameras
        self.detect_cameras()
        
        # Load the trained model
        self.load_model()
        
        # Create GUI elements
        self.create_widgets()
        
        # Start camera thread
        self.camera_thread = None
        
    def load_model(self):
        """Load the trained YOLO model"""
        try:
            if not YOLO_AVAILABLE:
                messagebox.showerror("Error", "Ultralytics not installed. Please run: pip install ultralytics")
                return
                
            self.model = YOLO('bestFinal.pt')
            print("YOLO model loaded successfully")
            print(f"Model names: {self.model.names}")
            
        except Exception as e:
            error_msg = f"Failed to load model: {str(e)}"
            print(error_msg)
            messagebox.showerror("Error", error_msg)
            self.model = None
            
    def detect_cameras(self):
        """Detect available cameras"""
        self.available_cameras = []
        
        # Test camera indices from 0 to 10
        for i in range(10):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    self.available_cameras.append(f"Camera {i}")
                cap.release()
        
        # If no cameras found, add default option
        if not self.available_cameras:
            self.available_cameras = ["No cameras detected"]
        
        # Set default selection
        if self.available_cameras and "No cameras" not in self.available_cameras[0]:
            self.selected_camera.set(self.available_cameras[0])
            
    def refresh_cameras(self):
        """Refresh the list of available cameras"""
        self.detect_cameras()
        self.camera_combo['values'] = self.available_cameras
        if self.available_cameras and "No cameras" not in self.available_cameras[0]:
            self.selected_camera.set(self.available_cameras[0])
            
    def get_camera_index(self):
        """Get the camera index from selected camera string"""
        selected = self.selected_camera.get()
        if "Camera" in selected:
            try:
                return int(selected.split()[-1])
            except:
                return 0
        return 0
        
    def reset_counters(self):
        """Reset the bolt counters"""
        self.good_bolt_count = 0
        self.defective_bolt_count = 0
        self.update_counter_display()
        
    def update_counter_display(self):
        """Update the counter display labels"""
        self.good_count_label.config(text=f"Good Bolts: {self.good_bolt_count}")
        self.defective_count_label.config(text=f"Defective Bolts: {self.defective_bolt_count}")
            
    def create_widgets(self):
        """Create the GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Bolt Fault Detection System", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Camera frame
        self.camera_frame = ttk.LabelFrame(main_frame, text="Camera Feed", padding="5")
        self.camera_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Video display
        self.video_label = ttk.Label(self.camera_frame)
        self.video_label.grid(row=0, column=0, padx=5, pady=5)
        
        # Control frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="5")
        control_frame.grid(row=1, column=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Camera selection
        camera_label = ttk.Label(control_frame, text="Select Camera:")
        camera_label.grid(row=0, column=0, pady=5, sticky=tk.W)
        
        self.camera_combo = ttk.Combobox(control_frame, textvariable=self.selected_camera, 
                                        values=self.available_cameras, state="readonly")
        self.camera_combo.grid(row=1, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Refresh cameras button
        refresh_button = ttk.Button(control_frame, text="Refresh Cameras", 
                                   command=self.refresh_cameras)
        refresh_button.grid(row=2, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Camera controls
        self.start_button = ttk.Button(control_frame, text="Start Camera", 
                                      command=self.start_camera)
        self.start_button.grid(row=3, column=0, pady=5, sticky=tk.W+tk.E)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Camera", 
                                     command=self.stop_camera, state="disabled")
        self.stop_button.grid(row=4, column=0, pady=5, sticky=tk.W+tk.E)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Detection Results", padding="5")
        results_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Status label
        self.status_label = ttk.Label(results_frame, text="Status: Ready", 
                                     font=("Arial", 12))
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Prediction label
        self.prediction_label = ttk.Label(results_frame, text="Prediction: -", 
                                         font=("Arial", 12, "bold"))
        self.prediction_label.grid(row=1, column=0, sticky=tk.W)
        
        # Confidence label
        self.confidence_label = ttk.Label(results_frame, text="Confidence: -", 
                                         font=("Arial", 10))
        self.confidence_label.grid(row=2, column=0, sticky=tk.W)
        
        # Counter labels
        self.good_count_label = ttk.Label(results_frame, text="Good Bolts: 0", 
                                         font=("Arial", 11), foreground="green")
        self.good_count_label.grid(row=0, column=1, sticky=tk.W, padx=(50, 0))
        
        self.defective_count_label = ttk.Label(results_frame, text="Defective Bolts: 0", 
                                              font=("Arial", 11), foreground="red")
        self.defective_count_label.grid(row=1, column=1, sticky=tk.W, padx=(50, 0))
        
        # Reset counter button
        reset_button = ttk.Button(results_frame, text="Reset Counters", 
                                 command=self.reset_counters)
        reset_button.grid(row=2, column=1, sticky=tk.W, padx=(50, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)        

    def start_camera(self):
        """Start the camera feed"""
        try:
            # Check if a camera is selected
            if "No cameras" in self.selected_camera.get():
                messagebox.showerror("Error", "No cameras available")
                return
                
            camera_index = self.get_camera_index()
            self.cap = cv2.VideoCapture(camera_index)
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", f"Could not open camera {camera_index}")
                return
                
            self.is_camera_running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            self.camera_combo.config(state="disabled")
            self.status_label.config(text=f"Status: {self.selected_camera.get()} Running")
            
            # Start camera thread
            self.camera_thread = threading.Thread(target=self.update_camera)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start camera: {str(e)}")
            
    def stop_camera(self):
        """Stop the camera feed"""
        self.is_camera_running = False
        if self.cap:
            self.cap.release()
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.camera_combo.config(state="readonly")
        self.status_label.config(text="Status: Camera Stopped")
        self.prediction_label.config(text="Prediction: -")
        self.confidence_label.config(text="Confidence: -")
        
        # Clear video display
        self.video_label.config(image="")
        
    def draw_detections(self, frame, results):
        """Draw detection boxes and labels on frame"""
        if results and len(results) > 0:
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        confidence = box.conf[0].cpu().numpy()
                        class_id = int(box.cls[0].cpu().numpy())
                        
                        # Get class name
                        class_name = self.model.names[class_id] if class_id in self.model.names else f"Class {class_id}"
                        
                        # Choose color based on class
                        color = (0, 255, 0) if "good" in class_name.lower() or "normal" in class_name.lower() else (0, 0, 255)
                        
                        # Draw bounding box
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                        
                        # Draw label
                        label = f"{class_name}: {confidence:.2f}"
                        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                        cv2.rectangle(frame, (int(x1), int(y1) - label_size[1] - 10), 
                                    (int(x1) + label_size[0], int(y1)), color, -1)
                        cv2.putText(frame, label, (int(x1), int(y1) - 5), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame
        
    def predict_fault(self, frame):
        """Make prediction on the current frame using YOLO"""
        if self.model is None:
            return "Model not loaded", 0.0, []
            
        try:
            # Run YOLO inference
            results = self.model(frame, verbose=False)
            
            # Process results and count detections
            if results and len(results) > 0:
                result = results[0]
                if result.boxes is not None and len(result.boxes) > 0:
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy()
                    
                    # Count all detections above confidence threshold (per frame)
                    good_detections = 0
                    defective_detections = 0
                    
                    for i, (conf, class_id) in enumerate(zip(confidences, class_ids)):
                        if conf > 0.7:  # Only count high confidence detections
                            class_name = self.model.names[int(class_id)]
                            if "Good_Bolt" in class_name:
                                good_detections += 1
                            elif "Defective_Bolt" in class_name:
                                defective_detections += 1
                    
                    # Update counters (only if new detections found)
                    if good_detections > 0 or defective_detections > 0:
                        self.good_bolt_count += good_detections
                        self.defective_bolt_count += defective_detections
                    
                    # Get the highest confidence detection for display
                    max_conf_idx = np.argmax(confidences)
                    max_confidence = confidences[max_conf_idx]
                    predicted_class_id = int(class_ids[max_conf_idx])
                    
                    # Get class name
                    class_name = self.model.names[predicted_class_id] if predicted_class_id in self.model.names else f"Class {predicted_class_id}"
                    
                    return class_name, max_confidence, results
                else:
                    return "No Detection", 0.0, results
            else:
                return "No Detection", 0.0, []
                
        except Exception as e:
            print(f"Prediction error: {e}")
            return f"Error: {str(e)}", 0.0, []
            
    def update_camera(self):
        """Update camera feed and run predictions"""
        while self.is_camera_running:
            ret, frame = self.cap.read()
            if not ret:
                break
                
            # Make prediction
            prediction, confidence, results = self.predict_fault(frame)
            
            # Draw detections on frame
            frame = self.draw_detections(frame, results)
            
            # Convert frame for tkinter display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_resized = cv2.resize(frame_rgb, (640, 410))
            img = Image.fromarray(frame_resized)
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update GUI in main thread
            self.root.after(0, self.update_gui, imgtk, prediction, confidence)
            
            time.sleep(0.03)  # ~30 FPS
            
    def update_gui(self, imgtk, prediction, confidence):
        """Update GUI elements with new frame and prediction"""
        if self.is_camera_running:
            self.video_label.config(image=imgtk)
            self.video_label.image = imgtk  # Keep a reference
            
            # Update prediction labels
            color = "green" if "good" in prediction.lower() or "normal" in prediction.lower() else "red"
            self.prediction_label.config(text=f"Prediction: {prediction}", 
                                       foreground=color)
            self.confidence_label.config(text=f"Confidence: {confidence:.2f}")
            
            # Update counter display
            self.update_counter_display()
            
    def on_closing(self):
        """Handle window closing"""
        self.stop_camera()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = BoltFaultDetectionGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()