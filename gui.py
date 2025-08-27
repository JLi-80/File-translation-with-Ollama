#!/usr/bin/env python3
"""
GUI for Ollama Translator
A graphical interface for the Ollama translation tool using CustomTkinter
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import os
from pathlib import Path
import sys
import threading
import queue
import subprocess
import re
import time

# Add the project root to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from translate_with_ollama import main as translate_main, SETTINGS as translation_settings
from ollama_client import load_ollama_config, create_ollama_client


class OllamaTranslatorGUI:
    def __init__(self):
        # Initialize the main window
        self.root = ctk.CTk()
        self.root.title("Ollama Translator")
        
        # Configure the grid layout
        self.root.grid_columnconfigure(0, weight=1)
        # Do not set weight for row 1 initially to allow natural sizing
        
        # Variables to store settings
        self.settings_file = Path(__file__).parent / "settings.json"
        self.settings = self.load_settings()
        
        # Variables to store file paths
        self.input_file_path = ctk.StringVar()
        self.output_file_path = ctk.StringVar()
        
        # Queue for handling log messages
        self.log_queue = queue.Queue()
        
        # Process variable
        self.translation_process = None
        
        # Create the UI
        self.create_widgets()
        
        # Load initial settings into the UI
        self.load_settings_to_ui()
        
        # Start checking for log messages
        self.check_log_queue()
        
        # Update the window size to fit all widgets with minimal size
        # but limit to half of screen height
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Limit window height to half of screen height
        max_height = screen_height * 0.7
        if height > max_height:
            height = max_height
            
        # Also ensure window isn't wider than screen
        if width > screen_width:
            width = screen_width
            
        self.root.minsize(width, height)
        self.root.geometry(f"{width}x{height}")
    
    def load_settings(self):
        """
        Load settings from the settings.json file
        """
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not read config file {self.settings_file}: {e}", file=sys.stderr)
        
        # Default settings
        return {
            "ollama": {
                "url": "http://localhost:11434/api/generate",
                "model_name": "gemma3:latest",
                "temperature": 0.1,
                "top_p": 0.9,
                "repeat_penalty": 1.2,
                "timeout": 240,
                "retries": 3
            },
            "translation": {
                "target_tokens_per_slice": 1024,
                "target_language": "simplified Chinese",
                "system_prompt": "You are a professional translator. Translate the following text into natural, fluent {target_language} if it's not already in {target_language}. DO NOT translate or remove any formating tags, including HTML/markdown/latex tags such as <table>, <figure>, <equation>, <reference>, etc. DO NOT translate people names, acronyms, equations, hyperlinks, or references. Return ONLY the {target_language} translation, do not include any thinking/reasoning, explanation or note.",
                "para_sep": "<段落分隔符>"
            },
            "general": {
                "skip_connection_test": False
            }
        }
    
    def save_settings(self):
        """
        Save settings to the settings.json file
        """
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
            return False
    
    def create_widgets(self):
        """
        Create all the UI widgets
        """
        # Create header frame
        header_frame = ctk.CTkFrame(self.root)
        header_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(header_frame, text="Ollama Translator", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)
        
        # File selection frame
        file_frame = ctk.CTkFrame(self.root)
        file_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")
        file_frame.grid_columnconfigure(1, weight=1)
        
        # Input file selection
        input_label = ctk.CTkLabel(file_frame, text="Input File:")
        input_label.grid(row=0, column=0, padx=(5, 2), pady=5, sticky="w")
        
        input_entry = ctk.CTkEntry(file_frame, textvariable=self.input_file_path)
        input_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
        
        input_button = ctk.CTkButton(file_frame, text="Browse", command=self.browse_input_file, width=80)
        input_button.grid(row=0, column=2, padx=(2, 5), pady=5)
        
        # Output file (will be automatically determined)
        output_label = ctk.CTkLabel(file_frame, text="Output File:")
        output_label.grid(row=1, column=0, padx=(5, 2), pady=(0, 5), sticky="w")
        
        output_entry = ctk.CTkEntry(file_frame, textvariable=self.output_file_path, state="readonly")
        output_entry.grid(row=1, column=1, padx=2, pady=(0, 5), sticky="ew")
        
        # Progress bar
        progress_frame = ctk.CTkFrame(self.root)
        progress_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_label = ctk.CTkLabel(progress_frame, text="Progress: 0%")
        self.progress_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0.0)  # Initialize to 0%
        
        # Notebook for settings tabs
        notebook = ctk.CTkTabview(self.root)
        notebook.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        self.root.grid_rowconfigure(3, weight=1)
        
        # Make sure notebook expands properly
        notebook.grid_columnconfigure(0, weight=1)
        notebook.grid_rowconfigure(0, weight=1)
        
        # Ollama settings tab
        ollama_tab = notebook.add("Ollama Settings")
        ollama_tab.grid_columnconfigure(1, weight=1)
        ollama_tab.grid_rowconfigure(7, weight=1)  # Add empty row to push content to top
        
        # Ollama URL
        url_label = ctk.CTkLabel(ollama_tab, text="Ollama URL:")
        url_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.url_entry = ctk.CTkEntry(ollama_tab)
        self.url_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Model name
        model_label = ctk.CTkLabel(ollama_tab, text="Model Name:")
        model_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.model_entry = ctk.CTkEntry(ollama_tab)
        self.model_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Temperature
        temp_label = ctk.CTkLabel(ollama_tab, text="Temperature:")
        temp_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.temp_entry = ctk.CTkEntry(ollama_tab)
        self.temp_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Top P
        top_p_label = ctk.CTkLabel(ollama_tab, text="Top P:")
        top_p_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.top_p_entry = ctk.CTkEntry(ollama_tab)
        self.top_p_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Repeat penalty
        repeat_label = ctk.CTkLabel(ollama_tab, text="Repeat Penalty:")
        repeat_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")
        
        self.repeat_entry = ctk.CTkEntry(ollama_tab)
        self.repeat_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Timeout
        timeout_label = ctk.CTkLabel(ollama_tab, text="Timeout (seconds):")
        timeout_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")
        
        self.timeout_entry = ctk.CTkEntry(ollama_tab)
        self.timeout_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        # Retries
        retries_label = ctk.CTkLabel(ollama_tab, text="Retries:")
        retries_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
        
        self.retries_entry = ctk.CTkEntry(ollama_tab)
        self.retries_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        # Translation settings tab
        translation_tab = notebook.add("Translation Settings")
        translation_tab.grid_columnconfigure(1, weight=1)
        translation_tab.grid_rowconfigure(4, weight=1)  # Add empty row to push content to top
        
        # Target language
        lang_label = ctk.CTkLabel(translation_tab, text="Target Language:")
        lang_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.lang_entry = ctk.CTkEntry(translation_tab)
        self.lang_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Tokens per slice
        tokens_label = ctk.CTkLabel(translation_tab, text="Tokens per Slice:")
        tokens_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.tokens_entry = ctk.CTkEntry(translation_tab)
        self.tokens_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Paragraph separator
        sep_label = ctk.CTkLabel(translation_tab, text="Paragraph Separator:")
        sep_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.sep_entry = ctk.CTkEntry(translation_tab)
        self.sep_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # System prompt
        prompt_label = ctk.CTkLabel(translation_tab, text="System Prompt:")
        prompt_label.grid(row=3, column=0, padx=10, pady=5, sticky="nw")
        
        self.prompt_text = ctk.CTkTextbox(translation_tab, height=100)
        self.prompt_text.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # General settings tab
        general_tab = notebook.add("General Settings")
        general_tab.grid_columnconfigure(0, weight=1)
        general_tab.grid_rowconfigure(1, weight=1)  # Add empty row to push content to top
        
        # Skip connection test
        self.skip_test_var = ctk.BooleanVar()
        skip_test_check = ctk.CTkCheckBox(
            general_tab, 
            text="Skip Connection Test", 
            variable=self.skip_test_var
        )
        skip_test_check.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Progress and log area
        progress_frame = ctk.CTkFrame(self.root)
        progress_frame.grid(row=4, column=0, padx=10, pady=5, sticky="nsew")
        progress_frame.grid_columnconfigure(0, weight=1)
        progress_frame.grid_rowconfigure(1, weight=1)
        
        progress_label = ctk.CTkLabel(progress_frame, text="Progress & Logs:")
        progress_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.progress_text = ctk.CTkTextbox(progress_frame, height=100)
        self.progress_text.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 5), sticky="nsew")
        self.progress_text.configure(state="disabled")
        
        clear_log_button = ctk.CTkButton(progress_frame, text="Clear Log", command=self.clear_log, width=80)
        clear_log_button.grid(row=0, column=1, padx=5, pady=5, sticky="e")
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.root)
        buttons_frame.grid(row=5, column=0, padx=10, pady=(5, 10), sticky="ew")
        buttons_frame.grid_columnconfigure((0, 1), weight=1)
        
        # Save settings button
        save_button = ctk.CTkButton(buttons_frame, text="Save Settings", command=self.save_settings_to_file)
        save_button.grid(row=0, column=0, padx=10, pady=10, sticky="e")
        
        # Translate button
        translate_button = ctk.CTkButton(buttons_frame, text="Translate", command=self.translate_file, fg_color="green")
        translate_button.grid(row=0, column=1, padx=10, pady=10, sticky="w")
    
    def load_settings_to_ui(self):
        """
        Load settings into the UI elements
        """
        # Ollama settings
        self.url_entry.insert(0, self.settings["ollama"]["url"])
        self.model_entry.insert(0, self.settings["ollama"]["model_name"])
        self.temp_entry.insert(0, str(self.settings["ollama"]["temperature"]))
        self.top_p_entry.insert(0, str(self.settings["ollama"]["top_p"]))
        self.repeat_entry.insert(0, str(self.settings["ollama"]["repeat_penalty"]))
        self.timeout_entry.insert(0, str(self.settings["ollama"]["timeout"]))
        self.retries_entry.insert(0, str(self.settings["ollama"]["retries"]))
        
        # Translation settings
        self.lang_entry.insert(0, self.settings["translation"]["target_language"])
        self.tokens_entry.insert(0, str(self.settings["translation"]["target_tokens_per_slice"]))
        self.sep_entry.insert(0, self.settings["translation"]["para_sep"])
        self.prompt_text.insert("0.0", self.settings["translation"]["system_prompt"])
        
        # General settings
        self.skip_test_var.set(self.settings["general"]["skip_connection_test"])
    
    def save_settings_from_ui(self):
        """
        Save settings from UI elements to the settings dictionary
        """
        # Ollama settings
        self.settings["ollama"]["url"] = self.url_entry.get()
        self.settings["ollama"]["model_name"] = self.model_entry.get()
        self.settings["ollama"]["temperature"] = float(self.temp_entry.get())
        self.settings["ollama"]["top_p"] = float(self.top_p_entry.get())
        self.settings["ollama"]["repeat_penalty"] = float(self.repeat_entry.get())
        self.settings["ollama"]["timeout"] = int(self.timeout_entry.get())
        self.settings["ollama"]["retries"] = int(self.retries_entry.get())
        
        # Translation settings
        self.settings["translation"]["target_language"] = self.lang_entry.get()
        self.settings["translation"]["target_tokens_per_slice"] = int(self.tokens_entry.get())
        self.settings["translation"]["para_sep"] = self.sep_entry.get()
        self.settings["translation"]["system_prompt"] = self.prompt_text.get("0.0", "end")
        
        # General settings
        self.settings["general"]["skip_connection_test"] = self.skip_test_var.get()
    
    def save_settings_to_file(self):
        """
        Save settings to file
        """
        self.save_settings_from_ui()
        if self.save_settings():
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.append_log("Settings saved successfully!\n")
    
    def browse_input_file(self):
        """
        Open file dialog to select input file
        """
        file_path = filedialog.askopenfilename(
            title="Select file to translate",
            filetypes=[
                ("Text files", "*.txt"),
                ("Markdown files", "*.md *.markdown"),
                ("HTML files", "*.html *.htm *.xhtml"),
                ("LaTeX files", "*.tex *.latex"),
                ("XML files", "*.xml"),
                ("Subtitle files", "*.srt *.vtt"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            self.input_file_path.set(file_path)
            # Set output file path
            input_path = Path(file_path)
            output_path = input_path.with_stem(input_path.stem + "-translated")
            self.output_file_path.set(str(output_path))
    
    def append_log(self, message):
        """
        Append message to the progress log area
        """
        # Debugging: Show raw message being added to log
        self.progress_text.configure(state="normal")
        debug_message = f"[LOG] {message}"
        self.progress_text.insert("end", debug_message)
        self.progress_text.configure(state="disabled")
        self.progress_text.see("end")  # Auto-scroll to the end
    
    def check_log_queue(self):
        """
        Check for messages in the log queue and display them
        """
        try:
            while True:
                message = self.log_queue.get_nowait()
                # Debugging: Show that we've received a message
                print(f"[DEBUG] Processing queue message: {message.strip()}")  # Will show in terminal/console
                self.append_log(message)
                # Try to extract progress information from the message
                self.update_progress_from_message(message)
        except queue.Empty:
            pass
        
        # Check again after 100ms
        self.root.after(100, self.check_log_queue)
    
    def update_progress_from_message(self, message):
        """
        Extract progress information from log messages and update the progress bar
        """
        try:
            # Look for our custom progress pattern like "Translating: 50% complete (25/50 slices)"
            match = re.search(r"Translating:\s*(\d+)%.*complete.*?\((\d+)/(\d+)\s+slices\)", message)
            if match:
                progress = int(match.group(1))
                current = int(match.group(2))
                total = int(match.group(3))
                
                # Update the progress bar and label
                self.progress_bar.set(progress / 100.0)
                self.progress_label.configure(text=f"Progress: {progress}%")
                
                # Force update the GUI to ensure changes are visible
                self.root.update_idletasks()
                return
            
            # Check for start and completion messages
            if "Starting translation process" in message:
                self.progress_bar.set(0.0)
                self.progress_label.configure(text="Progress: 0%")
            elif "Translation completed" in message or "translation completed" in message:
                self.progress_bar.set(1.0)
                self.progress_label.configure(text="Progress: 100%")
            elif "Generated" in message and "slices" in message:
                # This message indicates we're about to start the translation loop
                self.progress_bar.set(0.0)
                self.progress_label.configure(text="Progress: 0%")
        except Exception as e:
            # Silently ignore parsing errors to prevent GUI crashes
            pass

    def clear_log(self):
        """
        Clear the progress log area
        """
        self.progress_text.configure(state="normal")
        self.progress_text.delete("0.0", "end")
        self.progress_text.configure(state="disabled")
    
    def translate_file(self):
        """
        Translate the selected file
        """
        if not self.input_file_path.get():
            messagebox.showerror("Error", "Please select an input file first!")
            return
        
        # Save current settings
        self.save_settings_from_ui()
        if not self.save_settings():
            messagebox.showerror("Error", "Failed to save settings!")
            return
        
        # Run translation in a separate thread to avoid blocking the UI
        translation_thread = threading.Thread(target=self._run_translation_subprocess)
        translation_thread.daemon = True
        translation_thread.start()

    def _run_translation_subprocess(self):
        """
        Run the translation process as a subprocess to get real-time output
        """
        try:
            self.log_queue.put("Starting translation process...\n")
            
            # Get the directory of the current script
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_path = os.path.join(script_dir, "translate_with_ollama.py")
            input_file = self.input_file_path.get()
            
            # Build the command
            cmd = [sys.executable, script_path, input_file]
            
            # Start the subprocess with line buffered output
            self.translation_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'  # Handle encoding errors gracefully
            )
            
            # Function to read output from a stream
            def read_stream(stream, stream_name):
                while True:
                    try:
                        line = stream.readline()
                        if line:
                            self.log_queue.put(line)
                            # Check if this line contains progress info
                            self.update_progress_from_message(line)
                        elif self.translation_process.poll() is not None:
                            break
                    except Exception as e:
                        # Handle any reading errors gracefully
                        error_msg = f"Error reading {stream_name}: {str(e)}\n"
                        self.log_queue.put(error_msg)
                        if self.translation_process.poll() is not None:
                            break
            
            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(target=read_stream, args=(self.translation_process.stdout, "stdout"))
            stderr_thread = threading.Thread(target=read_stream, args=(self.translation_process.stderr, "stderr"))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for the process to complete
            while self.translation_process.poll() is None:
                time.sleep(0.1)
            
            # Wait for threads to finish reading
            stdout_thread.join(timeout=1)
            stderr_thread.join(timeout=1)
            
            # Get the return code
            return_code = self.translation_process.poll()
            
            if return_code == 0:
                success_message = f"Translation completed!\nOutput file: {self.output_file_path.get()}\n"
                self.log_queue.put(success_message)
                self.root.after(0, lambda: messagebox.showinfo("Success", success_message))
            else:
                error_message = f"Translation failed with return code: {return_code}\n"
                self.log_queue.put(error_message)
                self.root.after(0, lambda: messagebox.showerror("Error", error_message))
                
        except Exception as e:
            error_message = f"Translation failed: {str(e)}\n"
            self.log_queue.put(error_message)
            self.root.after(0, lambda: messagebox.showerror("Error", error_message))
        finally:
            self.translation_process = None
    
    def run(self):
        """
        Run the GUI application
        """
        self.root.mainloop()




if __name__ == "__main__":
    app = OllamaTranslatorGUI()
    app.run()