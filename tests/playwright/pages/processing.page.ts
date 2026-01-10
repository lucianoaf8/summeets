import { Page, Locator, expect } from '@playwright/test';

export class ProcessingPage {
  readonly page: Page;
  readonly currentJobCard: Locator;
  readonly noActiveJob: Locator;
  readonly currentJobTitle: Locator;
  readonly currentJobProgress: Locator;
  readonly currentJobStartTime: Locator;
  readonly currentJobType: Locator;
  readonly jobLogs: Locator;
  readonly cancelJobBtn: Locator;
  readonly progressBar: Locator;
  readonly progressFill: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.currentJobCard = page.locator('#currentJobCard');
    this.noActiveJob = page.locator('#noActiveJob');
    this.currentJobTitle = page.locator('#currentJobTitle');
    this.currentJobProgress = page.locator('#currentJobProgress');
    this.currentJobStartTime = page.locator('#currentJobStartTime');
    this.currentJobType = page.locator('#currentJobType');
    this.jobLogs = page.locator('#jobLogs');
    this.cancelJobBtn = page.locator('#cancelJobBtn');
    this.progressBar = page.locator('.progress-bar');
    this.progressFill = page.locator('.progress-fill');
  }
  
  async waitForJobStart(): Promise<void> {
    console.log('Waiting for job to start...');
    
    // Wait for job card to become visible
    await expect(this.currentJobCard).toBeVisible({ timeout: 10000 });
    await expect(this.noActiveJob).toBeHidden();
    
    // Wait for job title to be populated
    await expect(this.currentJobTitle).toContainText('video_for_testing.mp4');
    
    console.log('Job started successfully');
  }
  
  async monitorJobProgress(): Promise<{ success: boolean; logs: string[]; finalProgress: number }> {
    console.log('Monitoring job progress...');
    
    const logs: string[] = [];
    let finalProgress = 0;
    let success = false;
    
    // Wait for job to start processing
    await this.waitForJobStart();
    
    // Monitor logs for progress and completion
    try {
      await this.page.waitForFunction(() => {
        const logsElement = document.querySelector('#jobLogs');
        if (!logsElement) {
          console.log('No logs element found');
          return false;
        }
        
        const logEntries = logsElement.querySelectorAll('.log-entry');
        if (logEntries.length === 0) {
          console.log('No log entries found');
          return false;
        }
        
        const lastLog = logEntries[logEntries.length - 1];
        const logText = lastLog?.textContent || '';
        
        console.log('Latest log entry:', logText);
        
        return logText.includes('Processing completed successfully!') ||
               logText.includes('Error:') ||
               logText.includes('Failed:') ||
               logText.includes('Job cancelled') ||
               logText.includes('cancelled by user');
      }, { timeout: 300000 }); // 5 minute timeout
      
    } catch (error) {
      console.error('Timeout waiting for job completion:', error);
      // Continue to extract logs even if we timed out
    }
    
    // Extract all logs
    try {
      const logElements = await this.jobLogs.locator('.log-entry').all();
      for (const logElement of logElements) {
        const logText = await logElement.textContent();
        if (logText) {
          logs.push(logText);
        }
      }
    } catch (error) {
      console.error('Error extracting logs:', error);
    }
    
    // Get final progress
    try {
      const progressText = await this.currentJobProgress.textContent();
      const progressMatch = progressText?.match(/(\d+)%/);
      if (progressMatch) {
        finalProgress = parseInt(progressMatch[1]);
      }
    } catch (error) {
      console.warn('Could not extract progress:', error);
    }
    
    // Determine success
    const lastLog = logs[logs.length - 1] || '';
    success = lastLog.includes('Processing completed successfully!');
    
    console.log('Job monitoring completed:');
    console.log('- Success:', success);
    console.log('- Final progress:', finalProgress);
    console.log('- Log entries:', logs.length);
    console.log('- Last log:', lastLog);
    
    return { success, logs, finalProgress };
  }
  
  async cancelJob(): Promise<void> {
    console.log('Cancelling job...');
    
    await this.cancelJobBtn.click();
    
    // Wait for cancellation confirmation in logs
    await this.page.waitForFunction(() => {
      const logsElement = document.querySelector('#jobLogs');
      if (!logsElement) return false;
      
      const logText = logsElement.textContent || '';
      return logText.includes('Job cancelled') || logText.includes('cancelled by user');
    }, { timeout: 30000 });
    
    console.log('Job cancelled successfully');
  }
  
  async verifyJobCompletion(): Promise<void> {
    console.log('Verifying job completion...');
    
    // Verify completion message in logs
    await expect(this.jobLogs).toContainText('Processing completed successfully!');
    
    // Verify progress shows completion
    const progressText = await this.currentJobProgress.textContent();
    expect(progressText).toContain('100%');
    
    console.log('Job completion verified');
  }
  
  async getProgressPercentage(): Promise<number> {
    try {
      const progressText = await this.currentJobProgress.textContent();
      const match = progressText?.match(/(\d+)%/);
      return match ? parseInt(match[1]) : 0;
    } catch (error) {
      console.warn('Could not get progress percentage:', error);
      return 0;
    }
  }
  
  async getJobLogs(): Promise<string[]> {
    const logs: string[] = [];
    
    try {
      const logElements = await this.jobLogs.locator('.log-entry').all();
      
      for (const element of logElements) {
        const text = await element.textContent();
        if (text) {
          logs.push(text);
        }
      }
    } catch (error) {
      console.error('Error getting job logs:', error);
    }
    
    return logs;
  }
  
  async waitForLogEntry(expectedText: string, timeoutMs: number = 30000): Promise<void> {
    console.log('Waiting for log entry containing:', expectedText);
    
    await this.page.waitForFunction((text) => {
      const logsElement = document.querySelector('#jobLogs');
      if (!logsElement) return false;
      
      const logText = logsElement.textContent || '';
      return logText.includes(text);
    }, expectedText, { timeout: timeoutMs });
    
    console.log('Log entry found');
  }
}