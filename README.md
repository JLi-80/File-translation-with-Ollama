# Ollama Translator

Ollama Translator is a tool that uses local Ollama models to translate text into specified languages. It supports translation between multiple languages while preserving document formatting.

## Features

- Translate text files while preserving original formatting (HTML, Markdown, LaTeX, etc.)
- Support for multiple translation languages
- Graphical user interface for easy operation
- Configurable translation parameters
- Progress tracking during translation process

## Project Structure

```
ollama_translator/
├── translate_with_ollama.py  # Main program
├── ollama_client.py          # Ollama API client module
├── text_slicer.py            # Text slicing module
├── gui.py                    # Graphical user interface
├── settings.json             # Configuration file
└── README.md                 # Project documentation
```

## Requirements

- Python 3.x
- Ollama service running locally
- Required Python packages:
  - `requests`: HTTP library
  - `tqdm`: Progress bar display
  - `nltk`: Natural language processing toolkit
  - `customtkinter`: GUI framework (for GUI only)

Install dependencies:
```bash
pip install requests tqdm nltk customtkinter
```

## Configuration

The tool uses `settings.json` to manage configuration parameters. Key settings include:

### Ollama Settings
- `url`: Ollama API address (default: http://localhost:11434/api/generate)
- `model_name`: Model name to use for translation
- `temperature`: Controls randomness of output (0.0-1.0)
- `timeout`: Request timeout in seconds

### Translation Settings
- `target_language`: Target language for translation (e.g., "English", "simplified Chinese")
- `target_tokens_per_slice`: Maximum tokens per text slice (default 1024)

### General Settings
- `skip_connection_test`: Skip Ollama connection test at startup

## Usage

### Command Line Interface

1. Ensure Ollama service is running
2. Modify `settings.json` according to your needs
3. Run the translation program:
   ```bash
   python translate_with_ollama.py input.txt
   ```

The translated file will be saved as `{original_filename}-translated.{extension}` in the same directory.

### Graphical User Interface

A graphical user interface is available for easier operation:

1. Install the required GUI package:
   ```bash
   pip install customtkinter
   ```

2. Run the GUI application:
   ```bash
   python gui.py
   ```

GUI features:
- File selection with browse dialog
- Tabbed interface for all settings
- Real-time progress tracking with visual progress bar
- Detailed log output
- One-click translation

## Supported File Types

The tool reads files as UTF-8 text and supports various formats:
- Plain text (.txt)
- Markdown (.md, .markdown)
- HTML (.html, .htm, .xhtml)
- LaTeX (.tex, .latex)
- XML (.xml)
- Subtitles (.srt, .vtt)
- And other text-based formats

## Language Support

The translation language can be configured in `settings.json`. Supported languages depend on the Ollama model being used, including but not limited to:
- English
- Simplified Chinese
- Japanese
- Korean
- French
- German
- Spanish
- Italian
- Portuguese
- Russian

To change the target language, modify the `target_language` parameter in `settings.json`:
```json
{
    "translation": {
        "target_language": "English"
    }
}
```

