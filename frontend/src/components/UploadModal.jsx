import React, { useState, useRef, useEffect } from 'react';

function UploadModal({ onUploadSuccess, onClose }) {
  const [cameraName, setCameraName] = useState('Main Parking Lot Feed');
  const [file, setFile] = useState(null);
  const [step, setStep] = useState(1); // 1: Info & File upload, 2: ROI Draw
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
  
  const [selectedRoiIndex, setSelectedRoiIndex] = useState(null);

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
    if (!canvas) return { x: 0, y: 0 };
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
      setRois([...rois, { x, y, width, height, is_ev: false }]);
    }
    setCurrentMousePos(null);
  };
  
  const undoLastROI = () => {
    setRois(rois.slice(0, -1));
  };
  
  const toggleEV = (index) => {
    const updated = [...rois];
    updated[index].is_ev = !updated[index].is_ev;
    setRois(updated);
  };

  const deleteRoi = (index) => {
    setRois(rois.filter((_, idx) => idx !== index));
    setSelectedRoiIndex(null);
  };
  
  const handleAutoDetect = async () => {
    if (!file) return;
    setIsAutoDetecting(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/auto-calibrate', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) throw new Error('Auto-calibration failed');
      
      const data = await response.json();
      if (data.rois && data.rois.length > 0) {
        // Map detected ROIs to EV structure
        const mappedRois = data.rois.map(roi => ({ ...roi, is_ev: false }));
        setRois(mappedRois);
      } else {
        setError('Auto-detector could not locate any parking lot patterns.');
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
    
    // Draw all ROIs
    rois.forEach((roi, idx) => {
      const isSelected = selectedRoiIndex === idx;
      
      // Color scheme: Selected -> Yellow, EV -> Cyan, Normal -> Emerald
      if (isSelected) {
        ctx.strokeStyle = '#f59e0b';
        ctx.fillStyle = 'rgba(245, 158, 11, 0.15)';
      } else if (roi.is_ev) {
        ctx.strokeStyle = '#06b6d4';
        ctx.fillStyle = 'rgba(6, 182, 212, 0.05)';
      } else {
        ctx.strokeStyle = '#10b981';
        ctx.fillStyle = 'rgba(16, 185, 129, 0.05)';
      }
      
      ctx.lineWidth = isSelected ? 4 : 2;
      ctx.strokeRect(roi.x, roi.y, roi.width, roi.height);
      ctx.fillRect(roi.x, roi.y, roi.width, roi.height);
      
      // Text drawing
      ctx.fillStyle = isSelected ? '#f59e0b' : (roi.is_ev ? '#06b6d4' : '#10b981');
      ctx.font = 'bold 14px "JetBrains Mono", monospace';
      const label = `Spot ${idx + 1}${roi.is_ev ? ' [EV]' : ''}`;
      ctx.fillText(label, roi.x + 5, roi.y + 20);
    });
    
    // Draw current drag box
    if (isDrawing && currentMousePos) {
      ctx.strokeStyle = '#3b82f6';
      ctx.fillStyle = 'rgba(59, 130, 246, 0.1)';
      ctx.lineWidth = 2;
      const x = Math.min(startPos.x, currentMousePos.x);
      const y = Math.min(startPos.y, currentMousePos.y);
      const w = Math.abs(currentMousePos.x - startPos.x);
      const h = Math.abs(currentMousePos.y - startPos.y);
      ctx.strokeRect(x, y, w, h);
      ctx.fillRect(x, y, w, h);
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
  }, [step, mediaSrc, isVideo, rois, isDrawing, currentMousePos, selectedRoiIndex]);

  const handleSubmit = async () => {
    if (!file) return;
    
    setIsUploading(true);
    setError('');
    
    // Step 1: Upload media file
    const uploadForm = new FormData();
    uploadForm.append('file', file);
    if (rois.length > 0) {
      uploadForm.append('rois', JSON.stringify(rois));
    }
    
    try {
      const uploadRes = await fetch('http://localhost:8000/api/v1/upload', {
        method: 'POST',
        body: uploadForm,
      });
      
      if (!uploadRes.ok) throw new Error('Media upload failed');
      const uploadData = await uploadRes.json();
      
      // Step 2: Register camera in Database
      const cameraPayload = {
        name: cameraName,
        rtsp_url: uploadData.filename,
        capacity: rois.length > 0 ? rois.length : 10,
        rois: rois
      };
      
      const cameraRes = await fetch('http://localhost:8000/api/v1/cameras', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cameraPayload),
      });
      
      if (!cameraRes.ok) throw new Error('Failed to register camera in system');
      const cameraData = await cameraRes.json();
      
      onUploadSuccess(cameraData);
      
    } catch (err) {
      setError(err.message);
      setIsUploading(false);
    }
  };

  if (step === 1) {
    return (
      <div className="fixed inset-0 bg-slate-950/70 backdrop-blur-md flex items-center justify-center z-50 p-4">
        <div className="bg-slate-900 border border-slate-800 p-8 rounded-3xl max-w-md w-full shadow-2xl relative overflow-hidden text-white">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-cyan-500 to-rose-500"></div>
          <button onClick={onClose} className="absolute top-4 right-4 text-slate-400 hover:text-white font-bold text-xl transition-colors">&times;</button>
          
          <h2 className="text-2xl font-bold tracking-tight mb-2">Configure Camera Feed</h2>
          <p className="text-slate-400 text-sm mb-6">Add a new CCTV stream or overhead video to the AI analytics platform.</p>
          
          <div className="space-y-4">
              <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Camera Alias</label>
                  <input 
                    type="text" 
                    value={cameraName} 
                    onChange={(e) => setCameraName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 px-4 py-2.5 rounded-xl text-sm focus:outline-none focus:border-rose-500"
                    placeholder="Main Entrance Lot"
                  />
              </div>
              <div>
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Media File (Calibration Frame)</label>
                  <input 
                    type="file" 
                    accept="video/*,image/*" 
                    onChange={handleFileChange}
                    className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer border border-slate-700 rounded-xl bg-slate-800 p-1.5"
                  />
              </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-slate-950 backdrop-blur-lg flex flex-col z-50 text-white font-sans">
      <header className="p-6 bg-slate-900 border-b border-slate-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 shrink-0 shadow-md">
        <div>
            <h2 className="text-2xl font-extrabold tracking-tight">AI ROI Calibration Tool</h2>
            <p className="text-slate-400 text-sm mt-1">Drag boxes over slots to map spaces. Tag EV specific spots in the list.</p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
            <span className="text-sm font-semibold text-cyan-400 bg-cyan-500/10 px-4 py-2 rounded-xl border border-cyan-500/20">Spots Mapped: {rois.length}</span>
            <button 
                onClick={handleAutoDetect} 
                disabled={isAutoDetecting}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-xl font-bold text-xs tracking-wider transition-colors shadow-lg flex items-center gap-2"
            >
                {isAutoDetecting ? 'DETECTING...' : '✨ AUTO-CALIBRATE'}
            </button>
            <button onClick={undoLastROI} disabled={rois.length === 0} className="px-5 py-2.5 bg-slate-800 text-slate-300 rounded-xl text-xs font-semibold hover:bg-slate-700 disabled:opacity-50">Undo Last</button>
            <button 
              onClick={handleSubmit} 
              disabled={isUploading || rois.length === 0}
              className={`px-6 py-2.5 rounded-xl font-bold text-xs tracking-wider transition-all shadow-lg flex items-center justify-center gap-2 ${isUploading || rois.length === 0 ? 'bg-slate-800 text-slate-600 cursor-not-allowed' : 'bg-gradient-to-r from-rose-500 to-rose-600 text-white hover:shadow-rose-500/20'}`}
            >
              {isUploading ? 'SAVING PIPELINE...' : 'INITIALIZE PIPELINE'}
            </button>
        </div>
      </header>
      
      <div className="flex-1 flex flex-col lg:flex-row min-h-0 bg-slate-950">
        {/* Interactive Canvas Viewport */}
        <main className="flex-1 overflow-auto p-6 flex items-center justify-center relative bg-slate-900" ref={containerRef}>
          {error && <div className="absolute top-6 left-1/2 -translate-x-1/2 bg-rose-500 text-white px-6 py-3 rounded-xl shadow-lg z-10 text-sm font-semibold">{error}</div>}
          <div className="relative border border-slate-800 shadow-2xl rounded-2xl overflow-hidden bg-slate-950" style={{ maxWidth: '100%', maxHeight: '100%', aspectRatio: naturalSize.w > 0 ? `${naturalSize.w} / ${naturalSize.h}` : 'auto' }}>
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
        
        {/* Spots Detail sidebar */}
        <aside className="w-full lg:w-80 bg-slate-900 border-t lg:border-t-0 lg:border-l border-slate-800 flex flex-col overflow-hidden shrink-0">
          <div className="p-4 border-b border-slate-800 shrink-0">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">Active Slot Directory</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
            {rois.length === 0 ? (
              <div className="h-full flex items-center justify-center text-center p-8 text-slate-500 text-sm">
                No slots mapped yet. Draw rectangles on the viewport canvas to start.
              </div>
            ) : (
              rois.map((roi, idx) => (
                <div 
                  key={idx}
                  onClick={() => setSelectedRoiIndex(selectedRoiIndex === idx ? null : idx)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${selectedRoiIndex === idx ? 'bg-amber-500/10 border-amber-500/40' : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800'}`}
                >
                  <div className="flex justify-between items-center">
                    <span className="font-mono text-sm font-bold">Spot {idx + 1}</span>
                    <div className="flex gap-2">
                      <button 
                        onClick={(e) => { e.stopPropagation(); toggleEV(idx); }}
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${roi.is_ev ? 'bg-cyan-500 text-slate-950' : 'bg-slate-700 text-slate-400'}`}
                      >
                        {roi.is_ev ? 'EV ACTIVE' : 'MARK EV'}
                      </button>
                      <button 
                        onClick={(e) => { e.stopPropagation(); deleteRoi(idx); }}
                        className="text-slate-500 hover:text-rose-500 font-bold px-1"
                      >
                        &times;
                      </button>
                    </div>
                  </div>
                  <div className="text-[10px] text-slate-500 font-mono mt-1.5">
                    X: {Math.round(roi.x)} | Y: {Math.round(roi.y)} | W: {Math.round(roi.width)} | H: {Math.round(roi.height)}
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export default UploadModal;
