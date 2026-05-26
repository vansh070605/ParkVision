import os
from ultralytics import YOLO

def main():
    # Define the dataset YAML file path. 
    # The dataset should follow YOLOv8 format (images/labels in train/val splits).
    dataset_yaml = "data.yaml"
    
    # Check if dataset yaml exists
    if not os.path.exists(dataset_yaml):
        print(f"Error: Dataset configuration file '{dataset_yaml}' not found.")
        print("Please ensure you have your parking dataset organized in YOLO format")
        print("and the 'data.yaml' file is placed in the 'backend' directory.")
        print("\nExample data.yaml structure:")
        print("train: ./dataset/train/images")
        print("val: ./dataset/valid/images")
        print("\nnames:")
        print("  0: car")
        return

    # Load a pre-trained model (recommended for training)
    # Using 'yolov8m.pt' for better accuracy, or 'yolov8n.pt' for faster training
    print("Loading pre-trained YOLOv8m model...")
    model = YOLO("yolov8m.pt")

    # Train the model
    # Adjust epochs, batch_size, and imgsz based on your hardware capabilities (GPU vs CPU)
    print(f"Starting training on dataset: {dataset_yaml}")
    results = model.train(
        data=dataset_yaml,
        epochs=50,       # Number of epochs to train for
        batch=16,        # Batch size (reduce if you get Out of Memory errors)
        imgsz=640,       # Image size (usually 640 for YOLOv8)
        device="",       # Leave empty to auto-select (cuda:0 if GPU available, else CPU)
        name="parkvision_model", # Name of the folder where results are saved (runs/detect/parkvision_model)
        project="runs",  # Project directory
        exist_ok=True    # Overwrite existing project/name if it exists
    )

    print("\nTraining completed!")
    print("The best weights are saved at: runs/parkvision_model/weights/best.pt")
    print("The system will now automatically use these weights if available.")

if __name__ == "__main__":
    main()
