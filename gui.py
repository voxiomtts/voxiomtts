# -*- coding: utf-8 -*-
import os
import sys
import time
import json
import torch
import numpy as np
import threading
import traceback
import inspect
import hashlib
import webbrowser
from pathlib import Path
from PIL import Image  # For PNG loading/resizing
import customtkinter as ctk
# from tkinter import PhotoImage
from tkinter import simpledialog
from tkinter import ttk, filedialog
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from download_models import ModelUpdater, get_available_models # MUSE
from tts_engine import SileroTTS
import sounddevice as sd
import soundfile as sf

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0

        # Bind events
        self.widget.bind("<Enter>", self.showtip)
        self.widget.bind("<Leave>", self.hidetip)
        self.widget.bind("<ButtonPress>", self.hidetip)

    def showtip(self, event=None):
        """Display text in tooltip window"""
        if self.tip_window or not self.text:
            return

        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25

        self.tip_window = ctk.CTkToplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        label = ctk.CTkLabel(
            self.tip_window,
            text=self.text,
            justify="left",
            fg_color="#ffffe0",
            text_color="#000000",
            corner_radius=3,
            padx=5,
            pady=5
        )
        label.pack()

    def hidetip(self, event=None):
        """Destroy tooltip window"""
        if self.tip_window:
            self.tip_window.destroy()
        self.tip_window = None

class IconManager:
    def __init__(self, assets_dir="assets/icons"):
        self.assets_dir = Path(assets_dir)
        self._cache = {}
        self._dark_mode = True  # Default to dark mode

    def set_dark_mode(self, is_dark: bool):
        """Update mode and clear cache when theme changes"""
        if self._dark_mode != is_dark:
            self._dark_mode = is_dark
            self._cache.clear()

    def get(self, icon_name: str, size=(24, 24)) -> ctk.CTkImage:
        """Load theme-appropriate icon with fallbacks"""
        mapped_name = self._map_icon_name(icon_name)

        # Try theme-specific version first
        theme_suffix = "-dark" if self._dark_mode else ""
        themed_name = f"{icon_name}{theme_suffix}"

        # Try all possible variations
        for name in [themed_name, icon_name]:
            try:
                img_path = self.assets_dir / f"{name}.png"
                if img_path.exists():
                    with Image.open(img_path) as img:
                        img = img.resize(size, Image.Resampling.LANCZOS)
                        return ctk.CTkImage(
                            light_image=img,
                            dark_image=img,
                            size=size
                        )
            except:
                continue

        # Fallback to simple colored circle
        return self._get_fallback_icon(size, "red")

    # Add this to your IconManager class
    def _map_icon_name(self, icon_name):
        """Map standard icon names to your actual filenames"""
        icon_map = {
            'play': 'play',
            'stop': 'stop',
            'save': 'save',
            'check': 'verify',
            'error': 'warning',
            'loading': 'update',
            'export': 'export',
            'synth': 'synth'
        }
        return icon_map.get(icon_name, icon_name)

    def _get_fallback_icon(self, size, color):
        """Create a simple fallback icon"""
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0, 0), size], fill=color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

class VoxiomTTSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # === Phase 1: Core Setup ===
        # 1. Initialize paths and directories
        self.base_dir = Path(__file__).parent
        self.models_dir = self.base_dir / "models" / "tts"
        self.assets_dir = self.base_dir / "assets"
        self.icons_dir = self.assets_dir / "icons"
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 2. Initialize theme and appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # === Phase 2: Manager Setup ===
        # 3. Initialize IconManager with proper dark mode
        self.icons = IconManager(self.icons_dir)
        self.icons.set_dark_mode(True)

        # 4. Initialize tooltips collection
        self.tooltips = []  # Will store active tooltip references
        self._setup_icon_theming()  # Add this after icon manager setup

        # === Phase 3: Window Configuration ===
        # 5. Configure main window properties
        self.title("Voxiom TTS GUI")
        self.geometry("1000x1000")
        self.minsize(1000, 1000)
        self._setup_icon()  # Sets window icon using IconManager

        # === Phase 4: State Initialization ===
        # 6. Initialize all application state variables
        self._setup_attributes()  # Sets up self.debug_mode, audio_data, etc.
        self._setup_methods()     # Ensures all methods exist

        # === Phase 5: TTS Engine ===
        # 7. Initialize TTS engine with proper error handling
        self._setup_tts()
        self._verify_models_with_checksum()

        # === Phase 6: UI Construction ===
        # 8. Build the user interface
        self._create_ui()  # Creates all tabs, controls, and status bar

        # === Phase 7: Final Initialization ===
        # 9. Load initial data
        if self.available_models:
            self._load_model(self.available_models[0])
            self._update_presets_for_model(self.available_models[0])

        # 10. Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 11. Load initial model and presets
        if self.available_models:
            initial_model = self.available_models[0]
            self._load_model(initial_model)
            self._update_presets_for_model(initial_model)  # This will properly initialize presets
            self._load_first_preset_in_category(self.category_var.get())  # Load first preset in category

        # 12. Initial debug output if enabled
        if self.debug_mode:
            self._debug_state()
            print("Initialization complete")

    @property
    def presets(self):
        """Get presets from TTS engine or return empty dict"""
        if hasattr(self, 'tts') and hasattr(self.tts, 'presets'):
            return self.tts.presets
        return self._presets

    @presets.setter
    def presets(self, value):
        """Set presets and update UI if available"""
        self._presets = value or {}
        if hasattr(self, 'category_menu'):
            self.category_menu.configure(values=list(self._presets.keys()))
            if self._presets:
                self.category_var.set(next(iter(self._presets.keys())))
                self._update_preset_options()

    def _setup_methods(self):
        """Ensure all methods exist before they're called"""
        self._debug_state = self._create_debug_state()

    def _create_debug_state(self):
        """Factory method to create debug function"""
        def debug_state():
            print("\n=== Current Application State ===")
            print(f"TTS Engine Ready: {hasattr(self, 'tts')}")
            if hasattr(self, 'tts'):
                print(f"Loaded Models: {getattr(self.tts, 'models', {}).keys()}")
                print(f"Current Model: {getattr(self.tts, 'current_model', 'None')}")
            print(f"Presets Loaded: {len(getattr(self, 'presets', {}))} categories")
            print(f"UI Components Ready: {hasattr(self, 'voice_menu')}")
            print("===============================\n")
        return debug_state

    def _debug_ui_state(self):
        print("\n=== UI State ===")
        print(f"Model CB: {self.model_var.get()}")
        print(f"Category CB: {self.category_var.get()}")
        print(f"Preset CB: {self.preset_var.get()}")
        print(f"Voice CB: {self.voice_var.get()}")
        print(f"Sample Rate: {self.sample_rate_var.get()}")
        print("================")

        # 3. Add helper method for SSML mode check:
    def _is_ssml_mode(self):
        """
        Check if SSML should be used by verifying both:
        1. If the current model supports SSML
        2. If the current text is formatted as SSML
        """
        # First check model support
        model_name = self.model_var.get()
        model_supports_ssml = False
        if model_name in self.supported_models:
            model_supports_ssml = self.supported_models[model_name].get("supports_ssml", False)

        # Then check text format
        text = self.text_input.get("1.0", "end-1c").strip()
        text_is_ssml = text.startswith('<speak>') and text.endswith('</speak>')

        # Only use SSML if both conditions are met
        return model_supports_ssml and text_is_ssml

    def _should_wrap_ssml(self):
        """
        Check if text should be automatically wrapped in SSML tags.
        Returns True when:
        - Model supports SSML
        - Text isn't already SSML
        - Current category suggests SSML (e.g., "Russian SSML")
        """
        model_name = self.model_var.get()
        if model_name not in self.supported_models:
            return False

        category = self.category_var.get()
        if not category:
            return False

        model_supports_ssml = self.supported_models[model_name].get("supports_ssml", False)
        text = self.text_input.get("1.0", "end-1c").strip()
        text_is_ssml = text.startswith('<speak>') and text.endswith('</speak>')

        return (model_supports_ssml and
                not text_is_ssml and
                'ssml' in category.lower())

    def _create_loader_animation(self):
        self.loader_frames = self.icons.get_loader_frames((24, 24))
        self.loader_label = ctk.CTkLabel(master=frame, image=self.loader_frames[0])
        self._animate_loader(0)

    def _animate_loader(self, frame_idx):
        self.loader_label.configure(image=self.loader_frames[frame_idx])
        self.after(100, lambda: self._animate_loader((frame_idx + 1) % 7))

    def _update_button_states(self):
        # Example for play/pause toggle
        icon = "stop" if self.is_playing else "play"
        self.play_btn.configure(image=self.icons.get(icon, (16, 16)))

        # Disabled state example
        self.export_btn.configure(
            state="normal" if self.audio_data else "disabled",
            image=self.icons.get("export", (16, 16))
        )

    def _setup_icon_theming(self):
        """Preload and theme essential icons"""
        # Preload common icons
        for icon in ["play", "stop", "pause", "export", "save", "synth"]:
            self.icons.get(icon)

        # Set initial icons for buttons
        if hasattr(self, 'play_btn'):
            self.play_btn.configure(image=self.icons.get("play", (16, 16)))
        if hasattr(self, 'export_btn'):
            self.export_btn.configure(image=self.icons.get("export", (16, 16)))

        """Debug icon loading"""
        print(f"Icon directory: {self.icons_dir}")
        print("Available icons:")
        for f in self.icons_dir.glob('*.png'):
            print(f" - {f.name}")

        # Test load a common icon
        test_icon = self.icons.get("play", (16,16))
        if test_icon:
            print("Successfully loaded test icon")
        else:
            print("Failed to load test icon")

    def _setup_icon(self):
        """Safe cross-platform icon setup with fallbacks"""
        base_dir = Path(__file__).parent
        icon_path = base_dir / 'assets' / 'voxiom.ico'
        png_path = base_dir / 'assets' / 'voxiom256.png'

        try:
            # Try Windows .ico first
            if sys.platform == 'win32':
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Voxiom.TTS.GUI')
                self.iconbitmap(str(icon_path))
                return
        except Exception:
            pass

        # Fallback to PNG
        try:
            with Image.open(png_path) as img:
                photo = ctk.CTkImage(img)
                self.tk.call('wm', 'iconphoto', self._w, photo)
        except Exception as e:
            print(f"Could not load any icon: {e}")

    def _preload_icons(self):
        for icon in ["play", "stop", "error", "warning"]:
            self.icons.get(icon)  # Force cache

    # In your main app class:
    def _setup_dark_theme(self):
        """Configure dark theme and update icons"""
        ctk.set_appearance_mode("dark" if self._dark_mode else "light")
        self.icons.set_dark_mode(self._dark_mode)
        self._update_ui_icons()  # Refresh all icons

    def _update_ui_icons(self):
        """Refresh all icons in the UI to match current theme and state"""
        try:
            # Update status bar icon
            if hasattr(self, 'status_icon'):
                current_status = "ready"  # Default
                if hasattr(self, 'status_var'):
                    status_text = self.status_var.get().lower()
                    if "error" in status_text:
                        current_status = "error"
                    elif "working" in status_text or "processing" in status_text:
                        current_status = "working"
                    elif "warning" in status_text:
                        current_status = "warning"

                self.status_icon.configure(image=self.status_icons.get(current_status, self.status_icons["ready"]))

            # Update control buttons
            if hasattr(self, 'play_btn'):
                icon = "stop" if getattr(self, 'is_playing', False) else "play"
                self.play_btn.configure(image=self.icons.get(icon, (16, 16)))

            if hasattr(self, 'export_btn'):
                self.export_btn.configure(image=self.icons.get("export", (16, 16)))

            if hasattr(self, 'save_btn'):
                self.save_btn.configure(image=self.icons.get("save", (16, 16)))

            if hasattr(self, 'synth_btn'):
                self.synth_btn.configure(image=self.icons.get("synth", (16, 16)))

            # Update model management buttons
            if hasattr(self, 'update_btn'):
                self.update_btn.configure(image=self.icons.get("update", (16, 16)))

            if hasattr(self, 'check_btn'):
                self.check_btn.configure(image=self.icons.get("verify", (16, 16)))

            if hasattr(self, 'download_btn'):
                self.download_btn.configure(image=self.icons.get("download", (16, 16)))

            # Update collapsible section arrows
            if hasattr(self, 'toggle_btn'):
                icon = "arrow-down" if getattr(self, 'section_content', None) and self.section_content.winfo_ismapped() else "arrow-right"
                self.toggle_btn.configure(image=self.icons.get_arrow_icon(icon.split('-')[-1], (11, 11)))

            # Update any other dynamic icons
            if hasattr(self, 'status_icons'):
                # Refresh status icons in case theme changed
                self.status_icons = {
                    "ready": self.icons.get("verify", (16, 16)),
                    "error": self.icons.get("warning", (16, 16)),
                    "working": self.icons.get("update", (16, 16)),
                    "warning": self.icons.get("warning", (16, 16))
                }

        except Exception as e:
            print(f"Error updating UI icons: {e}")
            # Fallback to ensure basic functionality
            if hasattr(self, 'status_var'):
                self.status_var.set("Icon update failed")

    def _setup_attributes(self):
        """Initialize all class attributes with checksums"""
        self.debug_mode = True
        self.dark_bg = "#1e1e1e"
        self.dark_frame = "#2d2d2d"
        self.dark_text = "#ffffff"
        self.active_tab_color = "#3a3a3a"

        # State variables
        self._presets = {}
        self.audio_data = None
        self.playback_start_time = None
        self.is_playing = False
        self.available_models = []
        self.tooltips = []

        # Tkinter variables
        self.model_var = ctk.StringVar()
        self.voice_var = ctk.StringVar()
        self.category_var = ctk.StringVar()
        self.preset_var = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Initializing...")
        self.sample_rate_var = ctk.StringVar(value="48000")
        self.output_mode = ctk.StringVar(value="stereo")
        self.synthesis_state = ctk.StringVar(value="ready")
        self.playback_pos = ctk.DoubleVar(value=0.0)

        # Model checksums (SHA256) - add your actual checksums here
        self.model_checksums = {
            "v3_en.pt": "02b71034d9f13bc4001195017bac9db1c6bb6115e03fea52983e8abcff13b665",
            "v3_1_ru.pt": "cf60b47ec8a9c31046021d2d14b962ea56b8a5bf7061c98accaaaca428522f85",
            "v4_ru.pt": "896ab96347d5bd781ab97959d4fd6885620e5aab52405d3445626eb7c1414b00"
        }

        self.supported_models = {
            "v3_en": {
                "file": "v3_en.pt",
                "sample_rates": [8000, 24000, 48000],
                "supports_sample_rate": True,  # Explicit flag
                "speakers": [f'en_{i}' for i in range(118)],
                "default_rate": 48000,
                "language": "en",
                "supports_ssml": False
            },
            "v3_1_ru": {
                "file": "v3_1_ru.pt",
                "sample_rates": [8000, 24000, 48000],
                "supports_sample_rate": True,  # Explicit flag
                "speakers": ['aidar', 'baya', 'kseniya', 'xenia', 'eugene'],
                "default_rate": 48000,
                "language": "ru",
                "supports_ssml": False
            },
            "v4_ru": {
                "file": "v4_ru.pt",
                "sample_rates": [8000, 24000, 48000],
                "supports_sample_rate": True,  # Explicit flag
                "speakers": ['aidar', 'baya', 'kseniya', 'xenia', 'eugene'],
                "default_rate": 48000,
                "language": "ru",
                "supports_ssml": True
            }
        }

        self.just_buttons = []  # Initialize empty list for SSML buttons

    def _create_collapsible_section(self, parent, title):
        frame = ctk.CTkFrame(parent)
        header = ctk.CTkFrame(frame, fg_color="#252525")
        header.pack(fill="x")

        # Use icon instead of text arrow
        self.expand_icon = self.icons.get_arrow_icon('right')
        self.collapse_icon = self.icons.get_arrow_icon('down')

        self.toggle_btn = ctk.CTkButton(
            header,
            text=title,
            image=self.expand_icon,
            compound="left",
            command=lambda: self._toggle_section(frame),
            fg_color="transparent",
            hover_color="#353535",
            anchor="w"
        )
        self.toggle_btn.pack(fill="x", expand=True)

        self.section_content = ctk.CTkFrame(frame)
        # return self.section_content
        return frame  # Return the outer frame, not just content

    def _toggle_section(self, frame):
        if self.section_content.winfo_ismapped():
            self.section_content.pack_forget()
            self.toggle_btn.configure(image=self.expand_icon)
        else:
            self.section_content.pack(fill="x")
            self.toggle_btn.configure(image=self.collapse_icon)

    def _handle_missing_models(self):
        """Provide detailed information about missing/invalid models"""
        if not hasattr(self.tts, 'supported_models'):
            return

        missing = []
        invalid = []
        required_sizes = {}

        for model_name, config in self.tts.supported_models.items():
            model_file = config.get("file")
            if not model_file:
                continue

            model_path = self.models_dir / model_file
            if not model_path.exists():
                missing.append(model_file)
                continue

            # Check checksum if available
            if model_file in self.model_checksums:
                try:
                    with open(model_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    if file_hash != self.model_checksums[model_file]:
                        invalid.append(model_file)
                except:
                    invalid.append(model_file)

        message = []
        if missing:
            message.append(f"Missing model files:")
            message.extend(f" - {f}" for f in missing)

        if invalid:
            message.append(f"\nInvalid model files (checksum mismatch):")
            message.extend(f" - {f}" for f in invalid)

        if message:
            full_message = "\n".join(message)
            print(f"\nMODEL VERIFICATION ISSUES:")
            print(full_message)

            # Show in status bar
            self.status_var.set(f"Model verification issues - see console")

            # Show message box if UI is ready
            if hasattr(self, 'tk'):
                from tkinter import messagebox
                messagebox.showwarning(
                    "Model Verification",
                    f"Model verification issues found:\n\n{full_message}\n\n"
                    f"Please download valid models to:\n{self.models_dir}"
                )

    def _load_presets_file(self):
        """Load presets from file or create default structure"""
        try:
            if os.path.exists(self.presets_file):
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            else:
                self.presets = {
                    "Russian": {},
                    "English": {}
                }
                self._save_presets_to_file()
        except Exception as e:
            print(f"Error loading presets: {e}")
            self.presets = {
                "Russian": {},
                "English": {}
            }

    def _save_presets_to_file(self):
        """Save presets to JSON file"""
        try:
            with open(self.presets_file, 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def _verify_presets(self):
        print(f"\n=== Presets Verification ===")
        print(f"Presets path: {os.path.join(os.path.dirname(__file__), 'presets.json')}")
        print(f"File exists: {os.path.exists(os.path.join(os.path.dirname(__file__), 'presets.json'))}")
        print(f"Loaded presets: {self.presets}")
        print(f"==========================\n")

    def _update_preset_options(self, *args):
        """Safely update presets dropdown"""
        try:
            category = self.category_var.get()
            if not hasattr(self, 'presets') or category not in self.presets:
                self.preset_menu.configure(values=[])
                return

            presets = self.presets[category]
            preset_names = []

            for name, content in presets.items():
                if isinstance(content, dict):  # New format
                    # Only show presets matching current language
                    if (category == "Russian" and content.get("language") == "ru") or \
                       (category == "English" and content.get("language") == "en"):
                        preset_names.append(name)
                else:  # Legacy format - include all
                    preset_names.append(name)

            self.preset_menu.configure(values=preset_names)
            if preset_names:
                self.preset_var.set(preset_names[0])
        except Exception as e:
            print(f"Preset update error: {e}")
            self.preset_menu.configure(values=[])

    def _load_preset(self, choice):
        try:
            if choice == "Untitled":
                return  # Don't try to load an untitled preset

            category = self.category_var.get()
            if not category or not choice or choice == "Untitled":
                return

            # Get the preset data
            preset = self.presets[category][choice]

            # Clear and populate text field
            self.text_input.delete("1.0", "end")

            if isinstance(preset, dict):
                text = preset["text"]
                # Auto-wrap in SSML tags if needed
                if category == "Russian SSML" and not text.startswith("<speak>"):
                    text = f"<speak>{text}</speak>"
                self.text_input.insert("1.0", text)
            else:  # Legacy format
                self.text_input.insert("1.0", preset)

            # Update SSML button states
            self._toggle_ssml()

        except Exception as e:
            if choice != "Untitled":  # Only show errors for real presets
                self._handle_error(f"Failed to load preset '{choice}'", e)

    def _update_waveform(self, audio_data):
        """Update waveform display with proper mono/stereo handling"""
        try:
            # Clear previous plots
            self.ax_left.clear()
            self.ax_right.clear()

            # Configure axes
            for ax in [self.ax_left, self.ax_right]:
                ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
                ax.set_ylim(-1.1, 1.1)
                ax.set_xticklabels([])
                ax.set_yticklabels([])

            # Ensure audio_data is 2D (samples, channels)
            if len(audio_data.shape) == 1:
                audio_data = np.expand_dims(audio_data, axis=1)

            # Get number of channels
            num_channels = audio_data.shape[1]

            # Plot based on output mode and available channels
            if self.output_mode.get() == "mono" or num_channels == 1:
                # Mono display - same data on both channels
                mono_data = audio_data[:,0] if num_channels > 1 else audio_data[:,0]
                self.line_left, = self.ax_left.plot(mono_data, color='#4CAF50')
                self.line_right, = self.ax_right.plot(mono_data, color='#4CAF50')
            else:
                # Stereo display
                self.line_left, = self.ax_left.plot(audio_data[:,0], color='#4CAF50')
                if num_channels > 1:
                    self.line_right, = self.ax_right.plot(audio_data[:,1], color='#4CAF50')
                else:
                    self.line_right, = self.ax_right.plot(audio_data[:,0], color='#4CAF50')

            # Add RMS visualization
            for ax, channel in zip([self.ax_left, self.ax_right],
                                 [audio_data[:,0],
                                  audio_data[:,1] if num_channels > 1 else audio_data[:,0]]):
                rms = np.sqrt(np.mean(channel**2))
                ax.fill_betweenx(
                    [-1.1, -1.1 + rms*2.2],
                    0, len(channel),
                    color='#4CAF50',
                    alpha=0.1
                )

            # Initialize or update cursor lines
            # self.cursor_left = self.ax_left.axvline(x=0, color='red', linewidth=1.5, alpha=0.9)
            # self.cursor_right = self.ax_right.axvline(x=0, color='red', linewidth=1.5, alpha=0.9)
            # Initialize or update cursor lines with higher visibility
            self.cursor_left = self.ax_left.axvline(x=0, color='red', linewidth=2, alpha=0.9)
            self.cursor_right = self.ax_right.axvline(x=0, color='red', linewidth=2, alpha=0.9)

            # Update duration display
            duration = len(audio_data) / 48000
            self.time_text.set_text(f"00:00.000 / {self._format_duration(duration)}")

            self.canvas.draw()

        except Exception as e:
            print(f"Waveform update error: {e}")
            # Fallback to empty display
            self.ax_left.clear()
            self.ax_right.clear()
            for ax in [self.ax_left, self.ax_right]:
                ax.grid(True, color='#333333', linestyle='--', alpha=0.5)
                ax.set_ylim(-1.1, 1.1)
            self.canvas.draw()

    def _format_duration(self, seconds):
        """Format seconds to MM:SS.mmm"""
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins:02d}:{secs:06.3f}"

    def _setup_app(self):
        """Configure main window with dynamic sizing"""
        self.title(f"Voxiom TTS GUI")
        self.geometry("1000x800")  # Slightly taller default
        self.minsize(800, 600)    # Reasonable minimum size
        self.maxsize(1100, 900)   # Maximum size
        self.configure(fg_color=self.dark_bg)

        # Make the window responsive
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Windows taskbar integration
        if sys.platform == 'win32':
            try:
                from ctypes import windll
                windll.shell32.SetCurrentProcessExplicitAppUserModelID('Voxiom.TTS.GUI.1.0')
            except:
                pass

    def _setup_tts(self):
        """Initialize TTS engine with proper path handling"""
        self.status_var.set(f"Setting up TTS engine...")
        self.update()

        # Get absolute path to models directory
        self.models_dir = Path(__file__).parent / "models" / "tts"
        print(f"Models directory: {self.models_dir}")

        # Create directory if it doesn't exist
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # List files for debugging
        print(f"Files in models directory:")
        for f in self.models_dir.glob('*'):
            print(f" - {f.name} ({f.stat().st_size/1024/1024:.2f} MB)")

        try:
            # Initialize WITHOUT default_sample_rate
            self.tts = SileroTTS(str(self.models_dir))
            # Check what parameters the engine supports
            self.tts.SUPPORTS_SAMPLE_RATE = hasattr(self.tts, 'sample_rate')
            self.status_var.set(f"TTS engine ready")
        except Exception as e:
            self.status_var.set(f"TTS init failed: {str(e)}")
            print(f"TTS initialization error: {traceback.format_exc()}")
            # Create minimal dummy TTS object
            self.tts = type('DummyTTS', (), {
                'presets': {},
                'supported_models': {},
                'load_model': lambda *args: False,
                'get_voices': lambda: []
            })()

    def _update_model_ui(self, model_name: str):
        """Update all UI elements based on selected model"""
        try:
            # Update model dropdown
            self.model_var.set(model_name)

            # Load the model first
            if not self.tts.load_model(model_name):
                raise RuntimeError(f"Model loading failed")

            # Get voices for the loaded model
            voices = self.tts.get_voices()

            # Add these debug prints
            print(f"\n=== Voice Loading Debug ===")
            print(f"Loaded voices for {model_name}: {voices}")
            print(f"Voice menu exists: {hasattr(self, 'voice_menu')}")
            print(f"==========================\n")

            # Update voice menu if it exists
            if hasattr(self, 'voice_menu'):
                self.voice_menu.configure(values=voices)
                if voices:
                    self.voice_var.set(voices[0])
                    self._update_presets_for_language(voices[0].split('_')[0])

        except Exception as e:
            print(f"UI update error: {e}")
            self.status_var.set(f"UI update failed: {str(e)}")

    def _update_presets_for_language(self, language: str):
        """Filter presets based on language"""
        if not hasattr(self, 'tts') or not hasattr(self.tts, 'presets'):
            return

        available_presets = []
        for category, presets in self.tts.presets.items():
            # Check for language-specific or default preset
            if language in presets or 'default' in presets:
                available_presets.append(category)

        # Update UI if components exist
        if hasattr(self, 'category_menu'):
            self.category_menu.configure(values=available_presets)
            if available_presets:
                self.category_var.set(available_presets[0])
                self._update_preset_options()

    def _create_voice_controls(self):
        """Create voice selection controls"""
        voice_frame = ctk.CTkFrame(self.tts_tab)
        voice_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(voice_frame, text="Voice:").pack(side="left")
        self.voice_var = ctk.StringVar()

        # Now create voice_menu properly
        self.voice_menu = ctk.CTkOptionMenu(
            voice_frame,
            variable=self.voice_var,
            values=["Select model first"],
            width=200
        )
        self.voice_menu.pack(side="left", padx=5)

    def _preview_voice(self):
        """Play voice preview sample"""
        if not hasattr(self, 'voice_var') or not self.voice_var.get():
            return

        sample_text = "This is a voice preview"
        threading.Thread(
            target=lambda: self._generate_and_play(sample_text),
            daemon=True
        ).start()

    def _update_voices(self, *args):
        """Update voice list when language changes"""
        language = self.language_var.get()
        voices = self.tts.get_voices(language)
        self.voice_menu.configure(values=voices)
        if voices:
            self.voice_var.set(voices[0])

    def _verify_models_with_checksum(self):
        """Case-insensitive checksum verification"""
        self.available_models = []
        for model_name, config in self.tts.supported_models.items():
            model_file = config.get("file")
            model_path = self.models_dir / model_file

            if model_path.exists():
                # Case-insensitive comparison
                if model_file in self.model_checksums:
                    with open(model_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest().upper()  # Force uppercase

                    if file_hash == self.model_checksums[model_file].upper():  # Compare uppercase
                        self.available_models.append(model_name)
                else:
                    self.available_models.append(model_name)  # Accept if no checksum defined

    def _verify_models(self):
        """Enhanced model verification with detailed debugging"""
        if not hasattr(self, 'tts'):
            print(f"TTS engine not initialized in _verify_models")
            self.available_models = []
            return

        if not hasattr(self.tts, 'supported_models'):
            print(f"No supported_models attribute in TTS engine")
            self.available_models = []
            return

        self.available_models = []
        print(f"\n=== Model Verification ===")

        for model_name, config in self.tts.supported_models.items():
            model_file = config.get("file")
            if not model_file:
                print(f"Skipping {model_name} - no file specified")
                continue

            model_path = self.models_dir / model_file
            print(f"Checking model: {model_name} at {model_path}")

            if not model_path.exists():
                print(f" - File not found: {model_path}")
                continue

            try:
                # Verify the model can be loaded
                if self._verify_model(str(model_path)):
                    print(f" - Model verified: {model_name}")
                    self.available_models.append(model_name)
                else:
                    print(f" - Model verification failed: {model_name}")
            except Exception as e:
                print(f" - Error verifying model {model_name}: {str(e)}")
                continue

        print(f"Available models: {self.available_models}")
        print(f"=======================\n")

        # Update UI
        if hasattr(self, 'model_menu'):
            self.model_menu.configure(values=self.available_models)

        if not self.available_models:
            self.status_var.set(f"No valid models found. Please download models.")
            self._handle_missing_models()  # Show detailed warning
        else:
            self.status_var.set(f"Found {len(self.available_models)} models")
            # Auto-select first available model
            self.model_var.set(self.available_models[0])
            self._load_model(self.available_models[0])

    def _verify_model(self, model_path: str) -> bool:
        """Check if model file is valid by attempting to load it"""
        try:
            # Try to load the model file
            state_dict = torch.load(model_path, map_location='cpu')
            if not isinstance(state_dict, dict):
                return False
            return True
        except Exception as e:
            print(f"Model verification failed for {model_path}: {str(e)}")
            return False

    def _create_default_icon(self, size, color):
        """Create a colored circle as fallback icon"""
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0,0), (size[0]-1, size[1]-1)], fill=color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    def _setup_dark_theme(self):
        """Configure dark theme"""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        plt.style.use('dark_background')

        self.style = ttk.Style()
        self.style.theme_use('default')
        self.style.configure('TNotebook', background=self.dark_bg)
        self.style.configure('TNotebook.Tab',
                           background=self.dark_bg,
                           foreground=self.dark_text,
                           padding=[10, 5],
                            font=('Arial', 10, 'bold'))
        self.style.map('TNotebook.Tab',
                     background=[('selected', self.active_tab_color)],
                     foreground=[('selected', '#4CAF50')])  # Active tab white text
        # self._setup_attributes():
        # Add these to your color definitions
        self.success_green = "#4CAF50"
        self.warning_orange = "#FF9800"
        self.error_red = "#FF5252"

    def _create_ui(self):
        """Create all UI components"""
        self._setup_dark_theme()
        self._create_notebook()
        self._create_tts_tab()
        self._create_settings_tab()
        self._create_status_bar()  # Now status_var exists when this is called

            # Initialize with first model if available
        if hasattr(self, 'tts') and self.available_models:
            self._update_model_ui(self.available_models[0])

    def _on_model_selected(self, event=None):
        """Handle model selection changes with integrated model indicator updates"""
        try:
            model_name = self.model_var.get()
            if not model_name:
                self.model_indicator.configure(text="No model selected")
                return

            # Get model configuration
            model_info = self.supported_models.get(model_name, {})
            if not model_info:
                raise ValueError(f"Model {model_name} not in supported models")

            # Update sample rate options
            sample_rates = model_info.get("sample_rates", [48000])
            self.sample_rate_menu.configure(values=[str(r) for r in sample_rates])
            if str(model_info.get("default_rate", 48000)) in self.sample_rate_menu._values:
                self.sample_rate_var.set(str(model_info.get("default_rate", 48000)))

            # Verify model file exists
            model_file = model_info.get("file")
            if not model_file:
                raise ValueError("No model file specified in config")

            model_path = self.models_dir / model_file
            if not model_path.exists():
                raise FileNotFoundError(f"Model file missing: {model_path}")

            # Load model with visual feedback
            self.status_var.set(f"Loading {model_name}...")
            self.status_icon.configure(image=self.status_icons["working"])
            self.update()

            if not self.tts.load_model(model_name):
                raise RuntimeError("Model loading returned False")

            # Update all dependent components
            self._update_model_dependent_ui(model_name)

            # Success feedback
            self.status_var.set(f"Model loaded: {model_name}")
            self.status_icon.configure(image=self.status_icons["ready"])

        except Exception as e:
            self.model_indicator.configure(text="Load failed")
            self._handle_error("Model change failed", e)

    def _update_model_dependent_ui(self, model_name):
        """Update all UI elements that depend on the current model"""
        # Update voices
        voices = self.tts.get_voices() or ["No voices available"]
        self.voice_menu.configure(values=voices)
        if voices:
            self.voice_var.set(voices[0])

        # Update presets
        self._update_presets_for_model(model_name)
        if hasattr(self, 'category_var') and self.category_var.get():
            self._load_first_preset_in_category(self.category_var.get())

        # Update model indicator via trace
        self.model_var.set(model_name)  # This triggers the trace

    def is_ssml(text: str) -> bool:
        """Check if text contains SSML tags"""
        text = text.lower().strip()
        return any(tag in text for tag in ['<speak>', '<prosody', '<break', '<say-as'])

    def _debug_model_change(self, model_name):
        print(f"\n=== Model Change Debug: {model_name} ===")
        print(f"Current model: {self.tts.current_model}")
        print(f"Available voices: {self.tts.get_voices()}")
        print(f"Sample rates: {self.tts.supported_models[model_name]['sample_rates']}")
        print(f"Preset categories:", [
            cat for cat in self.tts.presets
            if any(k in self.tts.presets[cat] for k in ['default', model_name.split('_')[0]])
        ])
        print(f"==============================\n")

    def _debug_model_loading(self):
        """Temporary debug method to diagnose model loading"""
        if not hasattr(self, 'tts'):
            print(f"TTS engine not initialized")
            return

        print(f"\n=== Model Loading Debug ===")
        print(f"TTS Engine: {self.tts.__class__.__name__}")
        print(f"Supported Models: {getattr(self.tts, 'supported_models', 'N/A')}")

        if hasattr(self.tts, 'load_model'):
            print(f"TTS has load_model method")
        else:
            print(f"TTS MISSING load_model method")

        # Try direct model loading as test
        test_model = next(iter(self.tts.supported_models.keys()), None) if hasattr(self.tts, 'supported_models') else None
        if test_model:
            print(f"\nAttempting to load test model: {test_model}")
            try:
                success = self.tts.load_model(test_model)
                print(f"Load result: {success}")
                if success:
                    print(f"Voices: {self.tts.get_voices()}")
            except Exception as e:
                print(f"Test load failed: {str(e)}")
                traceback.print_exc()

        print(f"==========================")

    def _create_waveform_display(self, parent):
        frame = ctk.CTkFrame(parent, height=120, fg_color=self.dark_frame)
        frame.pack(fill="x", padx=5, pady=(0,5), expand=False)

        self.fig = Figure(figsize=(10, 1.5), dpi=100, facecolor=self.dark_frame)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1, 1])

        # Waveform channels
        self.ax_left = self.fig.add_subplot(gs[0], facecolor=self.dark_frame)
        self.ax_right = self.fig.add_subplot(gs[1], facecolor=self.dark_frame)

        # Configure axes
        for ax, label in zip([self.ax_left, self.ax_right], ["L", "R"]):
            ax.grid(True, color='#333333', linestyle=':', alpha=0.3)
            ax.set_ylim(-1.1, 1.1)
            ax.set_yticks([])
            ax.set_xticklabels([])
            ax.text(0.01, 0.9, label, transform=ax.transAxes,
                   color='white', fontsize=10, fontweight='bold')

        # Initialize empty waveforms
        self.line_left, = self.ax_left.plot([], [], color='#4CAF50', linewidth=1.5)
        self.line_right, = self.ax_right.plot([], [], color='#4CAF50', linewidth=1.5)

        # Initialize cursors
        self.cursor_left = self.ax_left.axvline(x=0, color='#FF0000', linewidth=2, alpha=0)
        self.cursor_right = self.ax_right.axvline(x=0, color='#FF0000', linewidth=2, alpha=0)

        # Initialize time text
        self.time_text = self.fig.text(0.5, 0.02, "00:00.000 / 00:00.000",
                                     ha='center', color='white', fontsize=10)

        self.canvas = FigureCanvasTkAgg(self.fig, master=frame)
        self.canvas.get_tk_widget().pack(fill="x", expand=False)
        self.canvas.mpl_connect('button_press_event', self._on_waveform_click)

        # Time display frame below waveform
        time_frame = ctk.CTkFrame(parent, height=28, fg_color="#252525")
        time_frame.pack(fill="x", padx=5, pady=(0,5))

        # Current position / total duration
        self.time_display1 = ctk.CTkLabel(
            time_frame,
            text="00:00.500 / 00:00.500",
            font=("Consolas", 11)
        )
        self.time_display1.pack(side="left", padx=10)

        # Selection start/end
        self.time_display2 = ctk.CTkLabel(
            time_frame,
            text="00:00.000 / 00:00.000",
            font=("Consolas", 11)
        )
        self.time_display2.pack(side="left", padx=10)

        # Play status label - this is what was missing
        self.play_status = ctk.CTkLabel(
            time_frame,
            text="Ready to play",
            font=("Arial", 11)
        )
        self.play_status.pack(side="left", padx=10)

        # Track number
        self.track_number = ctk.CTkLabel(
            time_frame,
            text="1",
            font=("Arial", 11)
        )
        self.track_number.pack(side="right", padx=10)

        # Large time display
        self.large_time = ctk.CTkLabel(
            time_frame,
            text="99:00 / 99:00",
            font=("Arial", 11, "bold")
        )
        self.large_time.pack(side="right", padx=10)

    def _on_waveform_click(self, event):
        if not hasattr(self, 'audio_data') or self.audio_data is None:
            return

        if event.inaxes in [self.ax_left, self.ax_right]:
            # Calculate position in samples
            total_samples = len(self.audio_data)
            x_pos = int(event.xdata)
            x_pos = max(0, min(x_pos, total_samples-1))

            # If currently playing, stop and seek
            if self.is_playing:
                sd.stop()
                self.playback_start_time = time.time() - (x_pos/48000)
                sd.play(self.audio_data[x_pos:], 48000, blocking=False)
            else:
                # Just move the cursor if not playing
                self._draw_playback_cursor(x_pos/total_samples)

    def _on_voice_selected(self, choice):
        """Handle voice selection change"""
        language = choice.split('_')[0]
        self._update_presets_for_language(language)
        self._toggle_ssml()

    def _load_first_preset(self):
        """Load the first preset if presets exist"""
        if hasattr(self, 'presets') and self.presets:
            first_preset = next(iter(self.presets))
            self._load_preset(first_preset)

        # In your category change handler:
    def _on_category_changed(self, *args):
        self._update_preset_options()
        self._toggle_ssml()

    def _on_text_modified(self, event=None):
        """Handle text changes by updating preset state"""
        if not hasattr(self, 'preset_var') or not hasattr(self, 'text_input'):
            return

        current_text = self.text_input.get("1.0", "end-1c").strip()

        if current_text:
            # Only set to Untitled if we're not already loading a preset
            if not self.preset_var.get():
                self.preset_var.set(f"Untitled")
                self._update_preset_options()
        else:
            self.preset_var.set(f"")

        # Update SSML button states
        self._toggle_ssml()

    def _handle_error(self, context_message, error):
        """Centralized error handling with logging"""
        try:
            error_msg = f"{context_message}: {str(error)}"

            # Update status bar
            self.status_var.set(error_msg)
            self.status_icon.configure(image=self.status_icons["error"])

            # Detailed logging
            error_details = traceback.format_exc()
            print(f"ERROR: {error_msg}\n{error_details}")

            # Log to file
            with open("error_log.txt", "a") as f:
                f.write(f"[{time.ctime()}] {error_msg}\n{error_details}\n\n")

        except Exception as e:
            print(f"Error handling failed: {str(e)}")

    def _thread_safe_error(self, message):
        """Show error message in main thread"""
        self.after(0, lambda: self.status_var.set(message))

    def _validate_ssml(self, text: str) -> bool:
        """Basic SSML validation"""
        text = text.strip()
        if not text.startswith("<speak>") or not text.endswith("</speak>"):
            return False
        # Add more validation as needed
        return True

    def _validate_sample_rate(self, model_info):
        """Validate and return proper sample rate with multiple fallbacks"""
        try:
            # 1. Try to use user-selected rate if valid
            user_rate = int(self.sample_rate_var.get())
            if user_rate in model_info.get("sample_rates", []):
                return user_rate

            # 2. Fallback to model's default rate
            if "default_rate" in model_info:
                self.sample_rate_var.set(str(model_info["default_rate"]))
                return model_info["default_rate"]

            # 3. Ultimate fallback to 48000
            self.sample_rate_var.set("48000")
            return 48000

        except (ValueError, AttributeError):
            # If all else fails
            self.sample_rate_var.set("48000")
            return 48000

    def _synthesize(self):
        if self.synthesis_state.get() == "synthesizing":
            return

        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            self.status_var.set(f"Error: No text to synthesize")
            return

        self.synthesis_state.set(f"synthesizing")
        self.play_btn.configure(state="disabled")
        self.status_var.set(f"Synthesizing...")

        threading.Thread(target=self._run_synthesis, args=(text,), daemon=True).start()

    def _run_synthesis(self, text):
        """Handle the complete synthesis process with proper parameter handling"""
        try:
            # Validate input
            text = text.strip()
            if not text:
                self.after(0, lambda: self.status_var.set("Error: No text to synthesize"))
                return

            # Prepare base parameters
            params = {
                'text': text,
                'speaker': self.voice_var.get()
            }

            # Check if model supports SSML
            if self._is_ssml_mode():
                params['ssml'] = True

            # Check if sample rate should be included
            current_model = self.model_var.get()
            if current_model in self.supported_models:
                model_info = self.supported_models[current_model]

                # Only add sample_rate if the model explicitly supports it
                if model_info.get('supports_sample_rate', False):
                    params['sample_rate'] = int(self.sample_rate_var.get())

            # Update UI for synthesis start
            self.after(0, lambda: [
                self.status_var.set("Synthesizing..."),
                self.status_icon.configure(image=self.status_icons["working"]),
                self.play_btn.configure(state="disabled")
            ])

            # Generate audio - only pass supported parameters
            valid_params = {}
            for param, value in params.items():
                if param in inspect.signature(self.tts.speak).parameters:
                    valid_params[param] = value

            audio = self.tts.speak(**valid_params)

            # Convert to numpy and process audio
            audio_np = audio.numpy()
            if len(audio_np.shape) == 1:  # Mono audio
                audio_np = np.expand_dims(audio_np, axis=1)  # Convert to 2D

            # Normalize audio with headroom
            max_amp = np.max(np.abs(audio_np))
            if max_amp > 0:
                audio_np = (audio_np / max_amp) * 0.95  # 5% headroom

            # Add small silence at beginning
            silence = np.zeros((int(0.05 * 48000), audio_np.shape[1]))
            self.audio_data = np.concatenate((silence, audio_np))

            # Update UI on completion
            self.after(0, self._on_synthesis_complete)

        except Exception as error:
            error_msg = str(error) or "Unknown error"
            self.after(0, lambda e=error_msg: [
                self._handle_error("Synthesis failed", e),
                self.play_btn.configure(state="normal"),
                self.status_icon.configure(image=self.status_icons["error"])
            ])

    def _on_synthesis_complete(self):
        try:
            if not hasattr(self, 'audio_data') or self.audio_data is None:
                self.status_var.set(f"Error: No audio generated")
                self.status_icon.configure(image=self.status_icons["error"])
                return

            # Force waveform update
            self._update_waveform(self.audio_data)

            # Make sure cursors are visible
            if hasattr(self, 'cursor_left') and hasattr(self, 'cursor_right'):
                self.cursor_left.set_alpha(0.9)
                self.cursor_right.set_alpha(0.9)
                self.canvas.draw_idle()

            self.synthesis_state.set("done")
            self.play_btn.configure(
                state="normal",
                image=self.icons.get("play", (16,16))
            )
            self.status_var.set(f"Ready to play")
            self.status_icon.configure(image=self.status_icons["ready"])

            # Only update play_status if it exists
            if hasattr(self, 'play_status'):
                self.play_status.configure(text="Ready to play")

            # Reset time displays
            if hasattr(self, 'audio_data'):
                duration = len(self.audio_data) / 48000
                mins, secs = divmod(duration, 60)
                if hasattr(self, 'time_display1'):
                    self.time_display1.configure(text=f"00:00.000 / {int(mins):02d}:{secs:06.3f}")
                if hasattr(self, 'time_display2'):
                    self.time_display2.configure(text=f"00:00.000 / {int(mins):02d}:{secs:06.3f}")
                if hasattr(self, 'large_time'):
                    self.large_time.configure(text=f"00:00 / {int(mins):02d}:{int(secs):02d}")

        except Exception as e:
            self._handle_error(f"Completion handler failed", e)

    def _verify_audio_shape(self, audio):
        """Ensure audio is proper format based on output mode"""
        if self.output_mode.get() == "mono":
            if len(audio.shape) == 2:  # Convert stereo to mono
                return np.mean(audio, axis=1)
            return audio.squeeze()  # Ensure 1D array
        else:  # Stereo
            if len(audio.shape) == 1:  # Convert mono to stereo
                return np.column_stack((audio, audio))
            elif audio.shape[1] == 1:  # Single channel 2D array
                return np.column_stack((audio[:,0], audio[:,0]))
            return audio

        # 5. Also update the _animate_playback_cursor method:
    def _animate_playback_cursor(self):
        if not hasattr(self, 'playback_start_time') or not self.is_playing:
            return

        try:
            current_time = time.time() - self.playback_start_time
            duration = len(self.audio_data) / 48000
            progress = min(1.0, current_time / duration)

            # Update cursor position
            self._draw_playback_cursor(progress)

            if progress < 1.0 and self.is_playing:
                self.after(16, self._animate_playback_cursor)  # ~60fps
            else:
                self._stop_playback()
        except Exception as e:
            print(f"Cursor animation error: {e}")
            self._stop_playback()

    def _draw_playback_cursor(self, position):
        """Update playback cursor position"""
        if not hasattr(self, 'ax_left') or not hasattr(self, 'audio_data'):
            return

        try:
            total_samples = len(self.audio_data)
            cursor_pos = int(position * total_samples)

            # Update cursor positions with high visibility
            self.cursor_left.set_xdata([cursor_pos, cursor_pos])
            self.cursor_left.set_alpha(0.9)  # Always visible
            self.cursor_right.set_xdata([cursor_pos, cursor_pos])
            self.cursor_right.set_alpha(0.9)  # Always visible

            # Update time displays
            current_time = position * (total_samples / 48000)
            total_time = total_samples / 48000

            # Format as MM:SS.mmm
            mins, secs = divmod(current_time, 60)
            total_mins, total_secs = divmod(total_time, 60)

            self.time_text.set_text(
                f"{int(mins):02d}:{secs:06.3f} / {int(total_mins):02d}:{total_secs:06.3f}"
            )

            self.canvas.draw_idle()
        except Exception as e:
            print(f"Cursor update error: {e}")

    def _generate_and_play(self, text):
        try:
            # Initial state - yellow "preparing" state
            self.status_var.set(f"Preparing synthesis...")
            self.update_idletasks()

            # Validate input
            text = text.strip()
            if not text:
                self.status_var.set(f"Error: No text to synthesize")
                return

            # Synthesis phase - yellow progress
            self.status_var.set(f"Synthesizing...")
            self.play_btn.configure(state="disabled",
                       image=self.icons.get("loading", (16,16)))
            self.update_idletasks()

            # Generate audio
            audio = self.tts.speak(
                text=text,
                speaker=self.voice_var.get(),
                # Change this line in _generate_and_play:
                ssml=self._is_ssml_mode()  # Instead of ssml=use_ssml
            )

            # Processing phase - orange progress
            self.status_var.set(f"Processing...")
            self.play_btn.configure(state="disabled",
                       image=self.icons.get("loading", (16,16)))
            self.update_idletasks()

            audio_np = audio.numpy()
            max_amp = np.max(np.abs(audio_np))
            if max_amp > 0:
                audio_np = audio_np / max_amp
            self.audio_data = audio_np
            self._update_waveform(audio_np)

            # Playback phase - green animated progress
            self.play_btn.configure(
                image=self.icons.get("stop", (16, 16)),
                text="Stop",                            # Text label
                compound="left",                        # Icon on left
                fg_color="#FF5252",
                state="normal"
            )
            self.status_var.set(f"Playing audio...")
            self.update_idletasks()

            # Animation during playback
            def update_progress():
                duration = len(audio_np) / 48000  # Approximate duration in seconds
                step = 0.01 / duration  # Small step for smooth animation

                while self.is_playing and self.progress_value.get() < 1.0:
                    self.progress_value.set(self.progress_value.get() + step)
                    self.update_idletasks()
                    time.sleep(0.01)

            self.is_playing = True
            threading.Thread(target=update_progress, daemon=True).start()

            sd.play(audio_np, 48000)
            sd.wait()

            # Completion
            self.status_var.set(f"Playback complete")

        except Exception as e:
            self._handle_error(f"Synthesis failed", e)
        finally:
            self.is_playing = False

    def _toggle_ssml(self):
        """Enable/disable justification controls based on context"""
        has_text = bool(self.text_input.get("1.0", "end-1c").strip())
        for btn in self.just_buttons:
            btn.configure(state="normal" if has_text else "disabled")

    def _create_notebook(self):
        """Create just the notebook widget without tabs"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

    # Usage in button creation:
    def _create_action_button(self, parent, icon_name, text, command):
        """Universal button factory with icons"""
        return ctk.CTkButton(
            master=parent,
            text=text,
            image=self.icons.get(icon_name, (16,16)),
            compound="left",
            command=command,
            width=120,
            height=28
        )

        # Usage example:
        # self.play_btn = self._create_action_button(
        #     frame, "play", "Play", self._play_audio
        # )

    def _create_tts_tab(self):
        """Create TTS tab with improved layout and fixed playback states"""
        self.tts_tab = ctk.CTkFrame(self.notebook, fg_color=self.dark_frame)
        self.notebook.add(self.tts_tab, text="TTS Generation")

        # Main container with consistent padding
        main_frame = ctk.CTkFrame(self.tts_tab, fg_color=self.dark_frame)
        main_frame.pack(fill="both", expand=True, padx=5, pady=5)  # Padding here

        # ===== Top Controls Section =====
        controls_frame = ctk.CTkFrame(main_frame, height=32)
        controls_frame.pack(fill="x", pady=(0,5))  # Padding here
        controls_frame.grid_propagate(False)

        # Category selection
        ctk.CTkLabel(controls_frame, text="Category:").grid(row=0, column=0, padx=(10,0), sticky="w")
        self.category_menu = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.category_var,
            values=["English", "Russian"],
            width=150,
            command=self._on_category_changed
        )
        self.category_menu.grid(row=0, column=1, padx=5, sticky="w")

        # Preset selection
        ctk.CTkLabel(controls_frame, text="Preset:").grid(row=0, column=2, padx=(10,0), sticky="w")
        self.preset_menu = ctk.CTkOptionMenu(
            controls_frame,
            variable=self.preset_var,
            values=[],
            width=200,
            command=self._load_preset
        )
        self.preset_menu.grid(row=0, column=3, padx=5, sticky="w")

        # Save button
        self.save_btn = ctk.CTkButton(
            controls_frame,
            text="Save",
            image=self.icons.get("save", (16,16)),
            command=self._save_preset,
            width=80,
            height=28
        )
        self.save_btn.grid(row=0, column=4, padx=5, sticky="w")

        # ===== Justification Controls =====
        # self._create_just_controls(controls_frame)

        """Create new audio justification controls"""
        # self.just_frame = ctk.CTkFrame(controls_frame, fg_color="#252525")
        # self.just_frame.pack(fill="x", pady=(5, 10))  # CHANGED PADDING HERE

        # Timing display
        self.time_display = ctk.CTkLabel(
            #self.just_frame,
            controls_frame,
            text="00:00 / 00:00",
            font=("Consolas", 11)
        )
        self.time_display.pack(side="right", padx=10)

        # Control buttons frame
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.pack(side="right")

        # Punctuation insertion button
        self.pause_btn = ctk.CTkButton(
            btn_frame,
            text=", — ",
            width=50,
            command=lambda: self._insert_justification(f", — ")
        )
        self.pause_btn.pack(side="left", padx=2)
        self._create_button_tooltip(self.pause_btn,
                                  "Insert pause punctuation\n(Estimated duration: 750ms)")

        # Pronunciation separator
        self.pronounce_btn = ctk.CTkButton(
            btn_frame,
            text="+",
            width=50,
            command=lambda: self._insert_justification(f"+")
        )
        self.pronounce_btn.pack(side="left", padx=2)
        self._create_button_tooltip(self.pronounce_btn,
                                  "Insert pronunciation separator\n(No added pause)")

        # Store references for state management
        self.just_buttons = [self.pause_btn, self.pronounce_btn]

        # ===== Text Input Section =====
        self.text_input = ctk.CTkTextbox(
            main_frame,
            wrap="word",
            height=200,  # Increased height
            font=("Arial", 14),
            fg_color="#2d2d2d",
            padx=10,  # Added horizontal padding
            pady=10   # Added vertical padding
        )
        self.text_input.pack(fill="x", pady=(5,10))  # Increased bottom padding
        self.text_input.bind(f"<KeyRelease>", self._on_text_modified)

        # ===== Waveform Display =====
        self._create_waveform_display(main_frame)

        # ===== Bottom Controls Section =====
        bottom_frame = ctk.CTkFrame(main_frame, height=32)
        bottom_frame.pack(fill="x", pady=(5,0))
        bottom_frame.grid_propagate(False)  # Fixed height

        # Audio format controls
        format_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        format_frame.grid(row=0, column=0, sticky="w", padx=5, pady=5)  # Add padding here

        ctk.CTkLabel(format_frame, text="Sample Rate:").pack(side="left", padx=(10,0))
        self.sample_rate_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.sample_rate_var,
            values=["48000", "24000", "8000"],
            width=80
        )
        self.sample_rate_menu.pack(side="left", padx=5)

        ctk.CTkLabel(format_frame, text="Output:").pack(side="left", padx=(10,0))
        ctk.CTkOptionMenu(
            format_frame,
            variable=self.output_mode,
            values=["mono", "stereo"],
            width=80,
            command=lambda _: self._update_waveform(self.audio_data) if hasattr(self, 'audio_data') else None
        ).pack(side="left", padx=5)

        ctk.CTkLabel(format_frame, text="Voice:").pack(side="left", padx=(10,0))
        self.voice_menu = ctk.CTkOptionMenu(
            format_frame,
            variable=self.voice_var,
            values=["Select model first"],
            width=150
        )
        self.voice_menu.pack(side="left", padx=5)

        # Action buttons
        # Action buttons frame
        action_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        action_frame.grid(row=0, column=1, sticky="e", padx=5, pady=5)  # Padding in grid

        button_width = 100
        button_height = 28
        button_padx = 5

        self.synth_btn = ctk.CTkButton(
            action_frame,
            text="Synthesize",
            image=self.icons.get("synth", (16,16)),
            compound="left",
            command=self._synthesize,
            width=button_width,
            height=button_height
        )
        self.synth_btn.pack(side="left", padx=button_padx)

        self.play_btn = ctk.CTkButton(
            action_frame,
            text="Play",
            image=self.icons.get("play", (16,16)),
            compound="left",
            command=self._play_audio,
            width=button_width,
            height=button_height
        )
        self.play_btn.pack(side="left", padx=button_padx)

        self.export_btn = ctk.CTkButton(
            action_frame,
            text="Export",
            image=self.icons.get("export", (16,16)),
            compound="left",
            command=self._export_audio,
            width=button_width,
            height=button_height
        )
        self.export_btn.pack(side="left", padx=button_padx)

    def _play_audio(self):
        if not hasattr(self, 'audio_data') or self.audio_data is None:
            return

        if self.is_playing:
            sd.stop()
            self._stop_playback()
            return

        try:
            self.is_playing = True
            self.play_btn.configure(
                text="Stop",
                image=self.icons.get("stop", (16,16)),
                compound="left"
            )

            # Only update play_status if it exists
            if hasattr(self, 'play_status'):
                self.play_status.configure(text="Playing...")

            # Make sure cursors are visible
            if hasattr(self, 'cursor_left') and hasattr(self, 'cursor_right'):
                self.cursor_left.set_alpha(0.9)
                self.cursor_right.set_alpha(0.9)
                self.canvas.draw_idle()

            # Start playback
            self.playback_start_time = time.time()
            sd.play(self.audio_data, 48000, blocking=False)
            self._animate_playback_cursor()

        except Exception as e:
            self._handle_error(f"Playback failed", e)
            self._stop_playback()

    def _stop_playback(self):
        """Consistent playback stopping"""
        self.is_playing = False
        self.play_btn.configure(
            text="Play",
            image=self.icons.get("play", (16,16)),
            compound="left"
        )

        # Only update play_status if it exists
        if hasattr(self, 'play_status'):
            self.play_status.configure(text="Ready to play")

        self.status_var.set(f"Playback complete")
        self.status_icon.configure(image=self.status_icons["ready"])

        # Reset cursors to start but keep visible
        # Ensure cursors are visible at position 0
        if hasattr(self, 'cursor_left') and hasattr(self, 'cursor_right'):
            self._draw_playback_cursor(0)
            self.cursor_left.set_alpha(0.9)
            self.cursor_right.set_alpha(0.9)
            self.canvas.draw_idle()

    def _create_collapsible_section(self, parent, title):
        frame = ctk.CTkFrame(parent)
        header = ctk.CTkFrame(frame, fg_color="#252525", height=32)
        header.pack(fill="x")

        # Material design icons (11px height)
        self.expand_icon = self.icons.get("arrow-right", (11,11))
        self.collapse_icon = self.icons.get("arrow-down", (11,11))

        self.toggle_btn = ctk.CTkButton(
            header,
            text=title,
            image=self.expand_icon,
            compound="left",
            command=lambda: self._toggle_section(frame),
            fg_color="transparent",
            hover_color="#353535",
            anchor="w",
            height=28
        )
        self.toggle_btn.pack(side="left", padx=(5,0))  # 5px left padding for icon

        self.section_content = ctk.CTkFrame(frame)
        return self.section_content

    def _toggle_section(self, frame):
        """Toggle section visibility"""
        if self.section_content.winfo_ismapped():
            self.section_content.pack_forget()
            self.toggle_btn.configure(image=self.expand_icon)
        else:
            self.section_content.pack(fill="x")
            self.toggle_btn.configure(image=self.collapse_icon)

    def _calculate_audio_duration(self, text):
        """Estimate audio duration based on text content"""
        word_count = len(text.split())
        comma_pauses = text.count(f", — ") * 0.75
        base_duration = word_count * 0.35
        return base_duration + comma_pauses

    def _insert_justification(self, text):
        """Insert justification characters and calculate timing"""
        cursor_pos = self.text_input.index("insert")
        self.text_input.insert(cursor_pos, text)

        if text == ", — ":
            # Calculate and display pause duration
            self._update_timing_display(added_pause=0.75)  # 750ms for comma+em dash

        self._update_audio_timing()

    def _update_audio_timing(self):
        """Calculate total audio duration based on text"""
        text = self.text_input.get("1.0", "end-1c")

        # Basic estimation (adjust these values as needed)
        word_count = len(text.split())
        comma_pauses = text.count(f", — ") * 0.75  # 750ms per comma+em dash
        base_duration = word_count * 0.35  # 350ms per word

        total_seconds = base_duration + comma_pauses
        mins, secs = divmod(total_seconds, 60)
        self.time_display.configure(text=f"{int(mins):02d}:{int(secs):02d}")

    def _update_timing_display(self, added_pause=0):
        """Update the time display with added pause duration"""
        current_text = self.time_display.cget("text")
        if "/" in current_text:
            current, total = current_text.split("/")
            try:
                # Update total time
                mins, secs = map(int, total.strip().split(":"))
                new_total = mins * 60 + secs + added_pause
                new_mins, new_secs = divmod(new_total, 60)
                self.time_display.configure(
                    text=f"{current.strip()} / {int(new_mins):02d}:{int(new_secs):02d}"
                )
            except:
                pass

    def _get_safe_categories(self):
        """Get available categories without any SSML support"""
        # Default fallback categories
        default_categories = ["English", "Russian"]

        try:
            # If no TTS engine or presets, return defaults
            if not hasattr(self, 'tts') or not hasattr(self.tts, 'presets'):
                return default_categories

            current_model = self.model_var.get()
            if not current_model:
                return list(self.tts.presets.keys())

            # Get model language
            model_info = self.supported_models.get(current_model, {})
            language = model_info.get("language", "").lower()

            # Filter categories by language only
            valid_categories = []
            for category in self.tts.presets.keys():
                # Skip any SSML-related categories
                if "ssml" in category.lower():
                    continue

                # Language matching (case-insensitive)
                if language == "ru" and "russian" in category.lower():
                    valid_categories.append(category)
                elif language == "en" and "english" in category.lower():
                    valid_categories.append(category)

            return valid_categories if valid_categories else default_categories

        except Exception as e:
            print(f"Category filtering error: {e}")
            return default_categories

    def _create_button_tooltip(self, button, text):
        """Create a visible tooltip"""
        tooltip = ctk.CTkToplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry("+10000+10000")  # Start off-screen
        tooltip.lift()

        label = ctk.CTkLabel(
            tooltip,
            text=text,
            fg_color="#333333",
            text_color="#ffffff",
            corner_radius=5,
            padx=10,
            pady=5
        )
        label.pack()

        # Store references
        self.tooltips.append(tooltip)

        # Bind events
        button.bind(f"<Enter>", lambda e, t=tooltip, b=button: self._show_tooltip(t, b))
        button.bind(f"<Leave>", lambda e, t=tooltip: t.wm_geometry("+10000+10000"))
        button.bind(f"<ButtonPress>", lambda e, t=tooltip: t.wm_geometry("+10000+10000"))

    def _show_tooltip(self, tooltip, button):
        """Position tooltip near cursor"""
        x = button.winfo_rootx() + 20
        y = button.winfo_rooty() + button.winfo_height() + 5
        tooltip.wm_geometry(f"+{x}+{y}")
        tooltip.lift()

    def _create_settings_tab(self):
        self.settings_tab = ctk.CTkFrame(self.notebook, fg_color=self.dark_frame)
        self.notebook.add(self.settings_tab, text="Settings")

        main_frame = ctk.CTkFrame(self.settings_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== Model Management Section =====
        model_frame = ctk.CTkFrame(main_frame)
        model_frame.pack(fill="x", padx=5, pady=5)

        # Section header
        ctk.CTkLabel(model_frame, text="Model Management",
                    font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

        # Model selection row
        model_row = ctk.CTkFrame(model_frame)
        model_row.pack(fill="x", pady=5)

        # Model dropdown
        ctk.CTkLabel(model_row, text="Model:").pack(side="left")
        self.model_menu = ctk.CTkOptionMenu(
            model_row,
            variable=self.model_var,
            values=list(self.supported_models.keys()),
            command=self._on_model_selected,
            width=200
        )
        self.model_menu.pack(side="left", padx=5)

        # Model action buttons
        model_btn_frame = ctk.CTkFrame(model_row)
        model_btn_frame.pack(side="right")

        # Update Model Button
        self.update_btn = ctk.CTkButton(
            model_btn_frame,
            text="Update",
            image=self.icons.get("update", (16,16)),
            compound="left",
            command=self._update_model,
            width=120
        )
        self.update_btn.pack(side="left", padx=5)

        # ===== Model Selection Section =====
        selector_frame = ctk.CTkFrame(main_frame)
        selector_frame.pack(fill="x", padx=5, pady=(5, 10), expand=True)

        # Section header
        ctk.CTkLabel(selector_frame,
                    text="Available Models",
                    font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))

        # Model checkboxes with scroll
        self.model_checkbox_frame = ctk.CTkScrollableFrame(selector_frame, height=150)
        self.model_checkbox_frame.pack(fill="both", expand=True)

        # Initialize checkboxes
        self.model_vars = {}
        for model in get_available_models():
            self.model_vars[model["name"]] = ctk.BooleanVar(value=False)
            cb = ctk.CTkCheckBox(
                self.model_checkbox_frame,
                text=f"{model['name']} ({model['language']}){' [SSML]' if model['supports_ssml'] else ''}",
                variable=self.model_vars[model["name"]]
            )
            cb.pack(anchor="w", pady=2)

        # Model action buttons frame
        btn_frame = ctk.CTkFrame(selector_frame)
        btn_frame.pack(fill="x", pady=(10, 0))

        # Check Models Button
        self.check_btn = ctk.CTkButton(
            btn_frame,
            text="Verify",
            image=self.icons.get("verify", (16,16)),
            compound="left",
            command=self._verify_installed_models,
            width=120
        )
        self.check_btn.pack(side="left", padx=5)

        # Download Button
        self.download_btn = ctk.CTkButton(
            btn_frame,
            text="Download",
            image=self.icons.get("download", (16,16)),
            compound="left",
            command=self._download_selected_models,
            width=120
        )
        self.download_btn.pack(side="left", padx=5)

        # Status label
        self.model_update_status = ctk.CTkLabel(
            selector_frame,
            text="",
            text_color="#FF9800"
        )
        self.model_update_status.pack(pady=(5, 0))

        # Credits section
        credits_frame = ctk.CTkFrame(main_frame)
        credits_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(credits_frame, text="Credits",
                    font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

        # Main credits text
        # credits_text = """Voxiom TTS GUI - Version 1.0.0
        # • Silero TTS Engine
        # • CustomTkinter UI Framework - https://github.com/TomSchimansky/CustomTkinter
        # • Developed by Voxiom TTS Team"""
        # ctk.CTkLabel(
        #     credits_frame,
        #     text=credits_text,
        #     justify="left",
        #     font=("Arial", 11)
        # ).pack(anchor="w", padx=10)

        credits_text = """Voxiom TTS GUI - Version 1.0.0
                • Silero TTS Engine
                • CustomTkinter UI Framework"""
        customtkinter_link = "https://github.com/TomSchimansky/CustomTkinter"
        developed_by_text = "• Developed by Voxiom TTS Team"

        # Create a frame to hold all the text elements
        text_frame = ctk.CTkFrame(credits_frame)
        text_frame.pack(anchor="w", padx=10, fill="x")

        # Add the main credits text
        ctk.CTkLabel(
            text_frame,
            text=credits_text,
            justify="left",
            font=("Consolas", 12)
        ).pack(anchor="w")

        # Add the clickable link
        link_label = ctk.CTkLabel(
            text_frame,
            text=customtkinter_link,
            justify="left",
            font=("Consolas", 12, "underline"),
            text_color="#4cc9f0",
            cursor="hand2"
        )
        link_label.pack(anchor="w")
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new(customtkinter_link))

        # Add the developed by text
        ctk.CTkLabel(
            text_frame,
            text=developed_by_text,
            justify="left",
            font=("Consolas", 12)
        ).pack(anchor="w")

        # Citation text (initially hidden)
        # @misc{Silero Models,
        #     author = {Silero Team},
        #     title = {Silero Models: pre-trained enterprise-grade STT/TTS models},
        #     year = {2021},
        #     publisher = {GitHub},
        #     howpublished = {\\url{https://github.com/snakers4/silero-models}}
        # }

        # Silero citation frame with expandable details
        silero_frame = ctk.CTkFrame(credits_frame, fg_color="#252525")
        silero_frame.pack(fill="x", pady=(5, 0))

        # Header with clickable disclosure
        self.silero_expanded = False
        self.silero_header = ctk.CTkButton(
            silero_frame,
            text="▶ Silero Models Credits",
            font=("Consolas", 12),
            anchor="w",
            fg_color="transparent",
            hover_color="#353535",
            command=self._toggle_silero_citation
        )
        self.silero_header.pack(fill="x")

        self.silero_citation = ctk.CTkLabel(
            silero_frame,
            text="""
        Silero Models are pre-trained, enterprise-grade speech-to-text (STT)
        and text-to-speech (TTS) models developed by the Silero Team.

        Key Details:
        • Author: Silero Team
        • Year: 2021
        • Source: Available on GitHub
        • Project Page: """,
            justify="left",
            font=("Consolas", 12)
        )

        # Create a clickable link for the GitHub page
        self.silero_link = ctk.CTkLabel(
            silero_frame,
            text="github.com/snakers4/silero-models",
            text_color="#4cc9f0",
            font=("Consolas", 12, "underline"),
            cursor="hand2"
        )
        self.silero_link.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/snakers4/silero-models"))

        self.silero_citation_rest = ctk.CTkLabel(
            silero_frame,
            text="""

        This application uses Silero's TTS models for high-quality
        text-to-speech synthesis in multiple languages.""",
            justify="left",
            font=("Consolas", 12)
        )

        # Pack all elements
        self.silero_citation.pack(anchor="w", padx=5, pady=(0, 0))
        self.silero_link.pack(anchor="w", padx=5, pady=(0, 0))
        self.silero_citation_rest.pack(anchor="w", padx=5, pady=(0, 5))

    # Add the toggle handler method
    def _toggle_silero_citation(self):
        """Toggle citation visibility"""
        self.silero_expanded = not self.silero_expanded
        if self.silero_expanded:
            self.silero_citation.pack(fill="x", padx=10, pady=(0,5))
            self.silero_header.configure(text="▼ Silero Models Credits")
        else:
            self.silero_citation.pack_forget()
            self.silero_header.configure(text="▶ Silero Models Credits")

    # In the _save_preset method (around line 1500):
    def _save_preset(self):
        try:
            category = self.category_var.get()
            text = self.text_input.get("1.0", "end-1c").strip()

            if not text:
                self.status_var.set(f"Error: No text to save")
                return

            # Get preset name
            preset_name = self.preset_var.get()
            if preset_name == "Untitled" or not preset_name:
                preset_name = simpledialog.askstring(
                    "Save Preset",
                    "Enter preset name:",
                    parent=self,
                    initialvalue="New Preset"
                )
                if not preset_name:
                    return

            # Save the preset - MODIFIED THIS PART
            if category not in self.presets:
                self.presets[category] = {}

            self.presets[category][preset_name] = {
                "text": text,
                "language": "ru" if "Russian" in category else "en",
                "timestamp": time.strftime("%Y-%m-%d %H:%M")
            }

            # Save to file and update UI
            self._save_presets_to_file()
            self.preset_var.set(preset_name)
            self._update_preset_options()
            self.status_icon.configure(image=self.icons.get("verify", (16,16)))
            self.status_var.set(f"Preset saved: {preset_name}")

        except Exception as e:
            self._handle_error(f"Preset save failed", e)

    def _create_status_bar(self):
        status_frame = ctk.CTkFrame(self, height=28, fg_color="#2b2b2b")  # Darker background
        status_frame.pack(fill="x", padx=10, pady=(0,10))

        # Initialize status icons with proper color contrast
        self.status_icons = {
            "ready": self.icons.get("verify", (16,16)),
            "error": self.icons.get("warning", (16,16)),
            "working": self.icons.get("update", (16,16)),
            "warning": self.icons.get("warning", (16,16))
        }

        # Verify icons are properly colored
        for name, icon in self.status_icons.items():
            if not icon:
                print(f"Warning: Failed to load icon for {name}")
                # Fallback to colored circles
                self.status_icons[name] = self._create_colored_icon(
                    (16,16),
                    {"ready": "green", "error": "red", "working": "yellow", "warning": "orange"}[name]
                )

        # Status icon label with contrast
        self.status_icon = ctk.CTkLabel(
            status_frame,
            image=self.status_icons["ready"],
            width=24,
            text=""  # Ensure no text interferes
        )
        self.status_icon.pack(side="left", padx=(5,0))

        # Status text
        self.status_var = ctk.StringVar(value="Ready")
        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            anchor="w",
            font=("Arial", 10),
            width=300  # Increased width
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        # Model indicator - properly initialized
        self.model_var.trace_add('write', self._update_model_indicator)  # Add trace
        self.model_indicator = ctk.CTkLabel(
            status_frame,
            text="No model loaded",
            font=("Arial", 10),
            width=200,
            anchor="e"
        )
        self.model_indicator.pack(side="right", padx=10)

    def _create_colored_icon(self, size, color):
        """Create fallback colored circle icons"""
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', size, (0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(0,0), size], fill=color)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    def _update_model_indicator(self, *args):
        """Update model indicator when model changes"""
        current_model = self.model_var.get()
        if current_model:
            # Shorten long model names
            display_text = current_model.replace('_', ' ').replace('.pt', '')
            if len(display_text) > 15:
                display_text = display_text[:12] + '...'
            self.model_indicator.configure(text=display_text)
        else:
            self.model_indicator.configure(text="No model loaded")

    def _load_initial_model(self):
        """Load first valid model with UI updates"""
        if self.available_models:
            self.model_var.set(self.available_models[0])
            self._load_model(self.available_models[0])

            # Force UI updates
            self._update_model_ui(self.available_models[0])
            self._update_presets_for_model(self.available_models[0])
            self._update_voice_menu()
        else:
            self.status_var.set(f"No valid models found")

    def _load_model(self, model_name: str) -> bool:
        """Robust model loading with error reporting"""
        print(f"\nAttempting to load model: {model_name}")

        if not hasattr(self, 'tts'):
            self.status_var.set(f"TTS engine not initialized")
            return False

        try:
            # Verify model is supported
            if model_name not in getattr(self.tts, 'supported_models', {}):
                raise ValueError(f"Model {model_name} not in supported_models")

            # Get model config
            model_config = self.tts.supported_models[model_name]
            model_file = model_config.get("file")
            if not model_file:
                raise ValueError(f"No model file specified in config")

            # Check file exists
            model_path = self.models_dir / model_file
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")

            # Try loading
            print(f"Loading model from: {model_path}")
            success = self.tts.load_model(model_name)
            if not success:
                raise RuntimeError(f"TTS engine returned False when loading model")

            # Update voices
            voices = self.tts.get_voices()
            print(f"Model loaded successfully. Available voices: {voices}")

            # Update UI
            self.model_var.set(model_name)
            self._update_presets_for_model(model_name)
            self.status_var.set(f"Loaded: {model_name}")

            # Update voice menu if it exists
            if hasattr(self, 'voice_menu'):
                self.voice_menu.configure(values=voices)
                if voices:
                    self.voice_var.set(voices[0])

            # Update model indicator
            if hasattr(self, 'model_indicator'):
                self.model_indicator.configure(text=model_name)

            return True

        except Exception as e:
            error_msg = f"Failed to load model {model_name}: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self._handle_error(f"Model loading error", e)
            return False

    def _update_presets_for_model(self, model_name: str):
        """Update available categories based on model with proper Russian handling"""
        model_info = self.supported_models.get(model_name, {})
        language = model_info.get("language", "")
        supports_ssml = model_info.get("supports_ssml", False)

        # Determine available categories
        if model_name == "v3_en":
            categories = ["English"]
        elif model_name == "v4_ru" or "v3_1_ru":
            categories = ["Russian"]
        else:
            categories = []

        # Update UI
        if hasattr(self, 'category_menu'):
            self.category_menu.configure(values=categories)
            if categories:
                self.category_var.set(categories[0])
                self._update_preset_options()

    def _load_first_preset_in_category(self, category: str):
        """Load the first preset in the given category"""
        if category in self.presets:
            presets = self.presets[category]
            if presets:
                first_preset = next(iter(presets.keys()))
                self.preset_var.set(first_preset)
                self._load_preset(first_preset)

    def _safe_update_voice_menu(self):
        """Thread-safe voice menu update"""
        if not hasattr(self, 'voice_menu'):
            return

        try:
            voices = self.tts.get_voices()
            self.voice_menu.configure(values=voices)
            if voices:
                self.voice_var.set(voices[0])
        except Exception as e:
            print(f"Voice menu update failed: {str(e)}")

    def _update_voice_menu(self):
        """Thread-safe UI update"""
        if hasattr(self, 'voice_menu') and self.voice_menu:
            voices = self.tts.get_voices()
            self.voice_menu.configure(values=voices or ["No voices available"])
            if voices:
                self.voice_var.set(voices[0])

    def _update_model(self):
        if not self.model_var.get():
            self.status_var.set(f"Select a model first")
            return

        model_name = self.model_var.get()
        if model_name not in self.supported_models:
            self.status_var.set(f"Cannot update: {model_name} is not supported")
            return

        try:
            self.status_var.set(f"Updating {model_name}...")
            self.update_idletasks()

            self.tts.update_model(model_name)
            self.status_var.set(f"Updated: {model_name}")

            # Reload the model after update
            self._load_model(model_name)
        except Exception as e:
            self.status_var.set(f"Update failed: {str(e)}")

    def _verify_installed_models(self):
        """Check installed models and update checkbox states"""
        updater = ModelUpdater()
        for model_name, var in self.model_vars.items():
            status = updater.check_model(model_name)
            var.set(status["valid"])

            # Visual feedback
            for widget in self.model_checkbox_frame.winfo_children():
                if model_name in widget.cget("text"):
                    color = "#4CAF50" if status["valid"] else "#FF5252"
                    widget.configure(text_color=color)

        self.model_update_status.configure(
            text="Verification completed",
            text_color="#4CAF50"
        )

    def _download_selected_models(self):
        """Download selected models with progress feedback"""
        selected = [name for name, var in self.model_vars.items() if var.get()]
        if not selected:
            self.model_update_status.configure(
                text="No models selected!",
                text_color="#FF5252"
            )
            return

        self.model_update_status.configure(
            text=f"Downloading {len(selected)} models...",
            text_color="#FF9800"
        )
        self.update()  # Force UI update

        try:
            updater = ModelUpdater()
            results = updater.update_models(selected, str(self.models_dir))  # Pass models directory

            # Process results
            success = sum(1 for r in results.values() if r.get("success", False))
            self.model_update_status.configure(
                text=f"Completed: {success}/{len(selected)} succeeded",
                text_color="#4CAF50" if success == len(selected) else "#FF9800"
            )

            # Re-verify models
            self._verify_models()

            # Reload UI if needed
            if success > 0 and hasattr(self, 'model_menu'):
                self.model_menu.configure(values=self.available_models)

        except Exception as e:
            self.model_update_status.configure(
                text=f"Download failed: {str(e)}",
                text_color="#FF5252"
            )

        # Dynamic preset loader
    def _update_presets(self):
        """Update presets based on current voice selection"""
        try:
            if not hasattr(self, 'preset_menu') or not self.preset_menu:
                return

            voice = self.voice_var.get()
            if not voice:
                return

            if '(' in voice:  # Multi-language format: "Russian (aidar)"
                lang = voice.split('(')[0].strip().lower()
            else:
                lang = 'en'  # Default

            filtered_presets = [
                f"{name} [{lang}]"
                for name, texts in self.presets.items()
                if lang in texts or 'default' in texts
            ]

            if hasattr(self, 'preset_menu'):
                self.preset_menu.configure(values=filtered_presets)

        except Exception as e:
            print(f"Preset update error: {e}")

    # 2. Fix the presets loading in _update_preset_options:
    def _update_preset_options(self, *args):
        """Refresh preset dropdown options"""
        try:
            category = self.category_var.get()
            if not category or not hasattr(self, 'presets'):
                return

            presets = self.presets.get(category, {})
            preset_names = list(presets.keys())

            # Auto-select first preset if none selected
            if preset_names and not self.preset_var.get():
                self.preset_var.set(preset_names[0])
                self._load_preset(preset_names[0])

            self.preset_menu.configure(values=preset_names)

            # Show "Untitled" only if there's text and no real preset selected
            current_text = self.text_input.get("1.0", "end-1c").strip()
            if current_text and (not self.preset_var.get() or self.preset_var.get() == "Untitled"):
                if "Untitled" not in preset_names:
                    preset_names.insert(0, "Untitled")

            # Maintain current selection if it exists
            if self.preset_var.get() in preset_names:
                self.preset_var.set(self.preset_var.get())
            elif current_text:
                self.preset_var.set(f"Untitled")
            else:
                self.preset_var.set("")

        except Exception as e:
            print(f"Preset update error: {e}")
            self.preset_menu.configure(values=[])

    def _smart_play(self):
        if self.is_playing:
            sd.stop()
            self.is_playing = False
            self.play_btn.configure(image=self.icons.get("play", (16,16)), text="Play")  # If keeping text
            return

        text = self.text_input.get("1.0", "end-1c").strip()
        if not text:
            self.status_var.set(f"Error: Enter text first")
            return

        self.progress.set(0)
        self.status_var.set(f"Synthesizing...")
        self.play_btn.configure(state="disabled")
        self.update()

        threading.Thread(
            target=self._generate_and_play,
            args=(text,),
            daemon=True
        ).start()

    def _export_audio(self):
        if self.audio_data is None:
            self.status_var.set(f"Generate audio first")
            return

        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".wav",
                filetypes=[(f"WAV files", f"*.wav")]
            )
            if file_path:
                sf.write(file_path, self.audio_data, 48000)
                self.status_var.set(f"Exported: {os.path.basename(file_path)}")
        except Exception as e:
            self.status_var.set(f"Export failed: {str(e)}")

    def _on_close(self):
        """Handle window closing"""
        # Clean up tooltips
        for tip in self.tooltips:
            try:
                tip.destroy()
            except:
                pass
        # Add to existing cleanup:
        if hasattr(self, 'icons'):
            for img in self.icons._cache.values():
                try:
                    img.close()  # Properly close CTkImage resources
                except:
                    pass

        # Only try to stop TTS if it was initialized
        if hasattr(self, 'tts'):
            if hasattr(self.tts, 'watcher') and self.tts.watcher:
                self.tts.watcher.stop()

        """Clean up resources"""
        # Stop any active playback
        if hasattr(self, 'is_playing') and self.is_playing:
            sd.stop()

        # Close matplotlib figure
        if hasattr(self, 'fig'):
            plt.close(self.fig)

        # Destroy window
        self.destroy()
