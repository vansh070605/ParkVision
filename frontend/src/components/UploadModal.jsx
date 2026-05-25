import React, { useState } from 'react';

function UploadModal({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [capacity, setCapacity] = useState(10);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a file to upload.');
      return;
    }
    
    setIsUploading(true);
    setError('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error('Upload failed');
      }
      
      const data = await response.json();
      onUploadSuccess(data.filename, capacity);
      
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-industrial-900/90 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-industrial-800 border border-industrial-700 p-8 rounded-xl max-w-md w-full shadow-2xl relative overflow-hidden">
        {/* Aesthetic touches */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-accent-blue to-accent-green"></div>
        
        <h2 className="text-2xl font-bold text-white mb-2">Initialize System</h2>
        <p className="text-gray-400 text-sm mb-6">Upload a parking lot feed (image/video) and set capacity to begin YOLOv8 analysis.</p>
        
        {error && <div className="bg-accent-red/10 border border-accent-red text-accent-red text-sm p-3 rounded mb-4">{error}</div>}
        
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Media Source</label>
            <input 
              type="file" 
              accept="video/*,image/*" 
              onChange={handleFileChange}
              className="block w-full text-sm text-gray-400
                file:mr-4 file:py-2 file:px-4
                file:rounded-md file:border-0
                file:text-sm file:font-semibold
                file:bg-industrial-700 file:text-white
                hover:file:bg-industrial-600
                cursor-pointer"
            />
          </div>
          
          <div>
            <label className="block text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">Total Capacity</label>
            <input 
              type="number" 
              min="1"
              value={capacity}
              onChange={(e) => setCapacity(parseInt(e.target.value) || 1)}
              className="w-full bg-industrial-900 border border-industrial-700 text-white rounded p-3 text-lg focus:outline-none focus:border-accent-blue transition-colors"
            />
          </div>
          
          <button 
            type="submit" 
            disabled={isUploading}
            className={`mt-4 w-full py-3 rounded font-bold tracking-wider transition-colors flex items-center justify-center gap-2
              ${isUploading ? 'bg-industrial-700 text-gray-500 cursor-not-allowed' : 'bg-accent-blue hover:bg-blue-400 text-white'}`}
          >
            {isUploading ? (
              <>
                <div className="w-4 h-4 border-2 border-gray-500 border-t-white rounded-full animate-spin"></div>
                PROCESSING...
              </>
            ) : 'INITIALIZE FEED'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default UploadModal;
