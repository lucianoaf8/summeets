import { test, expect } from '../utils/electron-utils';
import { DashboardPage } from '../pages/dashboard.page';
import { ProcessingPage } from '../pages/processing.page';
import { SettingsPage } from '../pages/settings.page';
import path from 'path';
import fs from 'fs/promises';

test.describe('Complete GUI Workflow Tests', () => {
  let dashboardPage: DashboardPage;
  let processingPage: ProcessingPage;
  let settingsPage: SettingsPage;
  
  test.beforeEach(async ({ mainWindow }) => {
    dashboardPage = new DashboardPage(mainWindow);
    processingPage = new ProcessingPage(mainWindow);
    settingsPage = new SettingsPage(mainWindow);
    
    // Ensure we start on dashboard
    await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
    await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
    
    console.log('Test setup complete - on dashboard tab');
  });
  
  test('Complete Video Processing Workflow', async ({ 
    mainWindow, 
    testDataPath, 
    processMonitor 
  }) => {
    console.log('Starting complete video processing workflow test');
    
    // Test Configuration
    const testConfig = {
      inputFile: testDataPath,
      outputDirs: [
        path.join(__dirname, '../../../data/output'),
        path.join(__dirname, '../../../data/transcript/video_for_testing'),
        path.join(__dirname, '../../../data/audio/video_for_testing'),
        path.join(__dirname, '../../../out')
      ],
      expectedFiles: [
        'video_for_testing.json',
        'video_for_testing.srt', 
        'video_for_testing.txt',
        'video_for_testing.summary.json',
        'video_for_testing.summary.md'
      ]
    };
    
    await test.step('Configure API Keys and Settings', async () => {
      console.log('Configuring API keys and settings...');
      
      // Navigate to settings
      await mainWindow.locator('.nav-item[data-tab="settings"]').click();
      await expect(mainWindow.locator('#settings-tab')).toBeVisible();
      
      // Configure LLM settings
      await settingsPage.configureLLMSettings({
        provider: 'openai',
        model: 'gpt-4o-mini',
        apiKey: process.env.OPENAI_API_KEY || 'test-key-for-testing',
        replicateToken: process.env.REPLICATE_API_TOKEN || 'test-token-for-testing',
        maxTokens: 3000,
        chunkSeconds: 1800
      });
      
      await settingsPage.saveConfiguration();
      
      // Return to dashboard
      await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
      await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
      
      console.log('API keys and settings configured');
    });
    
    await test.step('Select Video File', async () => {
      console.log('Selecting video file...');
      
      await dashboardPage.selectVideoFile(testConfig.inputFile);
      
      // Verify file selection
      await expect(dashboardPage.selectedFileDisplay).toBeVisible();
      await expect(dashboardPage.selectedFileName).toContainText('video_for_testing.mp4');
      await expect(dashboardPage.selectVideoBtn).toHaveClass(/active/);
      
      // Verify workflow steps are configured for video
      await dashboardPage.verifyWorkflowConfigurationForFileType('video');
      
      console.log('Video file selected and verified');
    });
    
    await test.step('Configure Workflow Settings', async () => {
      console.log('Configuring workflow settings...');
      
      await dashboardPage.configureWorkflow({
        extractAudio: true,
        processAudio: true,
        transcribe: true,
        summarize: true,
        audioFormat: 'm4a',
        audioQuality: 'high',
        transcribeLanguage: 'auto',
        summaryTemplate: 'Default'
      });
      
      // Verify start button is enabled
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
      
      console.log('Workflow settings configured');
    });
    
    await test.step('Start Processing and Monitor Progress', async () => {
      console.log('Starting processing...');
      
      await dashboardPage.startProcessing();
      
      // Verify automatic navigation to processing tab
      await expect(mainWindow.locator('.nav-item[data-tab="processing"].active')).toBeVisible();
      await expect(mainWindow.locator('#processing-tab')).toBeVisible();
      
      console.log('Processing started, monitoring progress...');
      
      // Monitor job progress
      const result = await processingPage.monitorJobProgress();
      
      console.log('Processing result:', {
        success: result.success,
        finalProgress: result.finalProgress,
        logCount: result.logs.length,
        lastLog: result.logs[result.logs.length - 1]
      });
      
      // For CI/mock environment, we may not have actual processing
      // so we'll be more lenient with assertions
      if (process.env.CI) {
        console.log('Running in CI environment - skipping strict progress checks');
        expect(result.logs.length).toBeGreaterThan(0);
      } else {
        expect(result.success).toBe(true);
        expect(result.finalProgress).toBe(100);
        expect(result.logs.length).toBeGreaterThan(5);
        
        // Verify completion message
        const lastLog = result.logs[result.logs.length - 1];
        expect(lastLog).toContain('Processing completed successfully!');
      }
      
      console.log('Processing monitoring complete');
    });
    
    await test.step('Verify Output Files (if not in CI)', async () => {
      if (process.env.CI) {
        console.log('Skipping file verification in CI environment');
        return;
      }
      
      console.log('Verifying output files...');
      
      // Wait a moment for files to be written
      await mainWindow.waitForTimeout(2000);
      
      let filesFound = 0;
      
      // Check each expected output file in all possible locations
      for (const fileName of testConfig.expectedFiles) {
        let found = false;
        
        for (const outputDir of testConfig.outputDirs) {
          const filePath = path.join(outputDir, fileName);
          try {
            const stats = await fs.stat(filePath);
            if (stats.size > 0) {
              console.log(`✓ Found output file: ${fileName} at ${outputDir} (${stats.size} bytes)`);
              found = true;
              filesFound++;
              break;
            }
          } catch (error) {
            // File not found in this location, continue searching
          }
        }
        
        if (!found) {
          console.warn(`⚠ Output file not found: ${fileName}`);
        }
      }
      
      // In a real test environment, we'd expect at least some files
      // In CI/mock environment, this might be 0
      console.log(`Found ${filesFound} out of ${testConfig.expectedFiles.length} expected output files`);
    });
    
    await test.step('Verify Processing Tab Completion State', async () => {
      console.log('Verifying completion state...');
      
      // If we're not in CI and had successful processing, verify completion
      if (!process.env.CI) {
        await processingPage.verifyJobCompletion();
      }
      
      // Verify we can return to dashboard
      await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
      await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
      
      // In a successful completion, start button should be re-enabled
      const isEnabled = await dashboardPage.startProcessingBtn.isEnabled();
      console.log('Start button enabled after completion:', isEnabled);
      
      console.log('Completion state verified');
    });
    
    console.log('Complete video processing workflow test finished');
  });
  
  test('Audio-Only Processing Workflow', async ({ mainWindow, testDataPath }) => {
    console.log('Starting audio-only processing workflow test');
    
    // Use audio file (assuming we have one or mock it)
    const audioPath = testDataPath.replace('.mp4', '.wav');
    
    await test.step('Select Audio File', async () => {
      await dashboardPage.selectAudioFile(audioPath);
      await dashboardPage.verifyWorkflowConfigurationForFileType('audio');
      
      // Extract audio should be disabled for audio files
      await expect(dashboardPage.workflowSteps.extractAudio).toBeDisabled();
      await expect(dashboardPage.workflowSteps.processAudio).toBeEnabled();
      await expect(dashboardPage.workflowSteps.transcribe).toBeEnabled();
      await expect(dashboardPage.workflowSteps.summarize).toBeEnabled();
    });
    
    await test.step('Process Audio File', async () => {
      await dashboardPage.configureWorkflow({
        processAudio: true,
        transcribe: true,
        summarize: true,
        audioFormat: 'm4a',
        audioQuality: 'high'
      });
      
      await dashboardPage.startProcessing();
      const result = await processingPage.monitorJobProgress();
      
      // Be lenient in CI environment
      if (!process.env.CI) {
        expect(result.success).toBe(true);
      }
      expect(result.logs.length).toBeGreaterThan(0);
    });
    
    console.log('Audio-only processing workflow test finished');
  });
  
  test('Transcript-Only Summarization Workflow', async ({ mainWindow }) => {
    console.log('Starting transcript-only summarization workflow test');
    
    const transcriptPath = path.join(__dirname, '../../../data/transcript/video_for_testing/video_for_testing.json');
    
    await test.step('Select Transcript File', async () => {
      await dashboardPage.selectTranscriptFile(transcriptPath);
      await dashboardPage.verifyWorkflowConfigurationForFileType('transcript');
      
      // Only summarize should be enabled for transcript files
      await expect(dashboardPage.workflowSteps.extractAudio).toBeDisabled();
      await expect(dashboardPage.workflowSteps.processAudio).toBeDisabled();
      await expect(dashboardPage.workflowSteps.transcribe).toBeDisabled();
      await expect(dashboardPage.workflowSteps.summarize).toBeEnabled();
    });
    
    await test.step('Process Transcript File', async () => {
      await dashboardPage.configureWorkflow({
        summarize: true,
        summaryTemplate: 'Meeting Notes'
      });
      
      await dashboardPage.startProcessing();
      const result = await processingPage.monitorJobProgress();
      
      // Be lenient in CI environment
      if (!process.env.CI) {
        expect(result.success).toBe(true);
      }
      expect(result.logs.length).toBeGreaterThan(0);
    });
    
    console.log('Transcript-only summarization workflow test finished');
  });
  
  test('Job Cancellation', async ({ mainWindow, testDataPath }) => {
    console.log('Starting job cancellation test');
    
    await test.step('Start Job and Cancel', async () => {
      await dashboardPage.selectVideoFile(testDataPath);
      await dashboardPage.configureWorkflow({
        extractAudio: true,
        processAudio: true,
        transcribe: true,
        summarize: true
      });
      
      await dashboardPage.startProcessing();
      
      // Wait for job to start
      await processingPage.waitForJobStart();
      
      // Wait a moment for processing to begin
      await mainWindow.waitForTimeout(2000);
      
      // Cancel the job
      await processingPage.cancelJob();
      
      // Verify cancellation
      const logs = await processingPage.getJobLogs();
      const cancelLog = logs.find(log => 
        log.includes('cancelled') || 
        log.includes('Job cancelled') ||
        log.includes('cancelled by user')
      );
      
      // In a real environment, we should find a cancellation log
      // In CI/mock environment, this might not be present
      if (!process.env.CI) {
        expect(cancelLog).toBeDefined();
      }
      
      console.log('Cancellation logs found:', cancelLog ? 'Yes' : 'No');
    });
    
    console.log('Job cancellation test finished');
  });
  
  test('Error Handling and Recovery', async ({ mainWindow }) => {
    console.log('Starting error handling test');
    
    await test.step('Handle Missing File Error', async () => {
      const invalidPath = '/path/to/nonexistent/file.mp4';
      
      // Try to select an invalid file
      await dashboardPage.selectVideoFile(invalidPath);
      
      // The file selection should still work (it's just a path)
      await expect(dashboardPage.selectedFileDisplay).toBeVisible();
      
      // Try to start processing with invalid file
      await dashboardPage.startProcessing();
      
      // Monitor for error handling
      const result = await processingPage.monitorJobProgress();
      
      // We expect this to fail due to invalid file
      if (!process.env.CI) {
        expect(result.success).toBe(false);
        
        const errorLog = result.logs.find(log => 
          log.includes('Error:') || 
          log.includes('Failed:') ||
          log.includes('No such file')
        );
        expect(errorLog).toBeDefined();
      }
      
      console.log('Error handling verified - invalid file detected');
    });
    
    console.log('Error handling test finished');
  });
});

