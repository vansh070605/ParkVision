import os
import torch
import torch.nn as nn
import torch.optim as optim
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import cv2
from app.config.config import settings

class OccupancyCNN(nn.Module):
    def __init__(self):
        super().__init__()
        # Standard input: 64x64 RGB crops
        self.features = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, stride=1, padding=1), # 64x64x16
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 32x32x16
            
            nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1), # 32x32x32
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 16x16x32
            
            nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1), # 16x16x64
            nn.ReLU(),
            nn.MaxPool2d(2, 2), # 8x8x64
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 8 * 8, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 2) # Outputs [prob_empty, prob_occupied]
        )

    def forward(self, x):
        return self.features(x)

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)

class CNNClassifierService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = OccupancyCNN().to(self.device)
        self.transform = transforms.Compose([
            transforms.Resize((64, 64)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        self.weights_path = settings.CNN_MODEL_PATH
        os.makedirs(os.path.dirname(self.weights_path), exist_ok=True)
        
        # Load weights or self-initialize
        if os.path.exists(self.weights_path):
            try:
                self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device))
                self.model.eval()
                print(f"[CNN] Loaded custom weights from {self.weights_path}")
            except Exception as e:
                print(f"[CNN] Error loading weights: {e}. Reinitializing model.")
                self._initialize_dummy_weights()
        else:
            self._initialize_dummy_weights()

    def _initialize_dummy_weights(self):
        """Saves initialized random weights so the model starts with a valid state."""
        print("[CNN] Initializing dummy weights...")
        # Train on some synthetic random data to create a non-zero state
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.CrossEntropyLoss()
        
        # Create a small random synthetic dataset
        self.model.train()
        for _ in range(5): # 5 dummy epochs
            dummy_inputs = torch.randn(10, 3, 64, 64).to(self.device)
            dummy_targets = torch.randint(0, 2, (10,)).to(self.device)
            
            optimizer.zero_grad()
            outputs = self.model(dummy_inputs)
            loss = criterion(outputs, dummy_targets)
            loss.backward()
            optimizer.step()
            
        torch.save(self.model.state_dict(), self.weights_path)
        self.model.eval()
        print(f"[CNN] Saved initialized weights to {self.weights_path}")

    def predict_batch(self, crops: list) -> list:
        """
        Takes a list of ROI crops (numpy BGR images) and returns predictions.
        Returns: List of dicts [{"occupied": bool, "confidence": float}]
        """
        if not crops:
            return []
            
        tensor_list = []
        for crop in crops:
            # Convert BGR (OpenCV) to RGB
            rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            tensor_list.append(self.transform(pil_img))
            
        batch_tensor = torch.stack(tensor_list).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(batch_tensor)
            probs = torch.softmax(outputs, dim=1)
            confidences, classes = torch.max(probs, dim=1)
            
        results = []
        for i in range(len(crops)):
            results.append({
                "occupied": bool(classes[i].item() == 1),
                "confidence": float(confidences[i].item())
            })
            
        return results

    def fine_tune(self, cropped_images: list, labels: list, epochs: int = 10):
        """
        Fine-tunes the CNN on runtime captured samples.
        cropped_images: List of BGR numpy images
        labels: List of integers (0: empty, 1: occupied)
        """
        if not cropped_images or len(cropped_images) != len(labels):
            return
            
        self.model.train()
        optimizer = optim.Adam(self.model.parameters(), lr=0.0005)
        criterion = nn.CrossEntropyLoss()
        
        tensor_list = []
        for img in cropped_images:
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            tensor_list.append(self.transform(Image.fromarray(rgb)))
            
        inputs = torch.stack(tensor_list).to(self.device)
        targets = torch.tensor(labels, dtype=torch.long).to(self.device)
        
        # Simple training loop
        for epoch in range(epochs):
            optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
        torch.save(self.model.state_dict(), self.weights_path)
        self.model.eval()
        print(f"[CNN] Fine-tuned model completed. Saved updated weights.")
