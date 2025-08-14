#!/usr/bin/env python3
"""Configuration tab component for application settings."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Any, Dict, Optional, Callable
import queue

from .base_component import BaseTabComponent
from ..constants import *


class ConfigTab(BaseTabComponent):
    """Configuration and settings tab component."""
    
    def __init__(self, parent_notebook: ttk.Notebook, message_queue: queue.Queue):
        # Configuration variables
        self.provider_var = tk.StringVar(value=DEFAULT_LLM_PROVIDER)
        self.model_var = tk.StringVar(value=DEFAULT_LLM_MODEL)
        self.max_tokens_var = tk.IntVar(value=DEFAULT_MAX_OUTPUT_TOKENS)
        self.chunk_seconds_var = tk.IntVar(value=DEFAULT_CHUNK_SECONDS)
        self.cod_passes_var = tk.IntVar(value=DEFAULT_COD_PASSES)
        self.ffmpeg_bin_var = tk.StringVar(value=DEFAULT_FFMPEG_BIN)
        self.ffprobe_bin_var = tk.StringVar(value=DEFAULT_FFPROBE_BIN)
        
        # API key variables (displayed as masked)
        self.openai_key_var = tk.StringVar()
        self.anthropic_key_var = tk.StringVar()
        self.replicate_key_var = tk.StringVar()
        
        # UI elements
        self.model_combo: Optional[ttk.Combobox] = None
        self.api_key_entries: Dict[str, ttk.Entry] = {}
        self.settings_changed = False
        
        # Callback for settings changes
        self.on_settings_changed: Optional[Callable[[Dict[str, Any]], None]] = None
        
        super().__init__(parent_notebook, TAB_CONFIG, message_queue)
    
    def setup_ui(self) -> None:
        """Setup the configuration tab UI elements."""
        # Create scrollable frame for all settings
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # LLM Provider Settings
        self._create_llm_settings(scrollable_frame)
        
        # API Keys Section
        self._create_api_keys_section(scrollable_frame)
        
        # Audio Processing Settings
        self._create_audio_settings(scrollable_frame)
        
        # Advanced Settings
        self._create_advanced_settings(scrollable_frame)
        
        # Action Buttons
        self._create_action_buttons(scrollable_frame)
        
        # Bind mouse wheel scrolling
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
    
    def _create_llm_settings(self, parent: tk.Widget) -> None:
        """Create LLM provider and model settings."""
        section = self.create_section(parent, "🤖 AI Model Settings")
        
        # Provider selection
        provider_frame = ttk.Frame(section)
        provider_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(provider_frame, text="Provider:", width=12).pack(side='left')
        provider_combo = ttk.Combobox(
            provider_frame,
            textvariable=self.provider_var,
            values=LLM_PROVIDERS,
            state='readonly',
            width=COMBO_WIDTH_PROVIDER
        )
        provider_combo.pack(side='left', padx=(DEFAULT_PADX, 0))
        provider_combo.bind('<<ComboboxSelected>>', self._on_provider_changed)
        
        # Model selection
        model_frame = ttk.Frame(section)
        model_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(model_frame, text="Model:", width=12).pack(side='left')
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            state='readonly',
            width=COMBO_WIDTH_MODEL
        )
        self.model_combo.pack(side='left', padx=(DEFAULT_PADX, 0))
        self.model_combo.bind('<<ComboboxSelected>>', self._on_setting_changed)
        
        # Update model options based on current provider
        self._update_model_options()
        
        # Token limit
        token_frame = ttk.Frame(section)
        token_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(token_frame, text="Max Tokens:", width=12).pack(side='left')
        token_spinbox = tk.Spinbox(
            token_frame,
            from_=MIN_OUTPUT_TOKENS,
            to=MAX_OUTPUT_TOKENS,
            increment=TOKEN_INCREMENT,
            textvariable=self.max_tokens_var,
            width=SPINBOX_WIDTH,
            command=self._on_setting_changed
        )
        token_spinbox.pack(side='left', padx=(DEFAULT_PADX, 0))
    
    def _create_api_keys_section(self, parent: tk.Widget) -> None:
        """Create API keys configuration section."""
        section = self.create_section(parent, "🔑 API Keys")
        
        # Warning label
        warning_label = ttk.Label(
            section,
            text="⚠️ API keys are stored securely in your system keychain",
            font=SECONDARY_FONT,
            foreground=COLORS['warning']
        )
        warning_label.pack(anchor='w', pady=(0, DEFAULT_PADY))
        
        # OpenAI API Key
        openai_frame = ttk.Frame(section)
        openai_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(openai_frame, text="OpenAI:", width=12).pack(side='left')
        openai_entry = ttk.Entry(
            openai_frame,
            textvariable=self.openai_key_var,
            show='*',
            width=ENTRY_WIDTH
        )
        openai_entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        openai_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        self.api_key_entries['openai'] = openai_entry
        
        ttk.Button(
            openai_frame,
            text="📋",
            command=lambda: self._paste_api_key('openai'),
            width=3
        ).pack(side='right', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            openai_frame,
            text="🔗",
            command=lambda: self._open_api_url(OPENAI_KEYS_URL),
            width=3
        ).pack(side='right')
        
        # Anthropic API Key
        anthropic_frame = ttk.Frame(section)
        anthropic_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(anthropic_frame, text="Anthropic:", width=12).pack(side='left')
        anthropic_entry = ttk.Entry(
            anthropic_frame,
            textvariable=self.anthropic_key_var,
            show='*',
            width=ENTRY_WIDTH
        )
        anthropic_entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        anthropic_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        self.api_key_entries['anthropic'] = anthropic_entry
        
        ttk.Button(
            anthropic_frame,
            text="📋",
            command=lambda: self._paste_api_key('anthropic'),
            width=3
        ).pack(side='right', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            anthropic_frame,
            text="🔗",
            command=lambda: self._open_api_url(ANTHROPIC_KEYS_URL),
            width=3
        ).pack(side='right')
        
        # Replicate API Token
        replicate_frame = ttk.Frame(section)
        replicate_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(replicate_frame, text="Replicate:", width=12).pack(side='left')
        replicate_entry = ttk.Entry(
            replicate_frame,
            textvariable=self.replicate_key_var,
            show='*',
            width=ENTRY_WIDTH
        )
        replicate_entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        replicate_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        self.api_key_entries['replicate'] = replicate_entry
        
        ttk.Button(
            replicate_frame,
            text="📋",
            command=lambda: self._paste_api_key('replicate'),
            width=3
        ).pack(side='right', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            replicate_frame,
            text="🔗",
            command=lambda: self._open_api_url(REPLICATE_TOKENS_URL),
            width=3
        ).pack(side='right')
    
    def _create_audio_settings(self, parent: tk.Widget) -> None:
        """Create audio processing settings."""
        section = self.create_section(parent, "🎵 Audio Processing")
        
        # FFmpeg binary path
        ffmpeg_frame = ttk.Frame(section)
        ffmpeg_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(ffmpeg_frame, text="FFmpeg:", width=12).pack(side='left')
        ffmpeg_entry = ttk.Entry(
            ffmpeg_frame,
            textvariable=self.ffmpeg_bin_var,
            width=ENTRY_WIDTH
        )
        ffmpeg_entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        ffmpeg_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        
        ttk.Button(
            ffmpeg_frame,
            text="📁",
            command=lambda: self._browse_executable('ffmpeg'),
            width=3
        ).pack(side='right', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            ffmpeg_frame,
            text="🧪",
            command=self._test_ffmpeg,
            width=3
        ).pack(side='right')
        
        # FFprobe binary path
        ffprobe_frame = ttk.Frame(section)
        ffprobe_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(ffprobe_frame, text="FFprobe:", width=12).pack(side='left')
        ffprobe_entry = ttk.Entry(
            ffprobe_frame,
            textvariable=self.ffprobe_bin_var,
            width=ENTRY_WIDTH
        )
        ffprobe_entry.pack(side='left', padx=(DEFAULT_PADX, 0), fill='x', expand=True)
        ffprobe_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        
        ttk.Button(
            ffprobe_frame,
            text="📁",
            command=lambda: self._browse_executable('ffprobe'),
            width=3
        ).pack(side='right', padx=(DEFAULT_PADX, 0))
    
    def _create_advanced_settings(self, parent: tk.Widget) -> None:
        """Create advanced processing settings."""
        section = self.create_section(parent, "⚙️ Advanced Settings")
        
        # Chunk duration
        chunk_frame = ttk.Frame(section)
        chunk_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(chunk_frame, text="Chunk (sec):", width=12).pack(side='left')
        chunk_spinbox = tk.Spinbox(
            chunk_frame,
            from_=MIN_CHUNK_SECONDS,
            to=MAX_CHUNK_SECONDS,
            increment=CHUNK_INCREMENT,
            textvariable=self.chunk_seconds_var,
            width=SPINBOX_WIDTH,
            command=self._on_setting_changed
        )
        chunk_spinbox.pack(side='left', padx=(DEFAULT_PADX, 0))
        
        ttk.Label(
            chunk_frame,
            text="(Audio split duration for processing)",
            font=INFO_FONT,
            foreground=COLORS['text_secondary']
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
        
        # Chain-of-Density passes
        cod_frame = ttk.Frame(section)
        cod_frame.pack(fill='x', pady=DEFAULT_PADY)
        
        ttk.Label(cod_frame, text="COD Passes:", width=12).pack(side='left')
        cod_spinbox = tk.Spinbox(
            cod_frame,
            from_=MIN_COD_PASSES,
            to=MAX_COD_PASSES,
            increment=COD_INCREMENT,
            textvariable=self.cod_passes_var,
            width=SPINBOX_WIDTH,
            command=self._on_setting_changed
        )
        cod_spinbox.pack(side='left', padx=(DEFAULT_PADX, 0))
        
        ttk.Label(
            cod_frame,
            text="(Summary refinement iterations)",
            font=INFO_FONT,
            foreground=COLORS['text_secondary']
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
    
    def _create_action_buttons(self, parent: tk.Widget) -> None:
        """Create configuration action buttons."""
        action_frame = ttk.Frame(parent)
        action_frame.pack(fill='x', padx=SECTION_PADX, pady=SECTION_PADY)
        
        # Primary actions
        ttk.Button(
            action_frame,
            text="💾 Save Settings",
            command=self._save_settings,
            style='success.TButton'
        ).pack(side='left', fill='x', expand=True)
        
        ttk.Button(
            action_frame,
            text="🔄 Reset to Defaults",
            command=self._reset_settings
        ).pack(side='left', fill='x', expand=True, padx=(DEFAULT_PADX, 0))
        
        # Utility actions
        utility_frame = ttk.Frame(parent)
        utility_frame.pack(fill='x', padx=SECTION_PADX, pady=DEFAULT_PADY)
        
        ttk.Button(
            utility_frame,
            text="📄 Export Config",
            command=self._export_config
        ).pack(side='left')
        
        ttk.Button(
            utility_frame,
            text="📁 Import Config",
            command=self._import_config
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            utility_frame,
            text="🧪 Test Connection",
            command=self._test_api_connection
        ).pack(side='right')
    
    def _on_provider_changed(self, event=None) -> None:
        """Handle LLM provider change."""
        self._update_model_options()
        self._on_setting_changed()
    
    def _update_model_options(self) -> None:
        """Update model options based on selected provider."""
        provider = self.provider_var.get()
        
        if provider == 'openai':
            models = OPENAI_MODELS
            default_model = 'gpt-4o-mini'
        elif provider == 'anthropic':
            models = ANTHROPIC_MODELS
            default_model = 'claude-3-5-sonnet-20241022'
        else:
            models = ['gpt-4o-mini']
            default_model = 'gpt-4o-mini'
        
        if self.model_combo:
            self.model_combo['values'] = models
            # Set to default if current model not in new list
            if self.model_var.get() not in models:
                self.model_var.set(default_model)
    
    def _on_setting_changed(self, event=None) -> None:
        """Handle any setting change."""
        self.settings_changed = True
        
        # Notify main application of changes
        settings = self._get_current_settings()
        self.send_message('settings_changed', settings)
        
        if self.on_settings_changed:
            self.on_settings_changed(settings)
    
    def _paste_api_key(self, provider: str) -> None:
        """Paste API key from clipboard."""
        try:
            key = self.frame.clipboard_get().strip()
            if provider == 'openai' and key.startswith('sk-'):
                self.openai_key_var.set(key)
            elif provider == 'anthropic' and key.startswith('sk-ant-'):
                self.anthropic_key_var.set(key)
            elif provider == 'replicate' and key.startswith('r8_'):
                self.replicate_key_var.set(key)
            else:
                self.show_error("Invalid Key", f"Clipboard content doesn't look like a valid {provider} API key.")
                return
            
            self._on_setting_changed()
            self.show_info("Key Pasted", f"{provider.title()} API key pasted from clipboard.")
            
        except tk.TclError:
            self.show_error("Clipboard Error", "Could not read from clipboard.")
    
    def _open_api_url(self, url: str) -> None:
        """Open API key URL in browser."""
        import webbrowser
        try:
            webbrowser.open(url)
        except Exception as e:
            self.show_error("Browser Error", f"Could not open URL: {str(e)}")
    
    def _browse_executable(self, exe_type: str) -> None:
        """Browse for executable file."""
        filename = filedialog.askopenfilename(
            title=f"Select {exe_type} executable",
            filetypes=EXECUTABLE_TYPES
        )
        
        if filename:
            if exe_type == 'ffmpeg':
                self.ffmpeg_bin_var.set(filename)
            elif exe_type == 'ffprobe':
                self.ffprobe_bin_var.set(filename)
            
            self._on_setting_changed()
    
    def _test_ffmpeg(self) -> None:
        """Test FFmpeg installation."""
        import subprocess
        
        ffmpeg_path = self.ffmpeg_bin_var.get()
        try:
            result = subprocess.run(
                [ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SECONDS
            )
            
            if result.returncode == 0:
                # Extract version info
                version_line = result.stdout.split('\n')[0]
                self.show_info("FFmpeg Test", f"FFmpeg is working!\n\n{version_line}")
            else:
                self.show_error("FFmpeg Test", f"FFmpeg test failed:\n{result.stderr}")
                
        except subprocess.TimeoutExpired:
            self.show_error("FFmpeg Test", "FFmpeg test timed out.")
        except FileNotFoundError:
            self.show_error("FFmpeg Test", f"FFmpeg not found at:\n{ffmpeg_path}")
        except Exception as e:
            self.show_error("FFmpeg Test", f"FFmpeg test error:\n{str(e)}")
    
    def _test_api_connection(self) -> None:
        """Test API connection with current provider."""
        provider = self.provider_var.get()
        
        if provider == 'openai' and not self.openai_key_var.get():
            self.show_error("No API Key", "Please enter your OpenAI API key first.")
            return
        elif provider == 'anthropic' and not self.anthropic_key_var.get():
            self.show_error("No API Key", "Please enter your Anthropic API key first.")
            return
        
        # This would need to be implemented with actual API test calls
        self.show_info("API Test", f"API connection test for {provider} would be performed here.")
    
    def _save_settings(self) -> None:
        """Save current settings."""
        settings = self._get_current_settings()
        
        # Validate settings
        if not self._validate_settings(settings):
            return
        
        # Send save message
        self.send_message('save_settings', settings)
        
        self.settings_changed = False
        self.show_info("Settings Saved", "Configuration has been saved successfully.")
    
    def _reset_settings(self) -> None:
        """Reset settings to defaults."""
        if self.confirm_action("Reset Settings", "Reset all settings to default values?"):
            self._load_default_settings()
            self._on_setting_changed()
            self.show_info("Settings Reset", "All settings have been reset to defaults.")
    
    def _export_config(self) -> None:
        """Export configuration to file."""
        filename = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                settings = self._get_current_settings()
                # Remove API keys from export for security
                safe_settings = {k: v for k, v in settings.items() if 'api_key' not in k}
                
                import json
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(safe_settings, f, indent=2)
                
                self.show_info("Export Successful", f"Configuration exported to:\n{filename}")
                
            except Exception as e:
                self.show_error("Export Failed", f"Failed to export configuration:\n{str(e)}")
    
    def _import_config(self) -> None:
        """Import configuration from file."""
        filename = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                import json
                with open(filename, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.load_settings(settings)
                self._on_setting_changed()
                
                self.show_info("Import Successful", f"Configuration imported from:\n{filename}")
                
            except Exception as e:
                self.show_error("Import Failed", f"Failed to import configuration:\n{str(e)}")
    
    def _get_current_settings(self) -> Dict[str, Any]:
        """Get current settings as dictionary."""
        return {
            'llm_provider': self.provider_var.get(),
            'llm_model': self.model_var.get(),
            'max_tokens': self.max_tokens_var.get(),
            'chunk_seconds': self.chunk_seconds_var.get(),
            'cod_passes': self.cod_passes_var.get(),
            'ffmpeg_bin': self.ffmpeg_bin_var.get(),
            'ffprobe_bin': self.ffprobe_bin_var.get(),
            'openai_api_key': self.openai_key_var.get(),
            'anthropic_api_key': self.anthropic_key_var.get(),
            'replicate_api_key': self.replicate_key_var.get()
        }
    
    def _validate_settings(self, settings: Dict[str, Any]) -> bool:
        """Validate settings before saving."""
        # Check API keys based on provider
        provider = settings['llm_provider']
        if provider == 'openai' and not settings['openai_api_key']:
            self.show_error("Missing API Key", "OpenAI API key is required for the selected provider.")
            return False
        elif provider == 'anthropic' and not settings['anthropic_api_key']:
            self.show_error("Missing API Key", "Anthropic API key is required for the selected provider.")
            return False
        
        # Check transcription API key
        if not settings['replicate_api_key']:
            self.show_error("Missing API Key", "Replicate API token is required for transcription.")
            return False
        
        # Validate numeric ranges
        if not (MIN_OUTPUT_TOKENS <= settings['max_tokens'] <= MAX_OUTPUT_TOKENS):
            self.show_error("Invalid Value", f"Max tokens must be between {MIN_OUTPUT_TOKENS} and {MAX_OUTPUT_TOKENS}.")
            return False
        
        if not (MIN_CHUNK_SECONDS <= settings['chunk_seconds'] <= MAX_CHUNK_SECONDS):
            self.show_error("Invalid Value", f"Chunk duration must be between {MIN_CHUNK_SECONDS} and {MAX_CHUNK_SECONDS}.")
            return False
        
        return True
    
    def _load_default_settings(self) -> None:
        """Load default settings values."""
        self.provider_var.set(DEFAULT_LLM_PROVIDER)
        self.model_var.set(DEFAULT_LLM_MODEL)
        self.max_tokens_var.set(DEFAULT_MAX_OUTPUT_TOKENS)
        self.chunk_seconds_var.set(DEFAULT_CHUNK_SECONDS)
        self.cod_passes_var.set(DEFAULT_COD_PASSES)
        self.ffmpeg_bin_var.set(DEFAULT_FFMPEG_BIN)
        self.ffprobe_bin_var.set(DEFAULT_FFPROBE_BIN)
        
        # Clear API keys
        self.openai_key_var.set("")
        self.anthropic_key_var.set("")
        self.replicate_key_var.set("")
        
        # Update model options
        self._update_model_options()
    
    def load_settings(self, settings: Dict[str, Any]) -> None:
        """Load settings from dictionary."""
        if 'llm_provider' in settings:
            self.provider_var.set(settings['llm_provider'])
            self._update_model_options()
        
        if 'llm_model' in settings:
            self.model_var.set(settings['llm_model'])
        
        if 'max_tokens' in settings:
            self.max_tokens_var.set(settings['max_tokens'])
        
        if 'chunk_seconds' in settings:
            self.chunk_seconds_var.set(settings['chunk_seconds'])
        
        if 'cod_passes' in settings:
            self.cod_passes_var.set(settings['cod_passes'])
        
        if 'ffmpeg_bin' in settings:
            self.ffmpeg_bin_var.set(settings['ffmpeg_bin'])
        
        if 'ffprobe_bin' in settings:
            self.ffprobe_bin_var.set(settings['ffprobe_bin'])
        
        # Load API keys if provided
        if 'openai_api_key' in settings:
            self.openai_key_var.set(settings['openai_api_key'])
        
        if 'anthropic_api_key' in settings:
            self.anthropic_key_var.set(settings['anthropic_api_key'])
        
        if 'replicate_api_key' in settings:
            self.replicate_key_var.set(settings['replicate_api_key'])
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update component state based on external changes."""
        if 'settings_loaded' in state:
            self.load_settings(state['settings_loaded'])
        
        if 'api_test_result' in state:
            result = state['api_test_result']
            if result['success']:
                self.show_info("API Test", f"✅ {result['provider']} API connection successful!")
            else:
                self.show_error("API Test", f"❌ {result['provider']} API test failed:\n{result['error']}")
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings (public method)."""
        return self._get_current_settings()
    
    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.settings_changed