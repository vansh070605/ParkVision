import React, { useState, useEffect } from 'react';
import VideoFeed from './components/VideoFeed';
import Sidebar from './components/Sidebar';
import UploadModal from './components/UploadModal';

function App() {
  const [isSetupComplete, setIsSetupComplete] = useState(false);
  const [feedConfig, setFeedConfig] = useState({ filename: '', capacity: 10 });
  const [frame, setFrame] = useState(null);
  const [metrics, setMetrics] = useState({
    total_capacity: 0,
    occupied: 0,
    available: 0
  });
  const [isConnected, setIsConnected] = useState(false);

  const handleUploadSuccess = (filename, capacity) => {
    setFeedConfig({ filename, capacity });
    setIsSetupComplete(true);
  };

  useEffect(() => {
    if (!isSetupComplete) return;

    const wsUrl = `ws://localhost:8000/ws?filename=${encodeURIComponent(feedConfig.filename)}&capacity=${feedConfig.capacity}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('Connected to WebSocket');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setFrame(data.frame);
      setMetrics(data.metrics);
    };

    ws.onclose = () => {
      console.log('Disconnected from WebSocket');
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [isSetupComplete, feedConfig]);

  return (
    <>
      {!isSetupComplete && <UploadModal onUploadSuccess={handleUploadSuccess} />}
      
      <div className="custom-grid bg-industrial-900">
        <header className="glass-panel col-[header] flex items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-accent-blue animate-pulse-slow"></div>
            <h1 className="text-2xl font-bold tracking-wider text-white">ParkVision<span className="text-accent-blue text-lg">.AI</span></h1>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-accent-green' : 'bg-accent-red'}`}></span>
            <span className="text-sm font-mono text-gray-400">
              {isConnected ? 'SYS.ONLINE' : 'SYS.OFFLINE'}
            </span>
          </div>
        </header>

        <main className="glass-panel col-[main] overflow-hidden flex flex-col relative group">
          <div className="absolute top-4 left-4 z-10 bg-black/50 px-3 py-1 rounded border border-gray-700 backdrop-blur">
            <span className="text-xs font-mono text-gray-300">
              {feedConfig.filename ? `FEED: ${feedConfig.filename.toUpperCase()}` : 'WAITING FOR FEED...'}
            </span>
          </div>
          <VideoFeed frame={frame} isConnected={isConnected} />
        </main>

        <aside className="glass-panel col-[sidebar] p-6 flex flex-col gap-6">
          <Sidebar metrics={metrics} />
        </aside>
      </div>
    </>
  );
}

export default App;
