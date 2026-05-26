import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import cv2

# Define a standard PyTorch U-Net for semantic segmentation of parking slots
class DoubleConv(nn.Module):
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, 3, 1, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, 3, 1, 1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.conv(x)

class UNet(nn.Module):
    def __init__(self, in_channels=3, out_channels=1, features=[64, 128, 256, 512]):
        super().__init__()
        self.ups = nn.ModuleList()
        self.downs = nn.ModuleList()
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)

        # Down part of UNet
        for feature in features:
            self.downs.append(DoubleConv(in_channels, feature))
            in_channels = feature

        # Up part of UNet
        for feature in reversed(features):
            self.ups.append(
                nn.ConvTranspose2d(feature*2, feature, kernel_size=2, stride=2)
            )
            self.ups.append(DoubleConv(feature*2, feature))

        self.bottleneck = DoubleConv(features[-1], features[-1]*2)
        self.final_conv = nn.Conv2d(features[0], out_channels, kernel_size=1)

    def forward(self, x):
        skip_connections = []

        for down in self.downs:
            x = down(x)
            skip_connections.append(x)
            x = self.pool(x)

        x = self.bottleneck(x)
        skip_connections = skip_connections[::-1]

        for idx in range(0, len(self.ups), 2):
            x = self.ups[idx](x)
            skip_connection = skip_connections[idx//2]

            if x.shape != skip_connection.shape:
                x = transforms.functional.resize(x, size=skip_connection.shape[2:])

            concat_x = torch.cat((skip_connection, x), dim=1)
            x = self.ups[idx+1](concat_x)

        return self.final_conv(x)

class SegmentationService:
    def __init__(self, weights_path="weights/unet_parking.pt"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = UNet(in_channels=3, out_channels=1).to(self.device)
        self.weights_path = weights_path
        self.has_weights = False
        
        self.transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        
        if os.path.exists(self.weights_path):
            try:
                # Bypass weights_only if needed for security configuration compatibility
                self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device, weights_only=False))
                self.model.eval()
                self.has_weights = True
                print(f"[Segmentation] Loaded model weights from {self.weights_path}")
            except Exception as e:
                print(f"[Segmentation] Error loading model weights: {e}")
        else:
            print(f"[Segmentation] No custom weights found at {self.weights_path}. Running in fallback mode.")

    def segment_image(self, image: np.ndarray) -> np.ndarray:
        """
        Takes a BGR image and returns a binary segmentation mask of parking areas.
        """
        if not self.has_weights:
            # Return an empty mask if no weights are available, triggering secondary fallback
            return np.zeros(image.shape[:2], dtype=np.uint8)
            
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        input_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            output = self.model(input_tensor)
            prediction = torch.sigmoid(output).squeeze(0).squeeze(0)
            prediction = (prediction > 0.5).cpu().numpy().astype(np.uint8) * 255
            
        # Resize prediction back to original image dimensions
        prediction_resized = cv2.resize(prediction, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_NEAREST)
        return prediction_resized
