from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Input, Label, Static, Select, TextArea
from textual.reactive import reactive
from pathlib import Path
import asyncio

from core.transcribe import transcribe_audio
from core.summarize import summarize_transcript
from core.fsio import get_data_manager

class SummeetsApp(App):
    """Summeets GUI - Audio transcription and summarization."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    Container {
        width: 90%;
        height: auto;
        padding: 1;
    }
    
    #main-container {
        height: 100%;
    }
    
    .section {
        border: solid green;
        padding: 1;
        margin: 1;
    }
    
    #status {
        height: 5;
        border: solid blue;
        padding: 1;
    }
    
    Input {
        margin: 1 0;
    }
    
    Button {
        margin: 1 0;
        width: 100%;
    }
    
    Select {
        margin: 1 0;
        width: 100%;
    }
    """
    
    def compose(self) -> ComposeResult:
        yield Header()
        
        with Container(id="main-container"):
            
            with Vertical(classes="section"):
                yield Label("📝 Transcription", classes="title")
                yield Label("Audio file or directory:")
                self.trans_input = Input(placeholder="/path/to/audio or /audio/folder")
                yield self.trans_input
                yield Button("Transcribe", id="transcribe", variant="success")
            
            with Vertical(classes="section"):
                yield Label("📊 Summarization", classes="title")
                yield Label("Transcript JSON:")
                self.summary_input = Input(placeholder="/path/to/transcript.json")
                yield self.summary_input
                
                yield Label("Provider:")
                self.provider_select = Select(
                    [("openai", "OpenAI"), ("anthropic", "Anthropic")],
                    value="openai"
                )
                yield self.provider_select
                
                yield Button("Summarize", id="summarize", variant="success")
            
            yield Static("Ready", id="status")
        
        yield Footer()
    
    def update_status(self, message: str, success: bool = True):
        """Update status message."""
        status = self.query_one("#status", Static)
        if success:
            status.update(f"✅ {message}")
        else:
            status.update(f"❌ {message}")
    
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        button_id = event.button.id
        
        try:
            if button_id == "transcribe":
                audio_path = self.trans_input.value
                if not audio_path:
                    self.update_status("Please provide audio path", False)
                    return
                
                self.update_status("Transcribing audio (this may take a while)...")
                json_path, srt_path, audit_path = await asyncio.to_thread(
                    transcribe_audio, 
                    Path(audio_path) if audio_path else None
                )
                self.update_status(f"Transcription complete: {json_path}")
                # Auto-fill summary input
                self.summary_input.value = str(json_path)
            
            elif button_id == "summarize":
                transcript = self.summary_input.value
                if not transcript:
                    self.update_status("Please provide transcript path", False)
                    return
                
                provider = self.provider_select.value
                self.update_status(f"Summarizing with {provider}...")
                md_path, json_path = await asyncio.to_thread(
                    summarize_transcript,
                    Path(transcript),
                    provider=provider
                )
                self.update_status(f"Summary complete: {md_path}")
        
        except Exception as e:
            self.update_status(f"Error: {str(e)}", False)

def main():
    app = SummeetsApp()
    app.run()

if __name__ == "__main__":
    main()