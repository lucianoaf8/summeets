#!/usr/bin/env python3
"""Results tab component for displaying and exporting processing results."""
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from pathlib import Path
from typing import Any, Dict, Optional
import queue
import json

from .base_component import BaseTabComponent
from ..constants import *


class ResultsTab(BaseTabComponent):
    """Results display and export tab component."""
    
    def __init__(self, parent_notebook: ttk.Notebook, message_queue: queue.Queue):
        # Results data
        self.transcript_data: Optional[Dict] = None
        self.summary_data: Optional[Dict] = None
        self.current_view = "transcript"  # transcript, summary
        
        # UI elements
        self.view_notebook: Optional[ttk.Notebook] = None
        self.transcript_text: Optional[scrolledtext.ScrolledText] = None
        self.summary_text: Optional[scrolledtext.ScrolledText] = None
        self.metadata_text: Optional[tk.Text] = None
        self.export_buttons_frame: Optional[ttk.Frame] = None
        
        super().__init__(parent_notebook, TAB_RESULTS, message_queue)
    
    def setup_ui(self) -> None:
        """Setup the results tab UI elements."""
        # Create main view area
        self._create_view_area()
        
        # Create metadata panel
        self._create_metadata_panel()
        
        # Create export controls
        self._create_export_section()
        
        # Initialize with empty state
        self._clear_results()
    
    def _create_view_area(self) -> None:
        """Create the main content viewing area."""
        view_section = self.create_section(self.frame, "📄 Results")
        
        # Sub-notebook for different views
        self.view_notebook = ttk.Notebook(view_section)
        self.view_notebook.pack(fill='both', expand=True, pady=DEFAULT_PADY)
        
        # Transcript tab
        transcript_frame = ttk.Frame(self.view_notebook)
        self.view_notebook.add(transcript_frame, text="🎤 Transcript")
        
        self.transcript_text = scrolledtext.ScrolledText(
            transcript_frame,
            wrap='word',
            font=INFO_FONT,
            state='disabled',
            background=COLORS['bg_secondary']
        )
        self.transcript_text.pack(fill='both', expand=True, padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        # Summary tab
        summary_frame = ttk.Frame(self.view_notebook)
        self.view_notebook.add(summary_frame, text="📝 Summary")
        
        self.summary_text = scrolledtext.ScrolledText(
            summary_frame,
            wrap='word',
            font=INFO_FONT,
            state='disabled',
            background=COLORS['bg_secondary']
        )
        self.summary_text.pack(fill='both', expand=True, padx=DEFAULT_PADX, pady=DEFAULT_PADY)
        
        # Bind tab change event
        self.view_notebook.bind('<<NotebookTabChanged>>', self._on_tab_changed)
    
    def _create_metadata_panel(self) -> None:
        """Create the metadata information panel."""
        metadata_section = self.create_section(self.frame, "ℹ️ Metadata")
        
        self.metadata_text = tk.Text(
            metadata_section,
            height=4,
            wrap='word',
            font=SECONDARY_FONT,
            state='disabled',
            background=COLORS['bg_secondary'],
            relief='flat'
        )
        self.metadata_text.pack(fill='x', pady=DEFAULT_PADY)
    
    def _create_export_section(self) -> None:
        """Create the export controls section."""
        self.export_buttons_frame = ttk.Frame(self.frame)
        self.export_buttons_frame.pack(fill='x', padx=SECTION_PADX, pady=SECTION_PADY)
        
        # Export buttons
        export_label = ttk.Label(
            self.export_buttons_frame,
            text="Export Options:",
            font=HEADING_FONT
        )
        export_label.pack(anchor='w', pady=(0, DEFAULT_PADY))
        
        # Primary export buttons
        primary_export = ttk.Frame(self.export_buttons_frame)
        primary_export.pack(fill='x', pady=DEFAULT_PADY)
        
        self.export_json_btn = ttk.Button(
            primary_export,
            text="📄 Export JSON",
            command=self._export_json,
            state='disabled'
        )
        self.export_json_btn.pack(side='left', fill='x', expand=True)
        
        self.export_srt_btn = ttk.Button(
            primary_export,
            text="🎬 Export SRT",
            command=self._export_srt,
            state='disabled'
        )
        self.export_srt_btn.pack(side='left', fill='x', expand=True, padx=(DEFAULT_PADX, 0))
        
        # Secondary export buttons
        secondary_export = ttk.Frame(self.export_buttons_frame)
        secondary_export.pack(fill='x', pady=DEFAULT_PADY)
        
        self.export_txt_btn = ttk.Button(
            secondary_export,
            text="📝 Export Text",
            command=self._export_txt,
            state='disabled'
        )
        self.export_txt_btn.pack(side='left', fill='x', expand=True)
        
        self.export_md_btn = ttk.Button(
            secondary_export,
            text="📋 Export Markdown",
            command=self._export_md,
            state='disabled'
        )
        self.export_md_btn.pack(side='left', fill='x', expand=True, padx=(DEFAULT_PADX, 0))
        
        # Utility buttons
        utility_frame = ttk.Frame(self.export_buttons_frame)
        utility_frame.pack(fill='x', pady=(SECTION_PADY, 0))
        
        ttk.Button(
            utility_frame,
            text="📋 Copy to Clipboard",
            command=self._copy_to_clipboard
        ).pack(side='left')
        
        ttk.Button(
            utility_frame,
            text="🔍 Search",
            command=self._search_content
        ).pack(side='left', padx=(DEFAULT_PADX, 0))
        
        ttk.Button(
            utility_frame,
            text="🔄 Refresh",
            command=self._refresh_display
        ).pack(side='right')
    
    def _clear_results(self) -> None:
        """Clear all results and reset UI."""
        self.transcript_data = None
        self.summary_data = None
        
        # Clear text areas
        self._update_text_widget(self.transcript_text, "No transcript available.\nProcess a media file to see results here.")
        self._update_text_widget(self.summary_text, "No summary available.\nComplete transcription and summarization to see results here.")
        self._update_text_widget(self.metadata_text, "No metadata available.")
        
        # Disable export buttons
        self._update_export_button_states(False, False)
    
    def _update_text_widget(self, widget: tk.Text, content: str) -> None:
        """Update a text widget with new content."""
        if widget:
            widget.configure(state='normal')
            widget.delete(1.0, 'end')
            widget.insert(1.0, content)
            widget.configure(state='disabled')
    
    def _on_tab_changed(self, event) -> None:
        """Handle view tab change."""
        selection = event.widget.tab('current')['text']
        if "Transcript" in selection:
            self.current_view = "transcript"
        elif "Summary" in selection:
            self.current_view = "summary"
    
    def load_transcript_results(self, transcript_data: Dict[str, Any]) -> None:
        """Load transcript results into the display."""
        self.transcript_data = transcript_data
        
        # Format transcript for display
        if 'segments' in transcript_data:
            formatted_text = self._format_transcript_for_display(transcript_data['segments'])
            self._update_text_widget(self.transcript_text, formatted_text)
        else:
            self._update_text_widget(self.transcript_text, "Transcript data format not recognized.")
        
        # Update metadata
        self._update_metadata_display()
        
        # Enable transcript export options
        self._update_export_button_states(True, bool(self.summary_data))
        
        # Notify other components
        self.send_message('transcript_loaded', {'has_transcript': True})
    
    def load_summary_results(self, summary_data: Dict[str, Any]) -> None:
        """Load summary results into the display."""
        self.summary_data = summary_data
        
        # Format summary for display
        if 'summary' in summary_data:
            formatted_text = self._format_summary_for_display(summary_data)
            self._update_text_widget(self.summary_text, formatted_text)
        else:
            self._update_text_widget(self.summary_text, "Summary data format not recognized.")
        
        # Update metadata
        self._update_metadata_display()
        
        # Enable all export options
        self._update_export_button_states(bool(self.transcript_data), True)
    
    def _format_transcript_for_display(self, segments: list) -> str:
        """Format transcript segments for display."""
        lines = []
        current_speaker = None
        
        for segment in segments:
            speaker = segment.get('speaker', 'Unknown')
            start_time = segment.get('start', 0)
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # Format timestamp
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            timestamp = TIME_FORMAT.format(0, minutes, seconds)
            
            # Add speaker header if changed
            if speaker != current_speaker:
                if lines:  # Add blank line between speakers
                    lines.append('')
                lines.append(f"🎤 {speaker} [{timestamp}]")
                lines.append('-' * 40)
                current_speaker = speaker
            
            lines.append(f"[{timestamp}] {text}")
        
        return '\n'.join(lines) if lines else "No transcript segments found."
    
    def _format_summary_for_display(self, summary_data: Dict[str, Any]) -> str:
        """Format summary data for display."""
        lines = []
        
        # Main summary
        if 'summary' in summary_data:
            lines.append("📝 MEETING SUMMARY")
            lines.append("=" * 50)
            lines.append('')
            lines.append(summary_data['summary'])
            lines.append('')
        
        # Key points if available
        if 'key_points' in summary_data:
            lines.append("🔑 KEY POINTS")
            lines.append("-" * 30)
            for i, point in enumerate(summary_data['key_points'], 1):
                lines.append(f"{i}. {point}")
            lines.append('')
        
        # Action items if available
        if 'action_items' in summary_data:
            lines.append("✅ ACTION ITEMS")
            lines.append("-" * 30)
            for i, action in enumerate(summary_data['action_items'], 1):
                lines.append(f"{i}. {action}")
            lines.append('')
        
        # Processing metadata
        if 'metadata' in summary_data:
            metadata = summary_data['metadata']
            lines.append("ℹ️ PROCESSING INFO")
            lines.append("-" * 30)
            lines.append(f"Model: {metadata.get('model', 'Unknown')}")
            lines.append(f"Provider: {metadata.get('provider', 'Unknown')}")
            if 'processing_time' in metadata:
                lines.append(f"Processing time: {metadata['processing_time']:.1f}s")
        
        return '\n'.join(lines) if lines else "No summary content found."
    
    def _update_metadata_display(self) -> None:
        """Update the metadata display."""
        metadata_lines = []
        
        # Transcript metadata
        if self.transcript_data:
            if 'metadata' in self.transcript_data:
                meta = self.transcript_data['metadata']
                metadata_lines.append(f"📁 File: {meta.get('filename', 'Unknown')}")
                if 'duration' in meta:
                    duration = int(meta['duration'])
                    mins, secs = divmod(duration, 60)
                    metadata_lines.append(f"⏱️ Duration: {mins:02d}:{secs:02d}")
                if 'file_size' in meta:
                    size_mb = meta['file_size'] / (1024 * 1024)
                    metadata_lines.append(f"📊 Size: {size_mb:.1f} MB")
            
            # Transcript statistics
            if 'segments' in self.transcript_data:
                segments = self.transcript_data['segments']
                speakers = set(seg.get('speaker', 'Unknown') for seg in segments)
                word_count = sum(len(seg.get('text', '').split()) for seg in segments)
                
                metadata_lines.append(f"🎤 Speakers: {len(speakers)}")
                metadata_lines.append(f"📝 Words: {word_count:,}")
                metadata_lines.append(f"🗣️ Segments: {len(segments)}")
        
        # Summary metadata
        if self.summary_data and 'metadata' in self.summary_data:
            meta = self.summary_data['metadata']
            if 'model' in meta:
                metadata_lines.append(f"🤖 AI Model: {meta['model']}")
            if 'processing_time' in meta:
                metadata_lines.append(f"⚡ Processing: {meta['processing_time']:.1f}s")
        
        metadata_text = '\n'.join(metadata_lines) if metadata_lines else "No metadata available."
        self._update_text_widget(self.metadata_text, metadata_text)
    
    def _update_export_button_states(self, has_transcript: bool, has_summary: bool) -> None:
        """Update export button availability."""
        # Transcript-dependent exports
        transcript_state = 'normal' if has_transcript else 'disabled'
        self.export_json_btn.configure(state=transcript_state)
        self.export_srt_btn.configure(state=transcript_state)
        self.export_txt_btn.configure(state=transcript_state)
        
        # Summary-dependent exports
        summary_state = 'normal' if has_summary else 'disabled'
        self.export_md_btn.configure(state=summary_state)
    
    def _export_json(self) -> None:
        """Export transcript as JSON."""
        if not self.transcript_data:
            self.show_error("No Data", "No transcript data available to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Transcript JSON",
            defaultextension=".json",
            filetypes=EXPORT_JSON_TYPES
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.transcript_data, f, indent=2, ensure_ascii=False)
                self.show_info("Export Successful", f"Transcript exported to:\n{filename}")
            except Exception as e:
                self.show_error("Export Failed", f"Failed to export JSON:\n{str(e)}")
    
    def _export_srt(self) -> None:
        """Export transcript as SRT subtitle file."""
        if not self.transcript_data or 'segments' not in self.transcript_data:
            self.show_error("No Data", "No transcript segments available for SRT export.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export SRT Subtitles",
            defaultextension=".srt",
            filetypes=EXPORT_SRT_TYPES
        )
        
        if filename:
            try:
                srt_content = self._generate_srt_content(self.transcript_data['segments'])
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(srt_content)
                self.show_info("Export Successful", f"SRT subtitles exported to:\n{filename}")
            except Exception as e:
                self.show_error("Export Failed", f"Failed to export SRT:\n{str(e)}")
    
    def _export_txt(self) -> None:
        """Export transcript as plain text."""
        if not self.transcript_data:
            self.show_error("No Data", "No transcript data available to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Transcript Text",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                content = self.transcript_text.get(1.0, 'end-1c')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.show_info("Export Successful", f"Text exported to:\n{filename}")
            except Exception as e:
                self.show_error("Export Failed", f"Failed to export text:\n{str(e)}")
    
    def _export_md(self) -> None:
        """Export summary as Markdown."""
        if not self.summary_data:
            self.show_error("No Data", "No summary data available to export.")
            return
        
        filename = filedialog.asksaveasfilename(
            title="Export Summary Markdown",
            defaultextension=".md",
            filetypes=EXPORT_MD_TYPES
        )
        
        if filename:
            try:
                content = self.summary_text.get(1.0, 'end-1c')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.show_info("Export Successful", f"Markdown exported to:\n{filename}")
            except Exception as e:
                self.show_error("Export Failed", f"Failed to export Markdown:\n{str(e)}")
    
    def _generate_srt_content(self, segments: list) -> str:
        """Generate SRT subtitle content from transcript segments."""
        srt_lines = []
        
        for i, segment in enumerate(segments, 1):
            start_time = segment.get('start', 0)
            end_time = segment.get('end', start_time + 2)  # Default 2s duration
            text = segment.get('text', '').strip()
            speaker = segment.get('speaker', 'Speaker')
            
            if not text:
                continue
            
            # Format timestamps for SRT
            start_srt = self._seconds_to_srt_time(start_time)
            end_srt = self._seconds_to_srt_time(end_time)
            
            # Add SRT entry
            srt_lines.append(str(i))
            srt_lines.append(f"{start_srt} --> {end_srt}")
            srt_lines.append(f"{speaker}: {text}")
            srt_lines.append('')  # Empty line between entries
        
        return '\n'.join(srt_lines)
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return SRT_TIME_FORMAT.format(hours, minutes, secs, millis)
    
    def _copy_to_clipboard(self) -> None:
        """Copy current view content to clipboard."""
        if self.current_view == "transcript" and self.transcript_text:
            content = self.transcript_text.get(1.0, 'end-1c')
        elif self.current_view == "summary" and self.summary_text:
            content = self.summary_text.get(1.0, 'end-1c')
        else:
            content = ""
        
        if content:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(content)
            self.show_info("Copied", f"{self.current_view.title()} content copied to clipboard.")
        else:
            self.show_error("No Content", f"No {self.current_view} content to copy.")
    
    def _search_content(self) -> None:
        """Open search dialog for current content."""
        # Simple implementation - could be enhanced with a proper search dialog
        from tkinter.simpledialog import askstring
        
        search_term = askstring("Search", "Enter search term:")
        if search_term:
            widget = self.transcript_text if self.current_view == "transcript" else self.summary_text
            if widget:
                content = widget.get(1.0, 'end-1c')
                count = content.lower().count(search_term.lower())
                self.show_info("Search Results", f"Found '{search_term}' {count} time(s) in {self.current_view}.")
    
    def _refresh_display(self) -> None:
        """Refresh the current display."""
        if self.transcript_data:
            self.load_transcript_results(self.transcript_data)
        if self.summary_data:
            self.load_summary_results(self.summary_data)
    
    def update_state(self, state: Dict[str, Any]) -> None:
        """Update component state based on external changes."""
        if 'transcript_results' in state:
            self.load_transcript_results(state['transcript_results'])
        
        if 'summary_results' in state:
            self.load_summary_results(state['summary_results'])
        
        if 'clear_results' in state:
            self._clear_results()
    
    def has_results(self) -> Dict[str, bool]:
        """Check what results are currently available."""
        return {
            'has_transcript': bool(self.transcript_data),
            'has_summary': bool(self.summary_data)
        }