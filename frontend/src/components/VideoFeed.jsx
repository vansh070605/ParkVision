import React from 'react';

function VideoFeed({ frame, isConnected }) {
  if (!isConnected) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50">
        <div className="w-12 h-12 border-4 border-slate-200 border-t-brand-rose rounded-full animate-spin mb-4"></div>
        <p className="text-slate-400 font-mono text-sm tracking-widest font-semibold">CONNECTING TO STREAM...</p>
      </div>
    );
  }

  if (!frame) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-50">
        <p className="text-slate-400 font-mono text-sm tracking-widest font-semibold">WAITING FOR DATA...</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative overflow-hidden bg-white flex items-center justify-center border-4 border-white rounded-xl shadow-soft">
      <img
        src={`data:image/jpeg;base64,${frame}`}
        alt="Live CCTV Feed"
        className="w-full h-full object-contain filter contrast-105 saturate-105 rounded-lg"
      />
    </div>
  );
}

export default VideoFeed;
