import React from 'react';

function Sidebar({ metrics }) {
  const { total_capacity, occupied, available } = metrics;
  
  const utilizationRate = total_capacity > 0 
    ? ((occupied / total_capacity) * 100).toFixed(1) 
    : 0;

  return (
    <div className="flex flex-col h-full">
      <h2 className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-6 border-b border-industrial-700 pb-2">
        Telemetry & Analytics
      </h2>
      
      <div className="flex flex-col gap-4">
        {/* Metric Card: Available */}
        <div className="bg-industrial-900/50 p-5 rounded-lg border border-industrial-700 hover:border-accent-green/50 transition-colors duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-accent-green/10 rounded-bl-full -mr-8 -mt-8 group-hover:bg-accent-green/20 transition-colors"></div>
          <p className="text-gray-400 text-sm font-medium mb-1">Available Spots</p>
          <p className="text-4xl font-mono font-bold text-accent-green">{available}</p>
        </div>

        {/* Metric Card: Occupied */}
        <div className="bg-industrial-900/50 p-5 rounded-lg border border-industrial-700 hover:border-accent-red/50 transition-colors duration-300 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-16 h-16 bg-accent-red/10 rounded-bl-full -mr-8 -mt-8 group-hover:bg-accent-red/20 transition-colors"></div>
          <p className="text-gray-400 text-sm font-medium mb-1">Occupied Spots</p>
          <p className="text-4xl font-mono font-bold text-accent-red">{occupied}</p>
        </div>

        {/* Metric Card: Total */}
        <div className="bg-industrial-900/50 p-5 rounded-lg border border-industrial-700 hover:border-industrial-600 transition-colors duration-300">
          <div className="flex justify-between items-end">
            <div>
              <p className="text-gray-400 text-sm font-medium mb-1">Total Capacity</p>
              <p className="text-3xl font-mono font-bold text-white">{total_capacity}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500 mb-1">Utilization</p>
              <p className="text-lg font-mono text-accent-blue">{utilizationRate}%</p>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-industrial-800 h-2 rounded-full mt-4 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-accent-blue to-accent-red transition-all duration-500 ease-out"
              style={{ width: `${utilizationRate}%` }}
            ></div>
          </div>
        </div>
      </div>
      
      <div className="mt-auto">
         <div className="flex items-center gap-2 text-xs font-mono text-gray-500 bg-industrial-900/30 p-3 rounded border border-industrial-800">
            <div className="w-1.5 h-1.5 rounded-full bg-accent-green animate-pulse"></div>
            <span>System optimal</span>
         </div>
      </div>
    </div>
  );
}

export default Sidebar;
