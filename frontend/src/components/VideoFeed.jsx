import React from 'react';

function VideoFeed({ frame, isConnected }) {
  if (!isConnected) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-industrial-900">
        <div className="w-12 h-12 border-4 border-industrial-700 border-t-accent-blue rounded-full animate-spin mb-4"></div>
        <p className="text-industrial-600 font-mono text-sm tracking-widest">CONNECTING TO STREAM...</p>
      </div>
    );
  }

  if (!frame) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-industrial-900">
        <p className="text-industrial-600 font-mono text-sm tracking-widest">WAITING FOR DATA...</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full relative overflow-hidden bg-black flex items-center justify-center">
      <img
        src={`data:image/jpeg;base64,${frame}`}
        alt="Live CCTV Feed"
        className="w-full h-full object-contain filter contrast-125 saturate-110"
      />
      {/* Scanline overlay for aesthetic */}
      <div className="absolute inset-0 pointer-events-none bg-[url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiPjxyZWN0IHdpZHRoPSI0IiBoZWlnaHQ9IjIiIGZpbGw9IiMwMDAiIGZpbGwtb3BhY2l0eT0iMC4yIi8+PC9zdmc+')] opacity-20 z-10 mix-blend-overlay"></div>
    </div>
  );
}

export default VideoFeed;
