const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs').promises;
const Store = require('electron-store');

const store = new Store();
let mainWindow;
let pythonProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    show: true  // Show window immediately
  });

  // Load the HTML app
  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // Open dev tools only if explicitly requested
  if (process.argv.includes('--devtools')) {
    mainWindow.webContents.openDevTools();
  }

  // Handle window closed
  mainWindow.on('closed', () => {
    if (pythonProcess) {
      pythonProcess.kill();
    }
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Security: Prevent new window creation
app.on('web-contents-created', (event, contents) => {
  contents.on('new-window', (event, navigationUrl) => {
    event.preventDefault();
    shell.openExternal(navigationUrl);
  });
});

// ================================
// IPC Handlers for Python Integration
// ================================

// Configuration Management
ipcMain.handle('get-config', () => {
  return store.get('config', {
    llmProvider: 'openai',
    llmModel: 'gpt-4o-mini',
    openaiApiKey: '',
    anthropicApiKey: '',
    replicateApiToken: '',
    maxTokens: 3000,
    chunkSeconds: 1800,
    codPasses: 2
  });
});

ipcMain.handle('save-config', (event, config) => {
  store.set('config', config);
  return true;
});

// File Operations
ipcMain.handle('select-audio-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { 
        name: 'Audio Files', 
        extensions: ['m4a', 'flac', 'wav', 'mka', 'ogg', 'mp3', 'webm'] 
      }
    ],
    title: 'Select Audio File to Process'
  });
  
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('select-media-file', async (event, fileType) => {
  let filters, title;
  
  switch (fileType) {
    case 'video':
      filters = [
        { name: 'Video Files', extensions: ['mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm', 'm4v'] }
      ];
      title = 'Select Video File';
      break;
    case 'audio':
      filters = [
        { name: 'Audio Files', extensions: ['m4a', 'flac', 'wav', 'mka', 'ogg', 'mp3', 'webm'] }
      ];
      title = 'Select Audio File';
      break;
    case 'transcript':
      filters = [
        { name: 'Transcript Files', extensions: ['json', 'txt'] }
      ];
      title = 'Select Transcript File';
      break;
    default:
      // Fallback to all media files
      filters = [
        { 
          name: 'Media Files', 
          extensions: ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4a', 'flac', 'wav', 'mka', 'ogg', 'mp3', 'json', 'txt'] 
        }
      ];
      title = 'Select Media File';
  }
  
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters,
    title
  });
  
  return result.canceled ? null : result.filePaths[0];
});

ipcMain.handle('select-transcript-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'JSON Files', extensions: ['json'] }
    ],
    title: 'Select Transcript File to Summarize'
  });
  
  return result.canceled ? null : result.filePaths[0];
});

