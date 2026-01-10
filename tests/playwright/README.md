# Playwright GUI Testing Framework for Summeets

This directory contains a comprehensive automated testing framework for the Summeets Electron GUI application using Playwright. The framework provides end-to-end testing capabilities with real-time process monitoring and complete workflow validation.

## Quick Start

### Prerequisites

1. **Node.js 18+** - Required for Playwright and Electron
2. **Python 3.11+** - Required for Summeets backend
3. **Summeets package installed** - `pip install -e .` from project root

### Installation

1. Install Playwright dependencies:
```bash
# From project root
npm install --save-dev @playwright/test @types/node typescript

# Install Playwright browsers
npx playwright install --with-deps electron
```

2. Verify installation:
```bash
npx playwright test --list
```

### Running Tests

```bash
# Run all GUI tests
npx playwright test

# Run specific test suite
npx playwright test tests/playwright/e2e/complete-workflow.spec.ts

# Run with visual interface (great for development)
npx playwright test --ui

# Run in headed mode (see browser)
npx playwright test --headed

# Run specific test by name
npx playwright test --grep "Complete Video Processing Workflow"

# Generate HTML report
npx playwright show-report
```

## Test Structure

### Core Components

- **`utils/electron-utils.ts`** - Base testing utilities and Electron app management
- **`pages/`** - Page Object Models for GUI components
  - `dashboard.page.ts` - Main dashboard interactions
  - `processing.page.ts` - Processing tab and job monitoring
  - `settings.page.ts` - Configuration management
- **`e2e/`** - End-to-end test scenarios
  - `complete-workflow.spec.ts` - Full workflow automation tests
  - `gui-interactions.spec.ts` - UI component interaction tests

### Test Scenarios Covered

#### 1. Complete Video Processing Workflow
- ✅ API configuration and settings
- ✅ Video file selection via GUI
- ✅ Workflow step configuration (extract → process → transcribe → summarize)
- ✅ Real-time progress monitoring
- ✅ Output file verification
- ✅ Completion state validation

#### 2. Audio-Only Processing
- ✅ Audio file selection
- ✅ Workflow adaptation (skip extract step)
- ✅ Processing monitoring

#### 3. Transcript-Only Summarization
- ✅ Transcript file selection
- ✅ Summary-only workflow
- ✅ Template configuration

#### 4. Error Handling and Recovery
- ✅ Invalid file handling
- ✅ Job cancellation
- ✅ Error message validation

#### 5. GUI Interactions
- ✅ File selection buttons and states
- ✅ Workflow checkbox behavior
- ✅ Tab navigation
- ✅ Theme toggle functionality
- ✅ Configuration form validation

## Key Features

### 🚀 Electron Integration
- Full Electron app launch and management
- Real Electron file dialogs (mocked for testing)
- Native window interactions

### 📊 Real-Time Monitoring
- Live job progress tracking
- Log output capture and analysis
- Process completion detection
- Error and cancellation handling

### 🎯 Smart Selectors
- CSS selector-based element targeting
- Wait strategies for dynamic content
- Robust element state verification

### 📝 Comprehensive Reporting
- HTML reports with screenshots
- JSON results for CI integration
- JUnit XML for test frameworks
- Video recordings on failure

### 🔄 CI/CD Ready
- GitHub Actions workflow included
- Environment variable configuration
- Artifact collection and storage
- Pull request commenting

## Configuration

### Environment Variables

Set these in your environment or CI/CD pipeline:

```bash
# API Keys (optional - tests will use mock values if not provided)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
REPLICATE_API_TOKEN=r8_...

# Test Configuration
CI=true  # Enables CI-specific behavior
```

### Playwright Configuration

Edit `playwright.config.ts` to customize:

```typescript
export default defineConfig({
  // Test directory
  testDir: './tests/playwright',
  
  // Execution settings
  workers: 1,  // Sequential execution for GUI tests
  retries: 2,  // Retry failed tests
  timeout: 300000,  // 5 minute timeout for full workflows
  
  // Reporting
  reporter: [
    ['html', { outputFolder: 'tests/reports/playwright-html' }],
    ['json', { outputFile: 'tests/reports/playwright-results.json' }]
  ],
  
  // Browser settings
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  }
});
```

## Advanced Usage

### Custom Test Data

Place test files in appropriate directories:

```
data/
├── video/
│   └── video_for_testing.mp4
├── audio/
│   └── audio_sample.wav
└── transcript/
    └── video_for_testing/
        └── video_for_testing.json
```

### Debugging Tests

1. **Visual Mode**: `npx playwright test --ui`
2. **Step Through**: `npx playwright test --debug`
3. **Headed Mode**: `npx playwright test --headed`
4. **Screenshots**: Automatically captured on failure
5. **Videos**: Recorded for failed tests
6. **Traces**: Complete interaction recordings

### Writing New Tests

