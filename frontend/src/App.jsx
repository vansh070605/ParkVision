import React, { useState, useEffect } from 'react';
import UploadModal from './components/UploadModal';
import Sidebar from './components/Sidebar';
import VideoFeed from './components/VideoFeed';

function App() {
  const [cameras, setCameras] = useState([]);
  const [activeCamera, setActiveCamera] = useState(null);
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  const [frame, setFrame] = useState(null);
  const [metrics, setMetrics] = useState({
    total_capacity: 0,
    occupied: 0,
    available: 0
  });
  const [isConnected, setIsConnected] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [activeTab, setActiveTab] = useState('live'); // 'live' | 'analytics' | 'predictions' | 'events'
  
  // Analytics Data States
  const [historicalData, setHistoricalData] = useState([]);
  const [peakHours, setPeakHours] = useState([]);
  const [avgDuration, setAvgDuration] = useState(0);
  const [spatialHeatmap, setSpatialHeatmap] = useState([]);
  const [predictions, setPredictions] = useState(null);
  const [violations, setViolations] = useState([]);

  // Fetch cameras on mount
  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/cameras');
      if (response.ok) {
        const data = await response.json();
        setCameras(data);
        if (data.length > 0 && !activeCamera) {
          handleSelectCamera(data[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching cameras:', err);
    }
  };

  const handleSelectCamera = async (camera) => {
    // Stop currently running feed if changing
    if (activeCamera && activeCamera.id !== camera.id) {
      await stopPipeline(activeCamera.id);
    }
    
    setActiveCamera(camera);
    setFrame(null);
    setMetrics({ total_capacity: camera.capacity, occupied: 0, available: camera.capacity });
    setIsSetupComplete(true);
    
    // Start pipeline on backend
    await startPipeline(camera.id);
    fetchAnalytics(camera.id);
  };

  const startPipeline = async (camera_id) => {
    try {
      await fetch(`http://localhost:8000/api/v1/cameras/${camera_id}/start`, { method: 'POST' });
    } catch (err) {
      console.error('Error starting pipeline:', err);
    }
  };

  const stopPipeline = async (camera_id) => {
    try {
      await fetch(`http://localhost:8000/api/v1/cameras/${camera_id}/stop`, { method: 'POST' });
    } catch (err) {
      console.error('Error stopping pipeline:', err);
    }
  };

  const fetchAnalytics = async (camera_id) => {
    try {
      // Trends
      const resTrends = await fetch(`http://localhost:8000/api/v1/analytics/${camera_id}/trends`);
      if (resTrends.ok) setHistoricalData(await resTrends.json());

      // Peaks
      const resPeaks = await fetch(`http://localhost:8000/api/v1/analytics/${camera_id}/peak-hours`);
      if (resPeaks.ok) setPeakHours(await resPeaks.json());

      // Duration
      const resDur = await fetch(`http://localhost:8000/api/v1/analytics/${camera_id}/duration`);
      if (resDur.ok) {
        const d = await resDur.json();
        setAvgDuration(d.average_duration_minutes);
      }

      // Heatmap
      const resHeat = await fetch(`http://localhost:8000/api/v1/analytics/${camera_id}/heatmap`);
      if (resHeat.ok) setSpatialHeatmap(await resHeat.json());

      // Violations / Events
      const resEv = await fetch(`http://localhost:8000/api/v1/analytics/${camera_id}/events`);
      if (resEv.ok) {
        const events = await resEv.json();
        setViolations(events.filter(e => e.event_type !== 'occupancy_change'));
      }
      
      // Predictions
      const resPred = await fetch(`http://localhost:8000/api/v1/predictions/${camera_id}`);
      if (resPred.ok) setPredictions(await resPred.json());

    } catch (err) {
      console.error('Error fetching analytics:', err);
    }
  };

  const handleDeleteCamera = async (camera_id) => {
    try {
      const res = await fetch(`http://localhost:8000/api/v1/cameras/${camera_id}`, { method: 'DELETE' });
      if (res.ok) {
        setCameras(cameras.filter(c => c.id !== camera_id));
        if (activeCamera && activeCamera.id === camera_id) {
          setActiveCamera(null);
          setIsSetupComplete(false);
        }
      }
    } catch (err) {
      console.error('Error deleting camera:', err);
    }
  };

  // WebSocket Live Stream Listener
  useEffect(() => {
    if (!isSetupComplete || !activeCamera) return;

    const wsUrl = `ws://localhost:8000/api/v1/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to stream WebSocket');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setFrame(data.frame);
      setMetrics(data.metrics);
    };

    ws.onclose = () => {
      console.log('Disconnected from stream WebSocket');
      setIsConnected(false);
    };

    // Periodically fetch analytics/predictions (every 10s)
    const interval = setInterval(() => {
      fetchAnalytics(activeCamera.id);
    }, 10000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [isSetupComplete, activeCamera]);

  const handleUploadSuccess = (camera) => {
    setCameras([...cameras, camera]);
    handleSelectCamera(camera);
    setShowModal(false);
  };

  return (
    <div className="bg-slate-950 min-h-screen text-slate-100 font-sans selection:bg-rose-500/20">
      {/* Upper Navigation Bar */}
      <header className="border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-6 py-4 flex justify-between items-center sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 rounded-md bg-gradient-to-r from-rose-500 to-rose-600 rotate-45 shadow-lg shadow-rose-500/30"></div>
          <span className="text-lg font-bold tracking-tight text-white">ParkVision <span className="text-[10px] text-cyan-400 font-mono bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-900/50">PLATFORM v2</span></span>
        </div>
        
        {/* Navigation Tabs */}
        {isSetupComplete && (
          <div className="flex gap-1.5 bg-slate-900 p-1.5 rounded-xl border border-slate-850">
            <button 
              onClick={() => setActiveTab('live')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all ${activeTab === 'live' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Live Feed
            </button>
            <button 
              onClick={() => setActiveTab('analytics')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all ${activeTab === 'analytics' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              Analytics
            </button>
            <button 
              onClick={() => setActiveTab('predictions')}
              className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wider uppercase transition-all ${activeTab === 'predictions' ? 'bg-slate-800 text-white shadow' : 'text-slate-400 hover:text-white'}`}
            >
              AI Forecasts
            </button>
          </div>
        )}

        <div className="flex items-center gap-4">
          {isSetupComplete && (
            <div className="flex items-center gap-2 text-[10px] font-mono font-bold uppercase tracking-widest bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl text-slate-400">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 shadow-md shadow-emerald-500/20' : 'bg-rose-500 animate-pulse'}`}></div>
              {isConnected ? 'STREAM.ONLINE' : 'STREAM.OFFLINE'}
            </div>
          )}
          <button 
            onClick={() => setShowModal(true)}
            className="bg-rose-500 hover:bg-rose-600 text-white px-4 py-2 rounded-xl text-xs font-semibold tracking-wider uppercase transition-all shadow-md shadow-rose-500/10 hover:shadow-rose-500/20"
          >
            Add Camera
          </button>
        </div>
      </header>

      {/* Main Layout Area */}
      {!isSetupComplete ? (
        <div className="max-w-7xl mx-auto px-6 py-24 flex flex-col items-center justify-center text-center">
          <div className="w-16 h-16 bg-slate-900 border border-slate-850 rounded-3xl flex items-center justify-center mb-8 shadow-2xl">
            <span className="text-2xl">📹</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight mb-4">No Camera Feeds Configured</h1>
          <p className="text-slate-400 max-w-md text-sm leading-relaxed mb-8">
            Create an enterprise-grade AI count engine by uploading a lot CCTV stream or calibration frame image.
          </p>
          <button 
            onClick={() => setShowModal(true)}
            className="bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 text-white px-8 py-3 rounded-xl text-sm font-semibold tracking-wider uppercase transition-all shadow-lg shadow-rose-500/20"
          >
            Get Started
          </button>
        </div>
      ) : (
        <div className="flex flex-col lg:grid lg:grid-cols-[1fr_320px] h-[calc(100vh-69px)] min-h-0">
          
          {/* Work area based on Active Tab */}
          <main className="p-6 overflow-y-auto bg-slate-950 flex flex-col min-h-0">
            {activeTab === 'live' && (
              <div className="flex-1 flex flex-col gap-6 min-h-0">
                {/* Live stream player container */}
                <div className="flex-1 min-h-[300px] relative rounded-2xl border border-slate-900 bg-slate-900/40 overflow-hidden flex items-center justify-center">
                  <div className="absolute top-4 left-4 z-10 bg-slate-950/80 backdrop-blur border border-slate-850 text-slate-300 text-[10px] font-mono px-3 py-1.5 rounded-xl uppercase font-semibold">
                    FEED ID: {activeCamera?.name} ({activeCamera?.rtsp_url})
                  </div>
                  <VideoFeed frame={frame} isConnected={isConnected} />
                </div>
                
                {/* Instant Info Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-slate-900/40 border border-slate-900 p-4.5 rounded-2xl">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Average Stay</p>
                    <p className="text-2xl font-mono font-bold text-cyan-400">{avgDuration} <span className="text-xs text-slate-500">mins</span></p>
                  </div>
                  <div className="bg-slate-900/40 border border-slate-900 p-4.5 rounded-2xl">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">Spatial Slots Mapped</p>
                    <p className="text-2xl font-mono font-bold text-purple-400">{activeCamera?.rois?.length || 0} spots</p>
                  </div>
                  <div className="bg-slate-900/40 border border-slate-900 p-4.5 rounded-2xl">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mb-1">AI Status</p>
                    <p className="text-2xl font-mono font-bold text-emerald-400">YOLOv8 + CNN</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="space-y-6">
                {/* Historical line chart */}
                <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-2xl">
                  <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Historical Occupancy Trends (24h)</h3>
                  {historicalData.length === 0 ? (
                    <div className="h-48 flex items-center justify-center text-xs text-slate-600 font-mono">
                      AWAITING SYSTEM TIME LOG DATA...
                    </div>
                  ) : (
                    <div className="h-48 w-full relative">
                      {/* SVG Line Chart */}
                      <svg className="w-full h-full" viewBox="0 0 500 150">
                        {/* Horizontal Gridlines */}
                        <line x1="0" y1="20" x2="500" y2="20" stroke="#1e293b" strokeDasharray="3" />
                        <line x1="0" y1="75" x2="500" y2="75" stroke="#1e293b" strokeDasharray="3" />
                        <line x1="0" y1="130" x2="500" y2="130" stroke="#1e293b" strokeDasharray="3" />
                        
                        {/* Generate polyline points dynamically */}
                        {(() => {
                          const points = historicalData.map((d, i) => {
                            const x = (i / (historicalData.length - 1)) * 500;
                            // Max capacity is the scale (avoid divide by zero)
                            const cap = activeCamera?.capacity || 10;
                            const y = 130 - (d.occupied / cap) * 110;
                            return `${x},${y}`;
                          }).join(' ');
                          
                          return (
                            <>
                              <polyline fill="none" stroke="#f43f5e" strokeWidth="2.5" points={points} />
                              {historicalData.map((d, i) => {
                                const x = (i / (historicalData.length - 1)) * 500;
                                const cap = activeCamera?.capacity || 10;
                                const y = 130 - (d.occupied / cap) * 110;
                                return (
                                  <g key={i}>
                                    <circle cx={x} cy={y} r="3" fill="#f43f5e" />
                                    {/* Hover info overlay */}
                                    <text x={x} y={y - 8} fill="#94a3b8" fontSize="8" textAnchor="middle" fontFamily="monospace">
                                      {d.occupied}
                                    </text>
                                  </g>
                                );
                              })}
                            </>
                          );
                        })()}
                      </svg>
                      {/* X axis labels */}
                      <div className="flex justify-between mt-2 text-[8px] font-mono text-slate-500">
                        <span>{new Date(historicalData[0]?.time).toLocaleTimeString([], {hour: '2-digit'})}</span>
                        <span>{new Date(historicalData[Math.floor(historicalData.length/2)]?.time).toLocaleTimeString([], {hour: '2-digit'})}</span>
                        <span>{new Date(historicalData[historicalData.length-1]?.time).toLocaleTimeString([], {hour: '2-digit'})}</span>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Peak hours bar chart */}
                  <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-2xl">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Peak Hour Aggregates</h3>
                    {peakHours.length === 0 ? (
                      <div className="h-40 flex items-center justify-center text-xs text-slate-600 font-mono">
                        AWAITING RECORD HISTORY LOGS...
                      </div>
                    ) : (
                      <div className="h-40 flex items-end justify-between gap-2.5 pt-6">
                        {peakHours.slice(0, 10).map((p, idx) => {
                          const cap = activeCamera?.capacity || 10;
                          const heightPct = Math.min(100, (p.avg_occupied / cap) * 100);
                          return (
                            <div key={idx} className="flex-1 flex flex-col items-center">
                              <span className="text-[8px] font-mono text-slate-400 mb-1">{p.avg_occupied}</span>
                              <div className="w-full bg-slate-800 rounded-t-md relative overflow-hidden" style={{ height: '80px' }}>
                                <div 
                                  className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-cyan-600 to-cyan-400 rounded-t-md" 
                                  style={{ height: `${heightPct}%` }}
                                ></div>
                              </div>
                              <span className="text-[8px] font-mono text-slate-500 mt-1.5">{p.hour}:00</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Spatial occupancy Heatmap */}
                  <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-2xl">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4">Spatial Occupancy Hotspots</h3>
                    {spatialHeatmap.length === 0 ? (
                      <div className="h-40 flex items-center justify-center text-xs text-slate-600 font-mono">
                        NO SPOT ACTIVITY CAPTURED YET
                      </div>
                    ) : (
                      <div className="grid grid-cols-5 gap-3 p-2">
                        {spatialHeatmap.map((spot, i) => {
                          // Find highest count to scale heat color
                          const maxCount = Math.max(...spatialHeatmap.map(s => s.count), 1);
                          const heatPct = spot.count / maxCount;
                          
                          // Color gradient from green to red based on occupancy count
                          const colorStyle = {
                            backgroundColor: `rgba(239, 68, 68, ${0.1 + heatPct * 0.9})`,
                            borderColor: `rgba(239, 68, 68, ${0.3 + heatPct * 0.7})`
                          };
                          
                          return (
                            <div 
                              key={i}
                              style={colorStyle}
                              className="border p-2 rounded-xl text-center flex flex-col justify-center items-center shadow-sm"
                            >
                              <span className="text-[9px] font-bold text-white leading-none">Spot {spot.spot_id+1}</span>
                              <span className="text-[10px] font-mono font-extrabold mt-1 text-red-200">{spot.count}x</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'predictions' && (
              <div className="bg-slate-900/40 border border-slate-900 p-6 rounded-2xl">
                <div className="flex justify-between items-center mb-6">
                  <div>
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest">LSTM Predictive Forecasting</h3>
                    <p className="text-xs text-slate-500 mt-1">AI models future occupancy percentages based on sequential temporal trends.</p>
                  </div>
                  
                  <button 
                    onClick={async () => {
                      await fetch(`http://localhost:8000/api/v1/predictions/${activeCamera.id}/retrain`, {method: 'POST'});
                      fetchAnalytics(activeCamera.id);
                    }}
                    className="text-[10px] font-bold text-cyan-400 border border-cyan-500/20 bg-cyan-500/10 px-3 py-1.5 rounded-lg hover:bg-cyan-500/20"
                  >
                    RETRAIN LSTM
                  </button>
                </div>
                
                {!predictions ? (
                  <div className="h-56 flex items-center justify-center text-xs text-slate-600 font-mono">
                    AWAITING SUFFICIENT RECORD PATTERNS FOR FORECASTING...
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6 pt-4">
                    {/* Prediction 15m */}
                    <div className="bg-slate-850/50 border border-slate-800 p-5 rounded-2xl flex flex-col justify-between">
                      <div>
                        <span className="text-[9px] font-mono font-bold text-cyan-400 uppercase tracking-widest bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-900/30">Next 15 Mins</span>
                        <p className="text-slate-400 text-xs mt-3">Expected Occupancy</p>
                      </div>
                      <div className="mt-4 flex justify-between items-end">
                        <p className="text-4xl font-mono font-extrabold text-white">{predictions.prediction_15m} <span className="text-xs text-slate-500">spots</span></p>
                        <p className="text-xs font-mono text-cyan-400">
                          {((predictions.prediction_15m / activeCamera.capacity) * 100).toFixed(0)}% Util
                        </p>
                      </div>
                    </div>
                    {/* Prediction 30m */}
                    <div className="bg-slate-850/50 border border-slate-800 p-5 rounded-2xl flex flex-col justify-between">
                      <div>
                        <span className="text-[9px] font-mono font-bold text-purple-400 uppercase tracking-widest bg-purple-950/50 px-2 py-0.5 rounded border border-purple-900/30">Next 30 Mins</span>
                        <p className="text-slate-400 text-xs mt-3">Expected Occupancy</p>
                      </div>
                      <div className="mt-4 flex justify-between items-end">
                        <p className="text-4xl font-mono font-extrabold text-white">{predictions.prediction_30m} <span className="text-xs text-slate-500">spots</span></p>
                        <p className="text-xs font-mono text-purple-400">
                          {((predictions.prediction_30m / activeCamera.capacity) * 100).toFixed(0)}% Util
                        </p>
                      </div>
                    </div>
                    {/* Prediction 60m */}
                    <div className="bg-slate-850/50 border border-slate-800 p-5 rounded-2xl flex flex-col justify-between">
                      <div>
                        <span className="text-[9px] font-mono font-bold text-pink-400 uppercase tracking-widest bg-pink-950/50 px-2 py-0.5 rounded border border-pink-900/30">Next 1 Hour</span>
                        <p className="text-slate-400 text-xs mt-3">Expected Occupancy</p>
                      </div>
                      <div className="mt-4 flex justify-between items-end">
                        <p className="text-4xl font-mono font-extrabold text-white">{predictions.prediction_60m} <span className="text-xs text-slate-500">spots</span></p>
                        <p className="text-xs font-mono text-pink-400">
                          {((predictions.prediction_60m / activeCamera.capacity) * 100).toFixed(0)}% Util
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </main>
          
          {/* Side panel telemetry metrics */}
          <aside className="shrink-0 lg:h-full lg:overflow-y-auto">
            <Sidebar 
              metrics={metrics}
              cameras={cameras}
              activeCamera={activeCamera}
              onCameraChange={handleSelectCamera}
              violations={violations}
              onAddCamera={() => setShowModal(true)}
              onDeleteCamera={handleDeleteCamera}
            />
          </aside>
        </div>
      )}

      {showModal && <UploadModal onUploadSuccess={handleUploadSuccess} onClose={() => setShowModal(false)} />}
    </div>
  );
}

export default App;