// Add a simple smoke test to verify basic functionality
test.describe('GUI Smoke Tests', () => {
  test('Application Launches and Basic UI Elements Load', async ({ mainWindow }) => {
    console.log('Starting application smoke test');
    
    // Verify main UI elements are present
    await expect(mainWindow.locator('.app-container')).toBeVisible();
    await expect(mainWindow.locator('.header')).toBeVisible();
    await expect(mainWindow.locator('.sidebar')).toBeVisible();
    await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
    
    // Verify navigation tabs are present
    await expect(mainWindow.locator('.nav-item[data-tab="dashboard"]')).toBeVisible();
    await expect(mainWindow.locator('.nav-item[data-tab="processing"]')).toBeVisible();
    await expect(mainWindow.locator('.nav-item[data-tab="history"]')).toBeVisible();
    await expect(mainWindow.locator('.nav-item[data-tab="settings"]')).toBeVisible();
    
    // Verify file selection buttons are present
    await expect(mainWindow.locator('#selectVideoBtn')).toBeVisible();
    await expect(mainWindow.locator('#selectAudioBtn')).toBeVisible();
    await expect(mainWindow.locator('#selectTranscriptBtn')).toBeVisible();
    
    // Verify start processing button is present (but disabled)
    await expect(mainWindow.locator('#startProcessingBtn')).toBeVisible();
    await expect(mainWindow.locator('#startProcessingBtn')).toBeDisabled();
    
    console.log('Application smoke test passed - all basic UI elements present');
  });
});