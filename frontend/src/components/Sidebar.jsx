import React from 'react';

function Sidebar({ metrics }) {
  const safeMetrics = metrics || { total_capacity: 0, occupied: 0, available: 0 };
  const { total_capacity, occupied, available } = safeMetrics;
  
  const utilizationRate = total_capacity > 0 
    ? ((occupied / total_capacity) * 100).toFixed(1) 
    : 0;

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl p-6 shadow-2xl border border-slate-100">
      <h2 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6 border-b border-slate-100 pb-3">
        Telemetry & Analytics
      </h2>
      
      <div className="flex flex-col gap-6">
        {/* Metric Card: Available */}
        <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 hover:border-accent-green/30 transition-all duration-300 relative overflow-hidden group shadow-sm hover:shadow-md">
          <div className="absolute top-0 right-0 w-16 h-16 bg-accent-green/10 rounded-bl-full -mr-8 -mt-8 group-hover:bg-accent-green/20 transition-colors"></div>
          <p className="text-slate-500 text-sm font-semibold mb-1">Available Spots</p>
          <p className="text-4xl font-mono font-extrabold text-accent-green">{available}</p>
        </div>

        {/* Metric Card: Occupied */}
        <div className="bg-slate-50 p-5 rounded-xl border border-slate-100 hover:border-rose-500/30 transition-all duration-300 relative overflow-hidden group shadow-sm hover:shadow-md">
          <div className="absolute top-0 right-0 w-16 h-16 bg-rose-500/10 rounded-bl-full -mr-8 -mt-8 group-hover:bg-rose-500/20 transition-colors"></div>
          <p className="text-slate-500 text-sm font-semibold mb-1">Occupied Spots</p>
          <p className="text-4xl font-mono font-extrabold text-rose-500">{occupied}</p>
        </div>

        {/* Metric Card: Total */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 hover:border-slate-300 transition-all duration-300 shadow-sm hover:shadow-md">
          <div className="flex justify-between items-end">
            <div>
              <p className="text-slate-500 text-sm font-semibold mb-1">Total Capacity</p>
              <p className="text-3xl font-mono font-extrabold text-slate-900">{total_capacity}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Utilization</p>
              <p className="text-lg font-mono font-bold text-accent-blue">{utilizationRate}%</p>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-slate-100 h-2 rounded-full mt-5 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-accent-blue to-rose-500 transition-all duration-500 ease-out"
              style={{ width: `${utilizationRate}%` }}
            ></div>
          </div>
        </div>
      </div>
      
      <div className="mt-auto pt-6">
         <div className="flex items-center gap-2 text-xs font-mono font-semibold text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100">
            <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse"></div>
            <span>System operational</span>
         </div>
      </div>
    </div>
  );
}

export default Sidebar;