// Job Management
ipcMain.handle('start-job', async (event, { filePath, jobType, config }) => {
  const jobId = Date.now().toString();
  
  // Validate inputs
  if (!filePath) {
    throw new Error('File path is required');
  }
  
  if (!['process', 'transcribe', 'summarize', 'extract', 'normalize'].includes(jobType)) {
    throw new Error(`Invalid job type: ${jobType}`);
  }

  // Build Python command
  const pythonCmd = findPythonCommand();
  let command = [pythonCmd, '-m', 'summeets'];
  
  switch (jobType) {
    case 'process':
      command.push('process', filePath);
      break;
    case 'transcribe':
      command.push('transcribe', filePath);
      break;
    case 'summarize':
      command.push('summarize', filePath);
      break;
    case 'extract':
      // Extract audio from video
      const audioPath = filePath.replace(/\.[^/.]+$/, '_audio.m4a');
      command.push('extract', filePath, audioPath, '--codec', 'aac');
      break;
    case 'normalize':
      // Normalize audio volume
      const normalizedPath = filePath.replace(/\.[^/.]+$/, '_normalized.m4a');
      command.push('normalize', filePath, normalizedPath);
      break;
  }

  // Add provider and model flags if specified
  if (config.llmProvider && jobType !== 'transcribe') {
    command.push('--provider', config.llmProvider);
  }
  if (config.llmModel && jobType !== 'transcribe') {
    command.push('--model', config.llmModel);
  }

  // Set up environment variables
  const env = { ...process.env };
  if (config.openaiApiKey) env.OPENAI_API_KEY = config.openaiApiKey;
  if (config.anthropicApiKey) env.ANTHROPIC_API_KEY = config.anthropicApiKey;
  if (config.replicateApiToken) env.REPLICATE_API_TOKEN = config.replicateApiToken;
  if (config.maxTokens) env.SUMMARY_MAX_OUTPUT_TOKENS = config.maxTokens.toString();
  if (config.chunkSeconds) env.SUMMARY_CHUNK_SECONDS = config.chunkSeconds.toString();

  try {
    // Kill any existing process
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }

    pythonProcess = spawn(command[0], command.slice(1), {
      env,
      cwd: process.cwd(),
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // Stream stdout for progress updates
    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      mainWindow.webContents.send('job-output', { 
        jobId, 
        output: output.trim(), 
        type: 'stdout' 
      });
    });

    // Stream stderr for errors and additional info
    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString();
      mainWindow.webContents.send('job-output', { 
        jobId, 
        output: output.trim(), 
        type: 'stderr' 
      });
    });

    // Handle process completion
    pythonProcess.on('close', (code, signal) => {
      mainWindow.webContents.send('job-complete', { 
        jobId, 
        exitCode: code,
        signal 
      });
      pythonProcess = null;
    });

    // Handle process errors
    pythonProcess.on('error', (error) => {
      mainWindow.webContents.send('job-error', { 
        jobId, 
        error: error.message 
      });
      pythonProcess = null;
    });

    return { jobId, status: 'started' };

  } catch (error) {
    throw new Error(`Failed to start job: ${error.message}`);
  }
});

// Workflow Job Management
ipcMain.handle('start-workflow-job', async (event, { inputFile, fileType, workflow, llmConfig }) => {
  const jobId = Date.now().toString();
  
  // Validate inputs
  if (!inputFile) {
    throw new Error('Input file is required');
  }
  
  if (!['video', 'audio', 'transcript'].includes(fileType)) {
    throw new Error(`Invalid file type: ${fileType}`);
  }

  // Build Python command for workflow execution
  const pythonCmd = findPythonCommand();
  let command = [pythonCmd, '-c', `
import sys
import os
from pathlib import Path
sys.path.insert(0, os.getcwd())

from summeets.core.workflow import WorkflowConfig, execute_workflow

# Create workflow configuration
config = WorkflowConfig(
    input_file=Path("${inputFile.replace(/\\/g, '\\\\')}"),
    output_dir=Path("data/output") / "${new Date().toISOString().split('T')[0]}",
    extract_audio=${workflow.extractAudio},
    process_audio=${workflow.processAudio},
    transcribe=${workflow.transcribe},
    summarize=${workflow.summarize},
    audio_format="${workflow.audioFormat}",
    audio_quality="${workflow.audioQuality}",
    increase_volume=${workflow.increaseVolume},
    normalize_audio=${workflow.normalizeAudio},
    output_formats=${JSON.stringify(workflow.outputFormats)},
    transcribe_model="thomasmol/whisper-diarization",
    language="${workflow.transcribeLanguage}",
    summary_template="${workflow.summaryTemplate}",
    provider="${llmConfig.llmProvider}",
    model="${llmConfig.llmModel}"
)

def progress_callback(step, total, step_name, status):
    progress = int((step / total) * 100)
    print(f"PROGRESS: {progress}% - {step_name}: {status}")

# Execute workflow
try:
    print(f"Starting workflow for {fileType} file: ${inputFile}")
    results = execute_workflow(config, progress_callback)
    print("WORKFLOW_COMPLETE: Workflow completed successfully")
    print(f"RESULTS: {results}")
except Exception as e:
    print(f"WORKFLOW_ERROR: {str(e)}")
    sys.exit(1)
`];

  // Set up environment variables
  const env = { ...process.env };
  if (llmConfig.openaiApiKey) env.OPENAI_API_KEY = llmConfig.openaiApiKey;
  if (llmConfig.anthropicApiKey) env.ANTHROPIC_API_KEY = llmConfig.anthropicApiKey;
  if (llmConfig.replicateApiToken) env.REPLICATE_API_TOKEN = llmConfig.replicateApiToken;
  if (llmConfig.maxTokens) env.SUMMARY_MAX_OUTPUT_TOKENS = llmConfig.maxTokens.toString();
  if (llmConfig.chunkSeconds) env.SUMMARY_CHUNK_SECONDS = llmConfig.chunkSeconds.toString();

  try {
    // Kill any existing process
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }

    pythonProcess = spawn(command[0], command.slice(1), {
      env,
      cwd: process.cwd(),
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // Stream stdout for progress updates
    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      mainWindow.webContents.send('job-output', { 
        jobId, 
        output: output.trim(), 
        type: 'stdout' 
      });
    });

    // Stream stderr for errors and additional info
    pythonProcess.stderr.on('data', (data) => {
      const output = data.toString();
      mainWindow.webContents.send('job-output', { 
        jobId, 
        output: output.trim(), 
        type: 'stderr' 
      });
    });

    // Handle process completion
    pythonProcess.on('close', (code, signal) => {
      mainWindow.webContents.send('job-complete', { 
        jobId, 
        exitCode: code,
        signal 
      });
      pythonProcess = null;
    });

    // Handle process errors
    pythonProcess.on('error', (error) => {
      mainWindow.webContents.send('job-error', { 
        jobId, 
        error: error.message 
      });
      pythonProcess = null;
    });

    return { jobId, status: 'started' };

  } catch (error) {
    throw new Error(`Failed to start workflow job: ${error.message}`);
  }
});

