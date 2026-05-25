import React, { useState, useEffect } from 'react';
import UploadModal from './components/UploadModal';
import Sidebar from './components/Sidebar';
import VideoFeed from './components/VideoFeed';

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
  const [showModal, setShowModal] = useState(false);

  const handleUploadSuccess = (filename, capacity) => {
    setFeedConfig({ filename, capacity });
    setIsSetupComplete(true);
    setShowModal(false);
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

  if (isSetupComplete) {
    return (
      <div className="custom-grid bg-slate-50 min-h-screen">
        <header className="glass-panel col-[header] flex justify-between items-center px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 rounded bg-rose-500 rotate-45 shadow-lg shadow-rose-500/40"></div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">ParkVision</h1>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-widest bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-accent-green' : 'bg-accent-red animate-pulse'}`}></div>
            {isConnected ? 'SYS.ONLINE' : 'SYS.OFFLINE'}
          </div>
        </header>

        <main className="col-[main] flex flex-col relative group">
          <div className="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur text-slate-800 text-xs font-mono px-3 py-1.5 rounded shadow-sm border border-slate-200 uppercase font-semibold">
            FEED: {feedConfig.filename}
          </div>
          <VideoFeed frame={frame} isConnected={isConnected} />
        </main>

        <aside className="col-[sidebar] overflow-y-auto">
          <Sidebar metrics={metrics} />
        </aside>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white font-sans selection:bg-rose-500/20">
      <nav className="max-w-7xl mx-auto px-6 py-6 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-rose-500 rotate-45 flex items-center justify-center shadow-lg shadow-rose-500/30"></div>
          <span className="text-xl font-bold tracking-tight text-slate-900">ParkVision</span>
        </div>
        <div className="hidden md:flex gap-8 text-sm font-medium text-slate-600">
          <a href="#" className="hover:text-slate-900 transition-colors">About</a>
          <a href="#" className="hover:text-slate-900 transition-colors">Company</a>
          <a href="#" className="hover:text-slate-900 transition-colors">Pricing</a>
        </div>
        <button 
          onClick={() => setShowModal(true)}
          className="bg-rose-500 hover:bg-rose-600 text-white px-6 py-2.5 rounded-full text-sm font-semibold transition-all shadow-lg shadow-rose-500/20 hover:shadow-rose-500/40 hover:-translate-y-0.5"
        >
          Get Started
        </button>
      </nav>

      <div className="max-w-7xl mx-auto px-6 pt-20 pb-32 grid md:grid-cols-2 gap-12 items-center relative">
        <div className="z-10">
          <h1 className="text-5xl md:text-6xl font-extrabold text-slate-900 leading-[1.1] mb-6 tracking-tight">
            Take care of your parking <span className="text-rose-500">every day.</span>
          </h1>
          <p className="text-lg text-slate-500 mb-8 max-w-md leading-relaxed">
            Build a well-presented parking lot that everyone will love. Utilize AI to develop resources continually and track utilization with absolute precision.
          </p>
          <div className="flex gap-4 items-center">
            <button 
              onClick={() => setShowModal(true)}
              className="bg-rose-500 hover:bg-rose-600 text-white px-8 py-3.5 rounded-full text-base font-semibold transition-all shadow-xl shadow-rose-500/20 hover:shadow-rose-500/40 hover:-translate-y-0.5"
            >
              Track your performance
            </button>
            <a href="#" className="text-slate-600 font-medium text-sm hover:text-slate-900">Learn more &rarr;</a>
          </div>
        </div>
        
        <div className="relative h-[500px] w-full hidden md:block">
          <div className="absolute right-0 top-0 w-[400px] h-[500px] bg-slate-100 rounded-3xl overflow-hidden shadow-2xl rotate-3 transform origin-bottom-right transition-transform hover:rotate-0 duration-500 border border-slate-200">
            <img src="https://images.unsplash.com/photo-1506521781263-d8422e82f27a?auto=format&fit=crop&q=80&w=800" alt="Hero" className="w-full h-full object-cover" />
          </div>
          
          <div className="absolute -left-12 top-20 bg-white p-4 rounded-2xl shadow-xl animate-pulse-slow border border-slate-100">
            <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">19</div>
            <p className="text-xs font-bold text-slate-400 mt-2 text-center uppercase tracking-wider">Available</p>
          </div>
          <div className="absolute right-12 -bottom-6 bg-rose-500 text-white px-6 py-4 rounded-2xl shadow-xl shadow-rose-500/30 hover:scale-105 transition-transform">
            <p className="text-2xl font-bold leading-none">99.9%</p>
            <p className="text-xs opacity-80 mt-1">Accuracy Rate</p>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-100 bg-slate-50 py-16">
        <p className="text-center text-sm font-semibold text-slate-400 uppercase tracking-widest mb-8">Trusted by brands all over the world</p>
        <div className="flex flex-wrap justify-center items-center gap-12 md:gap-24 opacity-40 grayscale">
          <span className="text-2xl font-bold font-sans">slack</span>
          <span className="text-2xl font-bold font-sans">Dropbox</span>
          <span className="text-2xl font-bold font-sans">Spotify</span>
          <span className="text-2xl font-bold font-sans">amazon</span>
          <span className="text-2xl font-bold font-sans tracking-widest">NETFLIX</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-24 bg-white">
        <div className="text-center mb-16">
          <p className="text-rose-500 font-semibold text-sm uppercase tracking-widest mb-3">How it works?</p>
          <h2 className="text-4xl font-bold text-slate-900 tracking-tight">Find out how<br/>simple and easy it is</h2>
        </div>
        
        <div className="grid md:grid-cols-3 gap-12 text-center">
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xl font-bold mb-6">1</div>
            <h3 className="text-xl font-bold text-slate-900 mb-4">Upload your feed.</h3>
            <p className="text-slate-500 leading-relaxed">Simply upload an image or video feed of your parking lot. The system handles all formats instantly.</p>
          </div>
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-accent-green/20 text-accent-green rounded-full flex items-center justify-center text-xl font-bold mb-6">2</div>
            <h3 className="text-xl font-bold text-slate-900 mb-4">Draw your spots.</h3>
            <p className="text-slate-500 leading-relaxed">Use our interactive canvas to draw custom regions of interest over your exact parking spaces.</p>
          </div>
          <div className="flex flex-col items-center">
            <div className="w-12 h-12 bg-rose-500/20 text-rose-500 rounded-full flex items-center justify-center text-xl font-bold mb-6">3</div>
            <h3 className="text-xl font-bold text-slate-900 mb-4">AI takes over.</h3>
            <p className="text-slate-500 leading-relaxed">YOLOv8 actively monitors the lot and provides real-time telemetry on capacity and utilization.</p>
          </div>
        </div>
      </div>

      {showModal && <UploadModal onUploadSuccess={handleUploadSuccess} onClose={() => setShowModal(false)} />}
    </div>
  );
}

export default App;
