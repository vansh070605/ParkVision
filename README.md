# ParkVision 🚗🤖

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/OpenCV-4.9-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white" alt="OpenCV" />
</p>

---

ParkVision is an enterprise-grade, AI-driven **Smart Parking Space Analytics Platform**. It utilizes **YOLOv8** object detection, a lightweight CNN, and advanced **1D RANSAC geometry calibration** to identify, track, and count vehicles in real time.

---

## 🌟 Key Features

| Feature | Description |
| :--- | :--- |
| **✨ RANSAC Auto-Calibration** | Automatically maps parking grids, determines divider spacing ($W$), and fills gaps under parked cars using 1D RANSAC and YOLOv8 spatial context. |
| **⚡ Throttled Database Engine** | Limits SQLite writes by committing only on state transitions and throttling telemetry logs to 5-second intervals to avoid locks. |
| **🧠 Dual-Model Inference** | Combines overhead YOLOv8 vehicle tracking with high-accuracy CNN patch verification for stable occupancy classification. |
| **🎨 Sleek Dark Dashboard** | Built with React and Tailwind CSS, featuring smooth micro-animations, glassmorphism overlays, and EV slot status tracking. |
| **🎥 Live Telemetry Streams** | Low-latency processed frame broadcasts directly to standard browser players via WebSockets and MJPEG stream endpoints. |

---

## 🛠️ Architecture & Tech Stack

### Frontend
- **React 19** & **Vite** (Next-generation lightning-fast developer experience)
- **Tailwind CSS v3** (Utility-first styling for dark glassmorphic widgets)
- **JetBrains Mono** & **Outfit** Typography

### Backend
- **Python 3.12** & **FastAPI** (High performance asynchronous routing)
- **SQLAlchemy** & **aiosqlite** (Asynchronous SQLite database layer)
- **WebSockets** (Real-time telemetry and state broadcasting)

### Deep Learning & Computer Vision
- **Ultralytics YOLOv8** (Vehicle detection and spatial context mapping)
- **PyTorch** & **Torchvision** (CNN Classifier & U-Net semantic segmentation fallback)
- **OpenCV** (CLAHE, bilateral filtering, Hough Line transforms, and Homography perspective warping)

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** v18+
- **Python** v3.10+
- **CUDA Toolkit** (Optional, for GPU acceleration)

### 1. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate      # On Windows
source .venv/bin/activate    # On macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn main:app --reload
```

> [!NOTE]
> On the first startup, the YOLOv8 model weights (`yolov8m.pt`) will automatically download to the backend directory.

### 2. Frontend Setup

```bash
# Open a new terminal and navigate to the frontend directory
cd frontend

# Install Node modules
npm install

# Start the Vite dev server
npm run dev
```

### 3. Running & Calibrating

1. Open `http://localhost:5173` in your browser.
2. In the **Configure Camera Feed** modal, input your camera alias and select a calibration image (e.g., `backend/uploads/lot.jpg`).
3. Click the **✨ AUTO-CALIBRATE** button in the header. The RANSAC grid pipeline will instantly project, align, and generate optimized parking-space ROIs.
4. Mark any specialized **EV spots** in the sidebar, adjust coordinates if desired, and click **INITIALIZE PIPELINE** to spin up the live analytics engine!

---

## 🤝 Contributing
Contributions are welcome. Feel free to open issues or submit pull requests.