ipcMain.handle('cancel-job', async (event, jobId) => {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM');
    
    // Force kill after 5 seconds if it doesn't respond
    setTimeout(() => {
      if (pythonProcess) {
        pythonProcess.kill('SIGKILL');
        pythonProcess = null;
      }
    }, 5000);
    
    return true;
  }
  return false;
});

// File System Operations
ipcMain.handle('get-output-files', async (event, baseName) => {
  const outputDir = path.join(process.cwd(), 'out');
  
  try {
    await fs.access(outputDir);
    const files = await fs.readdir(outputDir);
    
    // Filter files that start with the base name (without extension)
    const baseNameWithoutExt = path.parse(baseName).name;
    const relatedFiles = files.filter(file => 
      file.startsWith(baseNameWithoutExt) || 
      file.startsWith(baseName)
    );
    
    const fileDetails = await Promise.all(
      relatedFiles.map(async (file) => {
        const filePath = path.join(outputDir, file);
        try {
          const stats = await fs.stat(filePath);
          return {
            name: file,
            path: filePath,
            size: stats.size,
            modified: stats.mtime
          };
        } catch (error) {
          return {
            name: file,
            path: filePath,
            size: 0,
            modified: null
          };
        }
      })
    );
    
    return fileDetails;
  } catch (error) {
    return [];
  }
});

ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const content = await fs.readFile(filePath, 'utf8');
    return content;
  } catch (error) {
    throw new Error(`Failed to read file: ${error.message}`);
  }
});

ipcMain.handle('open-output-folder', async (event, filePath) => {
  try {
    const outputDir = filePath ? path.dirname(filePath) : path.join(process.cwd(), 'out');
    await shell.openPath(outputDir);
    return true;
  } catch (error) {
    throw new Error(`Failed to open folder: ${error.message}`);
  }
});

ipcMain.handle('export-file', async (event, filePath) => {
  try {
    const result = await dialog.showSaveDialog(mainWindow, {
      defaultPath: path.basename(filePath),
      filters: [
        { name: 'All Files', extensions: ['*'] }
      ]
    });
    
    if (!result.canceled) {
      await fs.copyFile(filePath, result.filePath);
      return result.filePath;
    }
    
    return null;
  } catch (error) {
    throw new Error(`Failed to export file: ${error.message}`);
  }
});

// System Information
ipcMain.handle('get-system-info', () => {
  return {
    platform: process.platform,
    arch: process.arch,
    nodeVersion: process.version,
    electronVersion: process.versions.electron,
    pythonCommand: findPythonCommand()
  };
});

// Helper Functions
function findPythonCommand() {
  // Try different Python commands based on platform
  const pythonCommands = process.platform === 'win32' 
    ? ['python', 'python3', 'py'] 
    : ['python3', 'python'];
  
  // For now, return the first one. In production, you'd want to validate
  // that the command exists and has the summeets package installed
  return pythonCommands[0];
}