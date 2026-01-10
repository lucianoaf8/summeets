import { test as base, ElectronApplication, Page, BrowserContext } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import fs from 'fs/promises';

export interface TestFixtures {
  electronApp: ElectronApplication;
  mainWindow: Page;
  testDataPath: string;
  processMonitor: ProcessMonitor;
}

class ProcessMonitor {
  private processes: Map<string, ChildProcess> = new Map();
  
  async startElectronApp(): Promise<ElectronApplication> {
    const { _electron } = await import('playwright');
    
    // Path to the main Electron file
    const electronMainPath = path.join(__dirname, '../../../electron/main.js');
    
    console.log('Launching Electron app from:', electronMainPath);
    
    return await _electron.launch({
      args: [electronMainPath, '--no-sandbox', '--disable-dev-shm-usage'],
      env: {
        ...process.env,
        NODE_ENV: 'test',
        ELECTRON_DISABLE_SECURITY_WARNINGS: 'true',
        // Provide test API keys if available
        OPENAI_API_KEY: process.env.OPENAI_API_KEY || 'test-key',
        REPLICATE_API_TOKEN: process.env.REPLICATE_API_TOKEN || 'test-token',
        ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY || 'test-key'
      },
      timeout: 30000
    });
  }
  
  async waitForProcessCompletion(
    page: Page, 
    timeoutMs: number = 300000
  ): Promise<{ success: boolean; logs: string[] }> {
    const logs: string[] = [];
    let success = false;
    
    console.log('Waiting for process completion...');
    
    try {
      // Monitor job logs for completion signals
      await page.waitForFunction(() => {
        const logsElement = document.querySelector('#jobLogs');
        if (!logsElement) return false;
        
        const logEntries = logsElement.querySelectorAll('.log-entry');
        if (logEntries.length === 0) return false;
        
        const lastLog = logEntries[logEntries.length - 1];
        const logText = lastLog?.textContent || '';
        
        console.log('Latest log entry:', logText);
        
        return logText.includes('Processing completed successfully!') || 
               logText.includes('Error:') ||
               logText.includes('Failed:') ||
               logText.includes('Job cancelled') ||
               logText.includes('cancelled by user');
      }, { timeout: timeoutMs });
      
      // Extract all logs
      const logElements = await page.locator('#jobLogs .log-entry').all();
      for (const logElement of logElements) {
        const text = await logElement.textContent();
        if (text) logs.push(text);
      }
      
      // Determine success/failure
      const lastLog = logs[logs.length - 1] || '';
      success = lastLog.includes('Processing completed successfully!');
      
      console.log('Process completed. Success:', success);
      console.log('Final log entry:', lastLog);
      
    } catch (error) {
      console.error('Error waiting for process completion:', error);
      
      // Try to extract logs even if we timed out
      try {
        const logElements = await page.locator('#jobLogs .log-entry').all();
        for (const logElement of logElements) {
          const text = await logElement.textContent();
          if (text) logs.push(text);
        }
      } catch (e) {
        console.error('Could not extract logs:', e);
      }
    }
    
    return { success, logs };
  }
  
  async cleanup(): Promise<void> {
    console.log('Cleaning up processes...');
    for (const [id, process] of this.processes) {
      if (!process.killed) {
        console.log(`Killing process ${id}`);
        process.kill('SIGTERM');
        
        // Force kill after 5 seconds
        setTimeout(() => {
          if (!process.killed) {
            process.kill('SIGKILL');
          }
        }, 5000);
      }
    }
    this.processes.clear();
  }
}

export const test = base.extend<TestFixtures>({
  electronApp: async ({}, use) => {
    const monitor = new ProcessMonitor();
    const app = await monitor.startElectronApp();
    
    // Wait for app to be ready
    await app.context().waitForEvent('page');
    
    await use(app);
    
    console.log('Closing Electron app...');
    await app.close();
    await monitor.cleanup();
  },
  
  mainWindow: async ({ electronApp }, use) => {
    console.log('Getting main window...');
    
    // Get the first window (main window)
    const window = await electronApp.firstWindow();
    
    // Wait for the window to load
    await window.waitForLoadState('domcontentloaded');
    
    // Wait for main elements to be visible
    await window.waitForSelector('.app-container', { timeout: 30000 });
    await window.waitForSelector('#dashboard-tab', { timeout: 30000 });
    
    console.log('Main window ready');
    
    await use(window);
  },
  
  testDataPath: async ({}, use) => {
    // Use the actual test video file
    const videoPath = path.join(__dirname, '../../../data/video/video_for_testing.mp4');
    
    // Verify the test file exists
    try {
      await fs.access(videoPath);
      console.log('Test video file found:', videoPath);
    } catch (error) {
      console.warn('Test video file not found, using placeholder path');
    }
    
    await use(videoPath);
  },
  
  processMonitor: async ({}, use) => {
    const monitor = new ProcessMonitor();
    await use(monitor);
    await monitor.cleanup();
  }
});

export { expect } from '@playwright/test';