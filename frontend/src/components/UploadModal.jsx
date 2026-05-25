import React, { useState, useRef, useEffect } from 'react';

function UploadModal({ onUploadSuccess, onClose }) {
  const [file, setFile] = useState(null);
  const [step, setStep] = useState(1); // 1: upload, 2: draw
  const [isUploading, setIsUploading] = useState(false);
  const [isAutoDetecting, setIsAutoDetecting] = useState(false);
  const [error, setError] = useState('');
  
  // Canvas & Drawing State
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const [mediaSrc, setMediaSrc] = useState(null);
  const [isVideo, setIsVideo] = useState(false);
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });
  
  const [rois, setRois] = useState([]);
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentMousePos, setCurrentMousePos] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const f = e.target.files[0];
      setFile(f);
      const url = URL.createObjectURL(f);
      setMediaSrc(url);
      setIsVideo(f.type.startsWith('video/'));
      setStep(2);
    }
  };

  const getScaledCoords = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY
    };
  };

  const handleMouseDown = (e) => {
    const pos = getScaledCoords(e);
    setIsDrawing(true);
    setStartPos(pos);
    setCurrentMousePos(pos);
  };

  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    setCurrentMousePos(getScaledCoords(e));
  };

  const handleMouseUp = () => {
    if (!isDrawing) return;
    setIsDrawing(false);
    
    if (!currentMousePos) return;
    
    const x = Math.min(startPos.x, currentMousePos.x);
    const y = Math.min(startPos.y, currentMousePos.y);
    const width = Math.abs(currentMousePos.x - startPos.x);
    const height = Math.abs(currentMousePos.y - startPos.y);
    
    if (width > 10 && height > 10) {
      setRois([...rois, { x, y, width, height }]);
    }
    setCurrentMousePos(null);
  };
  
  const undoLastROI = () => {
    setRois(rois.slice(0, -1));
  };
  
  const handleAutoDetect = async () => {
    if (!file) return;
    setIsAutoDetecting(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8000/auto-calibrate', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) throw new Error('Auto-calibration failed');
      
      const data = await response.json();
      if (data.rois && data.rois.length > 0) {
        setRois(data.rois);
      } else {
        setError('No cars detected for auto-calibration.');
      }
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsAutoDetecting(false);
    }
  };

  const drawCanvas = (imageElement) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (imageElement) {
        ctx.drawImage(imageElement, 0, 0, canvas.width, canvas.height);
    }
    
    ctx.strokeStyle = '#10b981';
    ctx.lineWidth = 3;
    rois.forEach((roi, idx) => {
      ctx.strokeRect(roi.x, roi.y, roi.width, roi.height);
      ctx.fillStyle = '#10b981';
      ctx.font = '16px "Inter"';
      ctx.fillText(`Spot ${idx + 1}`, roi.x, roi.y - 5);
    });
    
    if (isDrawing && currentMousePos) {
      ctx.strokeStyle = '#3b82f6';
      const x = Math.min(startPos.x, currentMousePos.x);
      const y = Math.min(startPos.y, currentMousePos.y);
      const w = Math.abs(currentMousePos.x - startPos.x);
      const h = Math.abs(currentMousePos.y - startPos.y);
      ctx.strokeRect(x, y, w, h);
    }
  };

  useEffect(() => {
    if (step !== 2) return;
    
    let img;
    let vid;
    let animationFrame;
    
    const renderLoop = () => {
        drawCanvas(img || vid);
        animationFrame = requestAnimationFrame(renderLoop);
    };

    if (isVideo) {
      vid = document.createElement('video');
      vid.src = mediaSrc;
      vid.muted = true;
      vid.autoplay = true;
      vid.loop = true;
      vid.onloadedmetadata = () => {
        setNaturalSize({ w: vid.videoWidth, h: vid.videoHeight });
        if(canvasRef.current) {
            canvasRef.current.width = vid.videoWidth;
            canvasRef.current.height = vid.videoHeight;
        }
      };
      renderLoop();
    } else {
      img = new Image();
      img.src = mediaSrc;
      img.onload = () => {
        setNaturalSize({ w: img.naturalWidth, h: img.naturalHeight });
        if(canvasRef.current) {
            canvasRef.current.width = img.naturalWidth;
            canvasRef.current.height = img.naturalHeight;
        }
      };
      renderLoop();
    }
    
    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
    };
  }, [step, mediaSrc, isVideo, rois, isDrawing, currentMousePos]);

  const handleSubmit = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    if (rois.length > 0) {
        formData.append('rois', JSON.stringify(rois));
    }
    
    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      onUploadSuccess(data.filename, rois.length > 0 ? rois.length : 10);
      
    } catch (err) {
      setError(err.message);
      setIsUploading(false);
    }
  };

  if (step === 1) {
    return (
      <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div className="bg-white border border-slate-200 p-8 rounded-2xl max-w-md w-full shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-blue to-rose-500"></div>
          <button onClick={onClose} className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 font-bold text-xl">&times;</button>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Initialize System</h2>
          <p className="text-slate-500 text-sm mb-6">Upload a parking lot feed (image or video) to begin ROI configuration.</p>
          <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Media Source</label>
              <input 
                type="file" 
                accept="video/*,image/*" 
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-500 file:mr-4 file:py-2.5 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-slate-100 file:text-slate-900 hover:file:bg-slate-200 cursor-pointer border border-slate-200 rounded-full bg-white p-1"
              />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-slate-50/95 backdrop-blur flex flex-col z-50">
      <header className="p-6 bg-white border-b border-slate-200 flex justify-between items-center shrink-0 shadow-sm">
        <div>
            <h2 className="text-2xl font-bold text-slate-900">Draw Parking Spots</h2>
            <p className="text-slate-500 text-sm mt-1">Click and drag on the image to draw rectangles over each parking spot, or use AI auto-detection.</p>
        </div>
        <div className="flex gap-4 items-center">
            <span className="text-sm font-semibold text-accent-green bg-accent-green/10 px-4 py-2 rounded-full">Spots Drawn: {rois.length}</span>
            <button 
                onClick={handleAutoDetect} 
                disabled={isAutoDetecting}
                className="px-6 py-2 bg-blue-50 text-blue-600 border border-blue-200 rounded-full font-bold tracking-wider hover:bg-blue-100 transition-colors disabled:opacity-50 flex items-center gap-2 text-sm shadow-sm"
            >
                {isAutoDetecting ? 'DETECTING...' : '✨ AUTO-DETECT'}
            </button>
            <button onClick={undoLastROI} disabled={rois.length === 0} className="px-6 py-2 bg-slate-100 text-slate-600 rounded-full font-medium hover:bg-slate-200 disabled:opacity-50">Undo Last</button>
            <button 
              onClick={handleSubmit} 
              disabled={isUploading || rois.length === 0}
              className={`px-8 py-2.5 rounded-full font-bold tracking-wider transition-all shadow-lg flex items-center justify-center gap-2 ${isUploading || rois.length === 0 ? 'bg-slate-200 text-slate-400 shadow-none cursor-not-allowed' : 'bg-rose-500 hover:bg-rose-600 hover:-translate-y-0.5 shadow-rose-500/30 text-white'}`}
            >
              {isUploading ? 'PROCESSING...' : 'START ANALYSIS'}
            </button>
        </div>
      </header>
      
      <main className="flex-1 overflow-auto p-8 flex items-center justify-center relative bg-slate-100" ref={containerRef}>
        {error && <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-accent-red/90 text-white px-6 py-3 rounded-full shadow-lg z-10 font-medium">{error}</div>}
        <div className="relative border-4 border-white shadow-2xl rounded-xl overflow-hidden bg-white" style={{ maxWidth: '100%', maxHeight: '100%', aspectRatio: naturalSize.w > 0 ? `${naturalSize.w} / ${naturalSize.h}` : 'auto' }}>
            <canvas 
              ref={canvasRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className="w-full h-full object-contain cursor-crosshair"
            />
        </div>
      </main>
    </div>
  );
}

export default UploadModal;
