const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Configuration management
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),
  
  // File operations
  selectAudioFile: () => ipcRenderer.invoke('select-audio-file'),
  selectMediaFile: () => ipcRenderer.invoke('select-media-file'),
  selectTranscriptFile: () => ipcRenderer.invoke('select-transcript-file'),
  getOutputFiles: (baseName) => ipcRenderer.invoke('get-output-files', baseName),
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  openOutputFolder: (filePath) => ipcRenderer.invoke('open-output-folder', filePath),
  exportFile: (filePath) => ipcRenderer.invoke('export-file', filePath),
  
  // Job management
  startJob: (params) => ipcRenderer.invoke('start-job', params),
  cancelJob: (jobId) => ipcRenderer.invoke('cancel-job', jobId),
  
  // System information
  getSystemInfo: () => ipcRenderer.invoke('get-system-info'),
  
  // Event listeners for real-time updates
  onJobOutput: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('job-output', subscription);
    
    // Return unsubscribe function
    return () => ipcRenderer.removeListener('job-output', subscription);
  },
  
  onJobComplete: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('job-complete', subscription);
    
    return () => ipcRenderer.removeListener('job-complete', subscription);
  },
  
  onJobError: (callback) => {
    const subscription = (event, data) => callback(data);
    ipcRenderer.on('job-error', subscription);
    
    return () => ipcRenderer.removeListener('job-error', subscription);
  },
  
  // Cleanup all listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});