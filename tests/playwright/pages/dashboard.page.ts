import { Page, Locator, expect } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly selectVideoBtn: Locator;
  readonly selectAudioBtn: Locator;
  readonly selectTranscriptBtn: Locator;
  readonly selectedFileDisplay: Locator;
  readonly selectedFileName: Locator;
  readonly selectedFileType: Locator;
  readonly selectedFileIcon: Locator;
  readonly changeFileBtn: Locator;
  readonly startProcessingBtn: Locator;
  readonly workflowSteps: {
    extractAudio: Locator;
    processAudio: Locator;
    transcribe: Locator;
    summarize: Locator;
  };
  readonly configOptions: {
    audioFormat: Locator;
    audioQuality: Locator;
    increaseVolume: Locator;
    normalizeAudio: Locator;
    transcribeLanguage: Locator;
    summaryTemplate: Locator;
  };
  
  constructor(page: Page) {
    this.page = page;
    this.selectVideoBtn = page.locator('#selectVideoBtn');
    this.selectAudioBtn = page.locator('#selectAudioBtn');
    this.selectTranscriptBtn = page.locator('#selectTranscriptBtn');
    this.selectedFileDisplay = page.locator('#selectedFileDisplay');
    this.selectedFileName = page.locator('#selectedFileName');
    this.selectedFileType = page.locator('#selectedFileType');
    this.selectedFileIcon = page.locator('#selectedFileIcon');
    this.changeFileBtn = page.locator('#changeFileBtn');
    this.startProcessingBtn = page.locator('#startProcessingBtn');
    
    this.workflowSteps = {
      extractAudio: page.locator('#enableExtractAudio'),
      processAudio: page.locator('#enableProcessAudio'),
      transcribe: page.locator('#enableTranscribe'),
      summarize: page.locator('#enableSummarize')
    };
    
    this.configOptions = {
      audioFormat: page.locator('#audioFormat'),
      audioQuality: page.locator('#audioQuality'),
      increaseVolume: page.locator('#increaseVolume'),
      normalizeAudio: page.locator('#normalizeAudio'),
      transcribeLanguage: page.locator('#transcribeLanguage'),
      summaryTemplate: page.locator('#summaryTemplate')
    };
  }
  
  async selectVideoFile(filePath: string): Promise<void> {
    console.log('Selecting video file:', filePath);
    
    // Mock the Electron file dialog to return our test file
    await this.page.evaluate((path) => {
      // Override the selectMediaFile function to return our test file
      if (window.electronAPI) {
        window.electronAPI.selectMediaFile = async (fileType: string) => {
          console.log('Mock selectMediaFile called with:', fileType);
          return path;
        };
      }
    }, filePath);
    
    // Click the video selection button
    await this.selectVideoBtn.click();
    
    // Wait for file to be selected and UI to update
    await expect(this.selectedFileDisplay).toBeVisible({ timeout: 10000 });
    await expect(this.selectedFileName).toContainText('video_for_testing.mp4');
    await expect(this.selectVideoBtn).toHaveClass(/active/);
    
    console.log('Video file selected successfully');
  }
  
  async selectAudioFile(filePath: string): Promise<void> {
    console.log('Selecting audio file:', filePath);
    
    await this.page.evaluate((path) => {
      if (window.electronAPI) {
        window.electronAPI.selectMediaFile = async (fileType: string) => {
          return path;
        };
      }
    }, filePath);
    
    await this.selectAudioBtn.click();
    
    await expect(this.selectedFileDisplay).toBeVisible({ timeout: 10000 });
    await expect(this.selectAudioBtn).toHaveClass(/active/);
  }
  
  async selectTranscriptFile(filePath: string): Promise<void> {
    console.log('Selecting transcript file:', filePath);
    
    await this.page.evaluate((path) => {
      if (window.electronAPI) {
        window.electronAPI.selectMediaFile = async (fileType: string) => {
          return path;
        };
      }
    }, filePath);
    
    await this.selectTranscriptBtn.click();
    
    await expect(this.selectedFileDisplay).toBeVisible({ timeout: 10000 });
    await expect(this.selectTranscriptBtn).toHaveClass(/active/);
  }
  
  async configureWorkflow(options: {
    extractAudio?: boolean;
    processAudio?: boolean;
    transcribe?: boolean;
    summarize?: boolean;
    audioFormat?: string;
    audioQuality?: string;
    increaseVolume?: boolean;
    normalizeAudio?: boolean;
    transcribeLanguage?: string;
    summaryTemplate?: string;
  }): Promise<void> {
    console.log('Configuring workflow with options:', options);
    
    // Configure workflow steps
    if (options.extractAudio !== undefined) {
      await this.setCheckbox(this.workflowSteps.extractAudio, options.extractAudio);
    }
    if (options.processAudio !== undefined) {
      await this.setCheckbox(this.workflowSteps.processAudio, options.processAudio);
    }
    if (options.transcribe !== undefined) {
      await this.setCheckbox(this.workflowSteps.transcribe, options.transcribe);
    }
    if (options.summarize !== undefined) {
      await this.setCheckbox(this.workflowSteps.summarize, options.summarize);
    }
    
    // Configure options
    if (options.audioFormat) {
      await this.configOptions.audioFormat.selectOption(options.audioFormat);
    }
    if (options.audioQuality) {
      await this.configOptions.audioQuality.selectOption(options.audioQuality);
    }
    if (options.increaseVolume !== undefined) {
      await this.setCheckbox(this.configOptions.increaseVolume, options.increaseVolume);
    }
    if (options.normalizeAudio !== undefined) {
      await this.setCheckbox(this.configOptions.normalizeAudio, options.normalizeAudio);
    }
    if (options.transcribeLanguage) {
      await this.configOptions.transcribeLanguage.selectOption(options.transcribeLanguage);
    }
    if (options.summaryTemplate) {
      await this.configOptions.summaryTemplate.selectOption(options.summaryTemplate);
    }
    
    console.log('Workflow configuration completed');
  }
  
  async startProcessing(): Promise<void> {
    console.log('Starting processing...');
    
    // Verify button is enabled
    await expect(this.startProcessingBtn).toBeEnabled();
    
    // Click start processing
    await this.startProcessingBtn.click();
    
    // Wait for processing to start (button should become disabled)
    await expect(this.startProcessingBtn).toBeDisabled();
    
    // Wait for automatic navigation to processing tab
    await this.page.waitForSelector('.nav-item[data-tab="processing"].active', { timeout: 10000 });
    
    console.log('Processing started, navigated to processing tab');
  }
  
  private async setCheckbox(checkbox: Locator, checked: boolean): Promise<void> {
    const isChecked = await checkbox.isChecked();
    if (isChecked !== checked) {
      await checkbox.click();
    }
  }
  
  async verifyWorkflowConfigurationForFileType(fileType: 'video' | 'audio' | 'transcript'): Promise<void> {
    console.log('Verifying workflow configuration for file type:', fileType);
    
    switch (fileType) {
      case 'video':
        await expect(this.workflowSteps.extractAudio).toBeEnabled();
        await expect(this.workflowSteps.processAudio).toBeEnabled();
        await expect(this.workflowSteps.transcribe).toBeEnabled();
        await expect(this.workflowSteps.summarize).toBeEnabled();
        break;
      case 'audio':
        await expect(this.workflowSteps.extractAudio).toBeDisabled();
        await expect(this.workflowSteps.processAudio).toBeEnabled();
        await expect(this.workflowSteps.transcribe).toBeEnabled();
        await expect(this.workflowSteps.summarize).toBeEnabled();
        break;
      case 'transcript':
        await expect(this.workflowSteps.extractAudio).toBeDisabled();
        await expect(this.workflowSteps.processAudio).toBeDisabled();
        await expect(this.workflowSteps.transcribe).toBeDisabled();
        await expect(this.workflowSteps.summarize).toBeEnabled();
        break;
    }
    
    console.log('Workflow configuration verified');
  }
  
  async clearSelectedFile(): Promise<void> {
    await this.changeFileBtn.click();
    await expect(this.selectedFileDisplay).toBeHidden();
    await expect(this.startProcessingBtn).toBeDisabled();
  }
}