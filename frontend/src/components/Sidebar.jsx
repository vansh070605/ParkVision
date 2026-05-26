import React from 'react';

function Sidebar({ 
  metrics, 
  cameras, 
  activeCamera, 
  onCameraChange, 
  violations, 
  onAddCamera,
  onDeleteCamera
}) {
  const safeMetrics = metrics || { total_capacity: 0, occupied: 0, available: 0 };
  const { total_capacity, occupied, available } = safeMetrics;
  
  const utilizationRate = total_capacity > 0 
    ? ((occupied / total_capacity) * 100).toFixed(1) 
    : 0;

  return (
    <div className="flex flex-col h-full bg-slate-900 border-l border-slate-800 text-white p-6 shadow-2xl overflow-y-auto font-sans">
      {/* Metrics Section */}
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 border-b border-slate-850 pb-3">
        Active Telemetry
      </h2>
      
      <div className="flex flex-col gap-4 mb-8">
        <div className="flex gap-4">
          {/* Available */}
          <div className="flex-1 bg-slate-850/60 p-4 rounded-2xl border border-slate-800 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-12 h-12 bg-emerald-500/10 rounded-bl-full -mr-6 -mt-6"></div>
            <p className="text-slate-400 text-xs font-semibold mb-1">Available</p>
            <p className="text-3xl font-mono font-extrabold text-emerald-400">{available}</p>
          </div>
          {/* Occupied */}
          <div className="flex-1 bg-slate-850/60 p-4 rounded-2xl border border-slate-800 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-12 h-12 bg-rose-500/10 rounded-bl-full -mr-6 -mt-6"></div>
            <p className="text-slate-400 text-xs font-semibold mb-1">Occupied</p>
            <p className="text-3xl font-mono font-extrabold text-rose-500">{occupied}</p>
          </div>
        </div>

        {/* Capacity / Utilization */}
        <div className="bg-slate-850/80 p-5 rounded-2xl border border-slate-800">
          <div className="flex justify-between items-end">
            <div>
              <p className="text-slate-400 text-xs font-semibold mb-1 font-sans">Total Capacity</p>
              <p className="text-2xl font-mono font-extrabold text-white">{total_capacity}</p>
            </div>
            <div className="text-right">
              <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Utilization</p>
              <p className="text-base font-mono font-bold text-cyan-400">{utilizationRate}%</p>
            </div>
          </div>
          
          <div className="w-full bg-slate-800 h-2 rounded-full mt-4 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-cyan-400 to-rose-500 transition-all duration-500 ease-out"
              style={{ width: `${utilizationRate}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Camera Directory */}
      <div className="flex justify-between items-center mb-4 border-b border-slate-850 pb-2">
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
          Camera Directories
        </h2>
        <button 
          onClick={onAddCamera}
          className="text-xs font-bold text-cyan-400 hover:text-cyan-300"
        >
          + ADD
        </button>
      </div>

      <div className="space-y-2 mb-8">
        {cameras.length === 0 ? (
          <div className="text-center p-4 text-xs text-slate-500">
            No cameras registered.
          </div>
        ) : (
          cameras.map(cam => (
            <div 
              key={cam.id}
              onClick={() => onCameraChange(cam)}
              className={`p-3 rounded-xl border flex justify-between items-center cursor-pointer transition-all ${activeCamera && activeCamera.id === cam.id ? 'bg-slate-800 border-cyan-500/50' : 'bg-slate-850/40 border-slate-800 hover:bg-slate-800'}`}
            >
              <div>
                <p className="text-xs font-bold truncate max-w-[150px]">{cam.name}</p>
                <p className="text-[10px] text-slate-500 font-mono mt-0.5 truncate max-w-[150px]">{cam.rtsp_url}</p>
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); onDeleteCamera(cam.id); }}
                className="text-slate-500 hover:text-rose-500 text-xs px-2"
              >
                &times;
              </button>
            </div>
          ))
        )}
      </div>

      {/* Active System Violations */}
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-4 border-b border-slate-850 pb-2">
        Critical Violations
      </h2>

      <div className="space-y-2.5 flex-1 min-h-[150px] overflow-y-auto">
        {violations.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-600 font-mono">
            SYS: NO ACTIVE VIOLATIONS
          </div>
        ) : (
          violations.map((v, i) => (
            <div key={i} className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl flex items-start gap-2.5">
              <div className="w-2 h-2 rounded-full bg-rose-500 mt-1.5 shrink-0 animate-ping"></div>
              <div>
                <p className="text-xs text-rose-200 font-semibold">{v.description}</p>
                <p className="text-[9px] text-slate-500 font-mono mt-1">
                  {new Date(v.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Sidebar;