1. **Create Page Object** (if needed):
```typescript
// tests/playwright/pages/my-page.page.ts
export class MyPage {
  constructor(private page: Page) {}
  
  async doSomething() {
    await this.page.locator('#my-button').click();
  }
}
```

2. **Write Test**:
```typescript
// tests/playwright/e2e/my-test.spec.ts
import { test, expect } from '../utils/electron-utils';

test('My Test', async ({ mainWindow }) => {
  await mainWindow.locator('#element').click();
  await expect(mainWindow.locator('#result')).toBeVisible();
});
```

### Performance Testing

Monitor application performance:

```typescript
test('Performance Test', async ({ mainWindow }) => {
  const startTime = Date.now();
  
  // Perform actions
  await dashboardPage.selectVideoFile(testPath);
  
  const endTime = Date.now();
  expect(endTime - startTime).toBeLessThan(5000);
});
```

## CI/CD Integration

### GitHub Actions

The included workflow (`.github/workflows/playwright-gui-tests.yml`) provides:

- ✅ Automated test execution on PR and push
- ✅ Multiple test suite options (all, smoke, specific)
- ✅ Artifact collection (reports, screenshots, videos)
- ✅ PR commenting with results
- ✅ Performance testing on main branch

### Manual Workflow Dispatch

Trigger tests manually with different options:
1. Go to Actions tab in GitHub
2. Select "Playwright GUI Tests" workflow
3. Click "Run workflow"
4. Choose test suite (all, smoke, complete-workflow, gui-interactions)

## Troubleshooting

### Common Issues

1. **Electron App Won't Launch**
   ```bash
   # Verify Electron installation
   npx playwright install electron
   
   # Check file permissions
   chmod +x electron/main.js
   ```

2. **Tests Time Out**
   ```bash
   # Increase timeout in playwright.config.ts
   timeout: 600000  // 10 minutes
   ```

3. **File Not Found Errors**
   ```bash
   # Verify test data exists
   ls -la data/video/video_for_testing.mp4
   
   # Create mock file for CI
   echo "mock" > data/video/video_for_testing.mp4
   ```

4. **Permission Errors**
   ```bash
   # Fix Node modules permissions
   npm ci
   npx playwright install --with-deps electron
   ```

### Debug Information

Enable verbose logging:

```bash
# Debug Playwright
DEBUG=pw:* npx playwright test

# Debug Electron
ELECTRON_ENABLE_LOGGING=1 npx playwright test

# Debug test execution
npx playwright test --debug
```

### CI-Specific Behavior

Tests automatically adapt for CI environments:

- Mock API calls when keys not available
- Skip file verification if outputs not generated
- Use headless mode
- Reduced timeouts
- Alternative assertion strategies

## Best Practices

### Test Organization
- Keep tests focused and independent
- Use descriptive test names
- Group related tests with `test.describe()`
- Use `test.step()` for clear test phases

### Selectors
- Prefer data-testid attributes
- Use CSS selectors for UI elements
- Avoid xpath unless necessary
- Test selector stability

### Assertions
- Use Playwright's auto-waiting assertions
- Verify state changes explicitly
- Check both positive and negative conditions
- Include timeout handling

### Maintenance
- Update selectors when UI changes
- Keep Page Object Models in sync
- Review and update test data regularly
- Monitor test execution times

## Examples

### Basic File Selection Test
```typescript
test('File Selection', async ({ mainWindow, testDataPath }) => {
  const dashboard = new DashboardPage(mainWindow);
  
  await dashboard.selectVideoFile(testDataPath);
  await expect(dashboard.selectedFileDisplay).toBeVisible();
  await expect(dashboard.startProcessingBtn).toBeEnabled();
});
```

### Complete Workflow Test
```typescript
test('Full Workflow', async ({ mainWindow, testDataPath }) => {
  const dashboard = new DashboardPage(mainWindow);
  const processing = new ProcessingPage(mainWindow);
  
  // Configure and start
  await dashboard.selectVideoFile(testDataPath);
  await dashboard.configureWorkflow({ 
    transcribe: true, 
    summarize: true 
  });
  await dashboard.startProcessing();
  
  // Monitor completion
  const result = await processing.monitorJobProgress();
  expect(result.success).toBe(true);
});
```

## Contributing

1. **Add New Tests**: Follow existing patterns in `e2e/` directory
2. **Update Page Objects**: Maintain page models when UI changes
3. **Improve Coverage**: Add tests for edge cases and error conditions
4. **Optimize Performance**: Keep test execution time reasonable
5. **Documentation**: Update this README with new features

## Support

For issues with this testing framework:

1. Check the [Playwright documentation](https://playwright.dev/)
2. Review test logs and screenshots in `test-results/`
3. Run tests with `--debug` flag for step-by-step execution
4. Examine the generated HTML report for detailed information

The framework is designed to be robust and maintainable, providing comprehensive coverage of the Summeets GUI functionality while being easy to extend and modify as the application evolves.