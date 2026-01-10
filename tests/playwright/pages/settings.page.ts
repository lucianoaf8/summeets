import { Page, Locator, expect } from '@playwright/test';

export class SettingsPage {
  readonly page: Page;
  readonly llmProvider: Locator;
  readonly llmModel: Locator;
  readonly apiKey: Locator;
  readonly apiKeyLabel: Locator;
  readonly replicateToken: Locator;
  readonly maxTokens: Locator;
  readonly chunkSeconds: Locator;
  readonly saveConfigBtn: Locator;
  readonly themeToggle: Locator;
  
  constructor(page: Page) {
    this.page = page;
    this.llmProvider = page.locator('#llmProvider');
    this.llmModel = page.locator('#llmModel');
    this.apiKey = page.locator('#apiKey');
    this.apiKeyLabel = page.locator('#apiKeyLabel');
    this.replicateToken = page.locator('#replicateToken');
    this.maxTokens = page.locator('#maxTokens');
    this.chunkSeconds = page.locator('#chunkSeconds');
    this.saveConfigBtn = page.locator('#saveConfigBtn');
    this.themeToggle = page.locator('#settingsThemeToggle');
  }
  
  async configureLLMSettings(options: {
    provider?: string;
    model?: string;
    apiKey?: string;
    replicateToken?: string;
    maxTokens?: number;
    chunkSeconds?: number;
  }): Promise<void> {
    console.log('Configuring LLM settings:', options);
    
    if (options.provider) {
      await this.llmProvider.selectOption(options.provider);
      
      // Wait for model options to update
      await this.page.waitForTimeout(500);
    }
    
    if (options.model) {
      await this.llmModel.selectOption(options.model);
    }
    
    if (options.apiKey) {
      await this.apiKey.fill(options.apiKey);
    }
    
    if (options.replicateToken) {
      await this.replicateToken.fill(options.replicateToken);
    }
    
    if (options.maxTokens) {
      await this.maxTokens.fill(options.maxTokens.toString());
    }
    
    if (options.chunkSeconds) {
      await this.chunkSeconds.fill(options.chunkSeconds.toString());
    }
    
    console.log('LLM settings configured');
  }
  
  async saveConfiguration(): Promise<void> {
    console.log('Saving configuration...');
    
    await this.saveConfigBtn.click();
    
    // Wait for save confirmation (you might need to adjust this based on UI feedback)
    await this.page.waitForTimeout(1000);
    
    console.log('Configuration saved');
  }
  
  async verifyProviderAndModel(provider: string, model: string): Promise<void> {
    await expect(this.llmProvider).toHaveValue(provider);
    await expect(this.llmModel).toHaveValue(model);
    
    // Verify API key label updates based on provider
    if (provider === 'openai') {
      await expect(this.apiKeyLabel).toContainText('OpenAI API Key');
    } else if (provider === 'anthropic') {
      await expect(this.apiKeyLabel).toContainText('Anthropic API Key');
    }
  }
  
  async toggleTheme(): Promise<void> {
    await this.themeToggle.click();
  }
  
  async getConfigurationValues(): Promise<{
    provider: string;
    model: string;
    maxTokens: string;
    chunkSeconds: string;
  }> {
    return {
      provider: await this.llmProvider.inputValue(),
      model: await this.llmModel.inputValue(),
      maxTokens: await this.maxTokens.inputValue(),
      chunkSeconds: await this.chunkSeconds.inputValue()
    };
  }
}