# Requirements Analysis - New GUI Workflow Implementation
**Date**: 2025-08-16
**Scope**: GUI implementation with flexible file input and workflow step management

## Requirements Summary

### File Input Types
1. **Video Files** → Extract audio → Process → Transcribe → Summarize
2. **Audio Files** → Process → Transcribe → Summarize  
3. **Transcript Files** → Summarize only

### Workflow Steps (Configurable)
1. **Extract Audio Track** (video only)
   - Settings: Audio format, quality options
2. **Process Audio Track** (audio/video)
   - Volume: Increase volume checkbox
   - Normalization: Normalize audio checkbox
   - Output formats: m4a, mka, mp3, ogg (checkboxes)
3. **Transcribe** (audio/video)
   - Model selection, language settings
4. **Summarize** (all types)
   - Template selection (Default, Custom)
   - Provider/model settings

### Conditional Logic
- **Video selected**: All steps available
- **Audio selected**: Skip "Extract Audio Track"
- **Transcript selected**: Skip "Extract Audio Track" and "Transcribe"

## Implementation Plan

### Phase 1: Core GUI Framework
- Create modern ttkbootstrap GUI with clean layout
- File selection panel with radio buttons for input type
- Workflow steps panel with checkboxes and settings
- Progress tracking and results display

### Phase 2: File Type Detection
- Extend validation to support video formats
- Implement file type detection logic
- Create conditional step enabling/disabling

### Phase 3: Workflow Engine
- Enhance processing pipeline for conditional steps
- Implement video audio extraction
- Add audio processing options
- Create configurable workflow execution

### Phase 4: Integration & Testing
- Comprehensive test suite for all workflow combinations
- Error handling and user feedback
- Performance optimization

## Technical Considerations

### Video Support
- Need FFmpeg video format detection
- Audio extraction from various video formats
- File size and duration validation

### Audio Processing Enhancements  
- Volume amplification utilities
- Multiple output format support
- Audio quality metrics

### State Management
- Workflow configuration persistence
- Progress tracking across async operations
- Error recovery and retry logic

### User Experience
- Intuitive step-by-step interface
- Real-time feedback and progress
- Clear error messages and guidance