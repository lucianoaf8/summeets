import { test, expect } from '../utils/electron-utils';
import { DashboardPage } from '../pages/dashboard.page';
import { SettingsPage } from '../pages/settings.page';

test.describe('GUI Interaction Tests', () => {
  let dashboardPage: DashboardPage;
  let settingsPage: SettingsPage;
  
  test.beforeEach(async ({ mainWindow }) => {
    dashboardPage = new DashboardPage(mainWindow);
    settingsPage = new SettingsPage(mainWindow);
    
    // Ensure we start on dashboard
    await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
    await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
  });
  
  test('File Selection and UI Updates', async ({ mainWindow, testDataPath }) => {
    console.log('Testing file selection and UI updates');
    
    await test.step('Test Initial State', async () => {
      // Initially no buttons should be active
      await expect(dashboardPage.selectVideoBtn).not.toHaveClass(/active/);
      await expect(dashboardPage.selectAudioBtn).not.toHaveClass(/active/);
      await expect(dashboardPage.selectTranscriptBtn).not.toHaveClass(/active/);
      
      // Start button should be disabled
      await expect(dashboardPage.startProcessingBtn).toBeDisabled();
      
      // Selected file display should be hidden
      await expect(dashboardPage.selectedFileDisplay).toBeHidden();
    });
    
    await test.step('Test Video File Selection', async () => {
      await dashboardPage.selectVideoFile(testDataPath);
      
      // Video button should be active
      await expect(dashboardPage.selectVideoBtn).toHaveClass(/active/);
      await expect(dashboardPage.selectAudioBtn).not.toHaveClass(/active/);
      await expect(dashboardPage.selectTranscriptBtn).not.toHaveClass(/active/);
      
      // File display should show
      await expect(dashboardPage.selectedFileDisplay).toBeVisible();
      await expect(dashboardPage.selectedFileName).toContainText('video_for_testing.mp4');
      await expect(dashboardPage.selectedFileType).toContainText('VIDEO file');
      
      // Start button should be enabled
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
    });
    
    await test.step('Test File Change Functionality', async () => {
      // Click change file button
      await dashboardPage.changeFileBtn.click();
      
      // File display should be hidden
      await expect(dashboardPage.selectedFileDisplay).toBeHidden();
      
      // Start button should be disabled again
      await expect(dashboardPage.startProcessingBtn).toBeDisabled();
      
      // No buttons should be active
      await expect(dashboardPage.selectVideoBtn).not.toHaveClass(/active/);
      await expect(dashboardPage.selectAudioBtn).not.toHaveClass(/active/);
      await expect(dashboardPage.selectTranscriptBtn).not.toHaveClass(/active/);
    });
    
    await test.step('Test Audio File Selection', async () => {
      const audioPath = testDataPath.replace('.mp4', '.wav');
      await dashboardPage.selectAudioFile(audioPath);
      
      // Audio button should be active
      await expect(dashboardPage.selectAudioBtn).toHaveClass(/active/);
      await expect(dashboardPage.selectVideoBtn).not.toHaveClass(/active/);
      
      // File display should show
      await expect(dashboardPage.selectedFileDisplay).toBeVisible();
      
      // Start button should be enabled
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
    });
  });
  
  test('Workflow Step Configuration', async ({ mainWindow, testDataPath }) => {
    console.log('Testing workflow step configuration');
    
    await dashboardPage.selectVideoFile(testDataPath);
    
    await test.step('Test Initial Checkbox States for Video', async () => {
      // All steps should be enabled and checked for video
      await expect(dashboardPage.workflowSteps.extractAudio).toBeEnabled();
      await expect(dashboardPage.workflowSteps.extractAudio).toBeChecked();
      
      await expect(dashboardPage.workflowSteps.processAudio).toBeEnabled();
      await expect(dashboardPage.workflowSteps.processAudio).toBeChecked();
      
      await expect(dashboardPage.workflowSteps.transcribe).toBeEnabled();
      await expect(dashboardPage.workflowSteps.transcribe).toBeChecked();
      
      await expect(dashboardPage.workflowSteps.summarize).toBeEnabled();
      await expect(dashboardPage.workflowSteps.summarize).toBeChecked();
    });
    
    await test.step('Test Checkbox Toggle Behavior', async () => {
      // Disable transcription
      await dashboardPage.workflowSteps.transcribe.click();
      await expect(dashboardPage.workflowSteps.transcribe).not.toBeChecked();
      
      // Start button should still be enabled (other steps are still active)
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
      
      // Disable extract audio
      await dashboardPage.workflowSteps.extractAudio.click();
      await expect(dashboardPage.workflowSteps.extractAudio).not.toBeChecked();
      
      // Start button should still be enabled
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
      
      // Disable process audio and summarize (leaving no steps enabled)
      await dashboardPage.workflowSteps.processAudio.click();
      await dashboardPage.workflowSteps.summarize.click();
      
      await expect(dashboardPage.workflowSteps.processAudio).not.toBeChecked();
      await expect(dashboardPage.workflowSteps.summarize).not.toBeChecked();
      
      // Start button should be disabled when no steps are enabled
      await expect(dashboardPage.startProcessingBtn).toBeDisabled();
      
      // Re-enable summarize
      await dashboardPage.workflowSteps.summarize.click();
      await expect(dashboardPage.workflowSteps.summarize).toBeChecked();
      
      // Start button should be enabled again
      await expect(dashboardPage.startProcessingBtn).toBeEnabled();
    });
    
    await test.step('Test Configuration Options', async () => {
      // Test audio format selection
      await dashboardPage.configOptions.audioFormat.selectOption('mp3');
      await expect(dashboardPage.configOptions.audioFormat).toHaveValue('mp3');
      
      // Test audio quality selection
      await dashboardPage.configOptions.audioQuality.selectOption('medium');
      await expect(dashboardPage.configOptions.audioQuality).toHaveValue('medium');
      
      // Test transcribe language selection
      await dashboardPage.configOptions.transcribeLanguage.selectOption('en');
      await expect(dashboardPage.configOptions.transcribeLanguage).toHaveValue('en');
      
      // Test summary template selection
      await dashboardPage.configOptions.summaryTemplate.selectOption('Meeting Notes');
      await expect(dashboardPage.configOptions.summaryTemplate).toHaveValue('Meeting Notes');
    });
  });
  
  test('Tab Navigation', async ({ mainWindow }) => {
    console.log('Testing tab navigation');
    
    await test.step('Navigate Between All Tabs', async () => {
      // Start on dashboard
      await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
      await expect(mainWindow.locator('.nav-item[data-tab="dashboard"]')).toHaveClass(/active/);
      
      // Navigate to settings
      await mainWindow.locator('.nav-item[data-tab="settings"]').click();
      await expect(mainWindow.locator('#settings-tab')).toBeVisible();
      await expect(mainWindow.locator('#dashboard-tab')).toBeHidden();
      await expect(mainWindow.locator('.nav-item[data-tab="settings"]')).toHaveClass(/active/);
      await expect(mainWindow.locator('.nav-item[data-tab="dashboard"]')).not.toHaveClass(/active/);
      
      // Navigate to processing
      await mainWindow.locator('.nav-item[data-tab="processing"]').click();
      await expect(mainWindow.locator('#processing-tab')).toBeVisible();
      await expect(mainWindow.locator('#settings-tab')).toBeHidden();
      await expect(mainWindow.locator('#noActiveJob')).toBeVisible();
      await expect(mainWindow.locator('.nav-item[data-tab="processing"]')).toHaveClass(/active/);
      
      // Navigate to history
      await mainWindow.locator('.nav-item[data-tab="history"]').click();
      await expect(mainWindow.locator('#history-tab')).toBeVisible();
      await expect(mainWindow.locator('#processing-tab')).toBeHidden();
      await expect(mainWindow.locator('.nav-item[data-tab="history"]')).toHaveClass(/active/);
      
      // Return to dashboard
      await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
      await expect(mainWindow.locator('#dashboard-tab')).toBeVisible();
      await expect(mainWindow.locator('#history-tab')).toBeHidden();
      await expect(mainWindow.locator('.nav-item[data-tab="dashboard"]')).toHaveClass(/active/);
    });
  });
  
  test('Theme Toggle Functionality', async ({ mainWindow }) => {
    console.log('Testing theme toggle functionality');
    
    await test.step('Test Header Theme Toggle', async () => {
      const themeToggle = mainWindow.locator('#themeToggle');
      const body = mainWindow.locator('body');
      
      // Get initial theme state
      const initialTheme = await body.getAttribute('data-theme');
      console.log('Initial theme:', initialTheme);
      
      // Toggle theme
      await themeToggle.click();
      
      // Wait for theme change
      await mainWindow.waitForTimeout(500);
      
      const newTheme = await body.getAttribute('data-theme');
      console.log('New theme:', newTheme);
      
      // Theme should have changed
      expect(newTheme).not.toBe(initialTheme);
      
      // Toggle back
      await themeToggle.click();
      await mainWindow.waitForTimeout(500);
      
      const revertedTheme = await body.getAttribute('data-theme');
      console.log('Reverted theme:', revertedTheme);
      
      // Should be back to original theme
      expect(revertedTheme).toBe(initialTheme);
    });
    
    await test.step('Test Settings Theme Toggle', async () => {
      // Navigate to settings
      await mainWindow.locator('.nav-item[data-tab="settings"]').click();
      
      const settingsThemeToggle = mainWindow.locator('#settingsThemeToggle');
      const body = mainWindow.locator('body');
      
      const initialTheme = await body.getAttribute('data-theme');
      
      // Toggle theme from settings
      await settingsThemeToggle.click();
      await mainWindow.waitForTimeout(500);
      
      const newTheme = await body.getAttribute('data-theme');
      expect(newTheme).not.toBe(initialTheme);
      
      // Both toggles should be in sync
      const headerToggle = mainWindow.locator('#themeToggle');
      const headerToggleState = await headerToggle.evaluate(el => el.classList.contains('active'));
      const settingsToggleState = await settingsThemeToggle.evaluate(el => el.classList.contains('active'));
      
      expect(headerToggleState).toBe(settingsToggleState);
    });
  });
  
  test('Settings Configuration', async ({ mainWindow }) => {
    console.log('Testing settings configuration');
    
    // Navigate to settings
    await mainWindow.locator('.nav-item[data-tab="settings"]').click();
    
    await test.step('Test LLM Provider and Model Selection', async () => {
      // Test OpenAI selection
      await settingsPage.llmProvider.selectOption('openai');
      await settingsPage.verifyProviderAndModel('openai', 'gpt-4o-mini');
      
      // Test Anthropic selection
      await settingsPage.llmProvider.selectOption('anthropic');
      await mainWindow.waitForTimeout(500); // Wait for model options to update
      await settingsPage.verifyProviderAndModel('anthropic', 'claude-3-5-sonnet-20241022');
    });
    
    await test.step('Test Configuration Form', async () => {
      await settingsPage.configureLLMSettings({
        provider: 'openai',
        model: 'gpt-4o-mini',
        apiKey: 'test-api-key-123',
        replicateToken: 'test-replicate-token-456',
        maxTokens: 2500,
        chunkSeconds: 1200
      });
      
      // Verify values are set
      const config = await settingsPage.getConfigurationValues();
      expect(config.provider).toBe('openai');
      expect(config.model).toBe('gpt-4o-mini');
      expect(config.maxTokens).toBe('2500');
      expect(config.chunkSeconds).toBe('1200');
      
      // Test save functionality
      await settingsPage.saveConfiguration();
    });
  });
  
  test('Quick Actions Functionality', async ({ mainWindow }) => {
    console.log('Testing quick actions functionality');
    
    await test.step('Test Quick Action Navigation', async () => {
      // Test transcribe only action
      const transcribeAction = mainWindow.locator('.quick-action-item[data-action="transcribe"]');
      await transcribeAction.click();
      
      // Should navigate to processing tab
      await expect(mainWindow.locator('#processing-tab')).toBeVisible();
      await expect(mainWindow.locator('.nav-item[data-tab="processing"]')).toHaveClass(/active/);
      
      // Return to dashboard
      await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
      
      // Test summarize only action
      const summarizeAction = mainWindow.locator('.quick-action-item[data-action="summarize"]');
      await summarizeAction.click();
      
      // Should navigate to processing tab
      await expect(mainWindow.locator('#processing-tab')).toBeVisible();
      await expect(mainWindow.locator('.nav-item[data-tab="processing"]')).toHaveClass(/active/);
      
      // Return to dashboard
      await mainWindow.locator('.nav-item[data-tab="dashboard"]').click();
      
      // Test settings action
      const settingsAction = mainWindow.locator('.quick-action-item[data-action="settings"]');
      await settingsAction.click();
      
      // Should navigate to settings tab
      await expect(mainWindow.locator('#settings-tab')).toBeVisible();
      await expect(mainWindow.locator('.nav-item[data-tab="settings"]')).toHaveClass(/active/);
    });
  });
  
  test('UI Responsiveness and Layout', async ({ mainWindow }) => {
    console.log('Testing UI responsiveness and layout');
    
    await test.step('Test Window Resize Behavior', async () => {
      // Test larger viewport
      await mainWindow.setViewportSize({ width: 1600, height: 1000 });
      await mainWindow.waitForTimeout(500);
      
      // Verify layout is still intact
      await expect(mainWindow.locator('.app-container')).toBeVisible();
      await expect(mainWindow.locator('.sidebar')).toBeVisible();
      await expect(mainWindow.locator('.content-area')).toBeVisible();
      
      // Test smaller viewport
      await mainWindow.setViewportSize({ width: 1200, height: 700 });
      await mainWindow.waitForTimeout(500);
      
      // Layout should still be functional
      await expect(mainWindow.locator('.app-container')).toBeVisible();
      await expect(mainWindow.locator('.sidebar')).toBeVisible();
      
      // Reset to original size
      await mainWindow.setViewportSize({ width: 1400, height: 900 });
    });
    
    await test.step('Test File Selection Grid Layout', async () => {
      // Verify file type buttons are in grid layout
      const fileTypeGrid = mainWindow.locator('.file-type-grid');
      await expect(fileTypeGrid).toBeVisible();
      
      const videoBtn = mainWindow.locator('#selectVideoBtn');
      const audioBtn = mainWindow.locator('#selectAudioBtn');
      const transcriptBtn = mainWindow.locator('#selectTranscriptBtn');
      
      await expect(videoBtn).toBeVisible();
      await expect(audioBtn).toBeVisible();
      await expect(transcriptBtn).toBeVisible();
      
      // Verify buttons are arranged horizontally
      const videoBtnBox = await videoBtn.boundingBox();
      const audioBtnBox = await audioBtn.boundingBox();
      const transcriptBtnBox = await transcriptBtn.boundingBox();
      
      // All buttons should be roughly at the same Y position (horizontal layout)
      expect(Math.abs(videoBtnBox!.y - audioBtnBox!.y)).toBeLessThan(10);
      expect(Math.abs(audioBtnBox!.y - transcriptBtnBox!.y)).toBeLessThan(10);
      
      // Video button should be leftmost
      expect(videoBtnBox!.x).toBeLessThan(audioBtnBox!.x);
      expect(audioBtnBox!.x).toBeLessThan(transcriptBtnBox!.x);
    });
  });
});