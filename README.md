# ParkVision 🚗🤖

ParkVision is an enterprise-grade AI-driven Smart Parking Space Counter. It utilizes **YOLOv8** object detection to identify and count vehicles from overhead CCTV feeds, satellite images, or video uploads in real time.

## 🌟 Features

- **Dynamic Media Uploads:** Upload any parking lot image or video directly from the UI.
- **State-of-the-art AI:** Powered by Ultralytics YOLOv8 for highly accurate vehicle detection (cars, buses, trucks) across various lighting conditions and angles.
- **Real-Time Telemetry:** Instantly calculates total capacity, occupied spots, and available spots using a custom algorithm.
- **Live Streaming:** Video processing frames are streamed directly to the dashboard via low-latency WebSockets.
- **Dark Industrial UI:** A sleek, high-fidelity React dashboard built with Tailwind CSS, featuring glassmorphism and a custom interleaved grid.

## 🛠️ Tech Stack

- **Frontend:** React 19, Vite, Tailwind CSS v3
- **Backend:** Python 3.12, FastAPI, WebSockets
- **Computer Vision:** Ultralytics YOLOv8, OpenCV

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup

Navigate to the `backend` directory and install the dependencies:
```bash
cd backend
pip install -r requirements.txt
```

Start the FastAPI server:
```bash
uvicorn main:app --reload
```
*Note: On the first run, the YOLOv8 model weights (`yolov8m.pt`) will download automatically.*

### 2. Frontend Setup

Open a new terminal, navigate to the `frontend` directory, and install dependencies:
```bash
cd frontend
npm install
```

Start the Vite development server:
```bash
npm run dev
```

### 3. Usage

1. Open `http://localhost:5173` in your browser.
2. The **Initialize System** modal will appear.
3. Upload a top-down parking lot image or video.
4. Set the **Total Capacity** of the lot.
5. Click **INITIALIZE FEED**. The dashboard will load and the AI will begin processing and displaying live telemetry!

## 🤝 Contributing
Contributions are welcome. Feel free to open issues or submit pull requests.
