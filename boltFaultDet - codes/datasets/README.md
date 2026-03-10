# Bolt Datasets

This folder contains training and testing datasets for the bolt fault detection system.

## 📁 Folder Structure

Organize your datasets as follows:

```
datasets/
├── training/
│   ├── good_bolts/
│   │   ├── good_001.jpg
│   │   ├── good_002.jpg
│   │   └── ...
│   └── defective_bolts/
│       ├── defect_001.jpg
│       ├── defect_002.jpg
│       └── ...
├── testing/
│   ├── good_bolts/
│   └── defective_bolts/
├── validation/
│   ├── good_bolts/
│   └── defective_bolts/
└── annotations/
    ├── labels.txt
    └── yolo_format/
```

## 📸 Image Guidelines

### Good Bolts
- Clear, well-lit images
- Bolt centered in frame
- Various angles and orientations
- Different lighting conditions
- Minimum 100 images recommended

### Defective Bolts
- Various defect types:
  - Cracks
  - Deformations
  - Missing threads
  - Rust/corrosion
  - Damaged heads
- Clear visibility of defects
- Multiple angles per defect type
- Minimum 100 images recommended

## 🏷️ Annotation Format

For YOLO training, use the following format:

```
<class_id> <x_center> <y_center> <width> <height>
```

Example:
```
0 0.5 0.5 0.3 0.4  # Good bolt
1 0.5 0.5 0.3 0.4  # Defective bolt
```

## 📊 Dataset Statistics

Track your dataset composition:

| Category | Training | Validation | Testing | Total |
|----------|----------|------------|---------|-------|
| Good Bolts | - | - | - | - |
| Defective Bolts | - | - | - | - |
| **Total** | - | - | - | - |

## 🔄 Data Augmentation

Consider these augmentation techniques:
- Rotation (±15°)
- Brightness adjustment
- Contrast variation
- Horizontal flip
- Zoom (0.8x - 1.2x)
- Gaussian noise

## 📝 Notes

- Keep original images separate from augmented ones
- Maintain consistent image quality
- Document defect types and characteristics
- Regular dataset updates improve accuracy
- Balance good vs defective samples (50/50 ratio recommended)
