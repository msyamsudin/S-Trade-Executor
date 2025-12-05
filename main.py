import customtkinter as ctk
import threading
import time
import ctypes
import ctypes.wintypes
import tkinter as tk
from pynput import mouse, keyboard
from executor import Executor
from config_manager import ConfigManager

# ========== THEME CONFIGURATION ==========
ctk.set_appearance_mode("Dark")

# Modern color palette
COLORS = {
    "bg_dark": "#09090b",      # Zinc 950
    "bg_card": "#18181b",      # Zinc 900
    "bg_card_hover": "#27272a", # Zinc 800
    "accent": "#fafafa",       # Zinc 50 (White)
    "accent_hover": "#e4e4e7", # Zinc 200
    "accent_secondary": "#52525b", # Zinc 600
    "text_primary": "#fafafa", # Zinc 50
    "text_secondary": "#a1a1aa", # Zinc 400
    "success": "#fafafa",      # Zinc 50 (White for active)
    "warning": "#d4d4d8",      # Zinc 300
    "danger": "#3f3f46",       # Zinc 700
    "border": "#27272a"        # Zinc 800
}

class CoordRow(ctk.CTkFrame):
    """A compact coordinate chip with pick and delete buttons."""
    def __init__(self, master, x=0, y=0, on_pick=None, on_delete=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_pick = on_pick
        self.on_delete = on_delete
        
        # Compact coordinate chip
        coord_text = f"{x},{y}" if x != 0 or y != 0 else "Pick"
        self.coord_btn = ctk.CTkButton(
            self, 
            text=coord_text, 
            width=70, 
            height=24,
            fg_color=COLORS["bg_card_hover"],
            hover_color=COLORS["accent"],
            border_width=1,
            border_color=COLORS["border"],
            corner_radius=12,
            font=ctk.CTkFont(size=11),
            command=self._pick
        )
        self.coord_btn.pack(side="left", padx=(0, 2))
        
        self.del_btn = ctk.CTkButton(
            self, 
            text="×", 
            width=20, 
            height=24,
            fg_color="transparent",
            hover_color=COLORS["danger"],
            text_color=COLORS["text_secondary"],
            corner_radius=12,
            font=ctk.CTkFont(size=14),
            command=self._delete
        )
        self.del_btn.pack(side="left")
    
    def _pick(self):
        self.coord_btn.configure(text="...", fg_color=COLORS["warning"])
        if self.on_pick:
            self.on_pick(self)
    
    def _delete(self):
        if self.on_delete:
            self.on_delete(self)
    
    def get_coord(self):
        text = self.coord_btn.cget("text")
        if text in ["Pick", "..."]:
            return (0, 0)
        parts = text.split(',')
        return (int(parts[0]), int(parts[1]))
    
    def set_coord(self, x, y):
        self.coord_btn.configure(text=f"{x},{y}", fg_color=COLORS["bg_card_hover"])

class ActionFrame(ctk.CTkFrame):
    """Card-style action frame with modern styling."""
    def __init__(self, master, action_data, delete_callback, pick_callback, bind_callback, test_callback, on_change_callback=None, **kwargs):
        super().__init__(
            master, 
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
            **kwargs
        )
        self.action_data = action_data
        self.delete_callback = delete_callback
        self.pick_callback = pick_callback
        self.bind_callback = bind_callback
        self.test_callback = test_callback
        self.on_change_callback = on_change_callback
        self.coord_rows = []
        self._burst_notified = action_data.get("mode", "Single") == "Burst"  # Already notified if loaded as Burst
        self._burst_pulse_running = False

        # Card Header - compact single row
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=(8, 4))
        
        # Name entry - smaller
        self.name_entry = ctk.CTkEntry(
            self.header_frame, 
            width=100, 
            height=28,
            placeholder_text="Name",
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            corner_radius=6,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.name_entry.insert(0, action_data.get("name", "Action"))
        self.name_entry.pack(side="left", padx=(0, 6))
        self.name_entry.bind("<FocusOut>", lambda e: self._on_change())
        self.name_entry.bind("<Return>", lambda e: self._on_change())

        # Hotkey button - compact pill
        hotkey_text = action_data.get("hotkey", "Bind Key")
        self.hotkey_btn = ctk.CTkButton(
            self.header_frame, 
            text=f"⌨ {hotkey_text}", 
            width=80,
            height=28,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#09090b",
            corner_radius=14,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self.bind_hotkey
        )
        self.hotkey_btn.pack(side="left", padx=2)

        # Test button - with label for clarity
        self.test_btn = ctk.CTkButton(
            self.header_frame, 
            text="▶ Test", 
            width=60,
            height=28,
            fg_color=COLORS["warning"],
            hover_color="#a1a1aa",
            text_color="#09090b",
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda: test_callback(self)
        )
        self.test_btn.pack(side="left", padx=2)

        # Delete button - compact
        self.del_btn = ctk.CTkButton(
            self.header_frame, 
            text="🗑", 
            width=28,
            height=28,
            fg_color="transparent",
            hover_color=COLORS["danger"],
            corner_radius=6,
            command=lambda: delete_callback(self)
        )
        self.del_btn.pack(side="right")
        
        # Enable/Disable toggle button
        self.is_enabled = action_data.get("enabled", True)
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="●" if self.is_enabled else "○",
            width=28,
            height=28,
            fg_color=COLORS["success"] if self.is_enabled else COLORS["bg_card_hover"],
            hover_color="#e4e4e7" if self.is_enabled else COLORS["border"],
            text_color="#09090b" if self.is_enabled else COLORS["text_secondary"],
            corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=self._toggle_enabled
        )
        self.toggle_btn.pack(side="right", padx=(0, 4))

        # Settings row - compact inline
        self.settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.settings_frame.pack(fill="x", padx=10, pady=2)
        
        # Mode selector - compact
        self.mode_label = ctk.CTkLabel(
            self.settings_frame, 
            text="Mode:", 
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.mode_label.pack(side="left")
        
        self.mode_menu = ctk.CTkOptionMenu(
            self.settings_frame, 
            values=["Single", "Double", "Burst"], 
            width=75,
            height=24,
            fg_color=COLORS["bg_dark"],
            button_color=COLORS["bg_card_hover"],
            button_hover_color=COLORS["accent"],
            dropdown_fg_color=COLORS["bg_card"],
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=self._on_mode_change
        )
        self.mode_menu.set(action_data.get("mode", "Single"))
        self.mode_menu.pack(side="left", padx=(2, 2))
        
        # Burst count entry - only visible when Burst mode selected
        self.burst_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.burst_frame.pack(side="left", padx=(0, 8))
        
        self.burst_label = ctk.CTkLabel(
            self.burst_frame,
            text="×",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.burst_label.pack(side="left")
        
        self.burst_entry = ctk.CTkEntry(
            self.burst_frame,
            width=35,
            height=24,
            placeholder_text="5",
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.burst_entry.insert(0, str(action_data.get("burst_count", 5)))
        self.burst_entry.pack(side="left", padx=(2, 0))
        self.burst_entry.bind("<FocusOut>", lambda e: self._on_change())
        self.burst_entry.bind("<Return>", lambda e: self._on_change())
        
        # Initially hide burst frame if not Burst mode, or apply burst styling
        if action_data.get("mode", "Single") == "Burst":
            # Apply burst mode styling
            self.mode_menu.configure(
                fg_color="#3f3f46",  # Zinc 700
                button_color="#52525b",  # Zinc 600
                button_hover_color="#71717a"  # Zinc 500
            )
            self.burst_entry.configure(
                border_color="#52525b",
                fg_color="#27272a"  # Zinc 800
            )
            self.burst_label.configure(text_color="#a1a1aa")
            # Change card styling for burst mode
            self.configure(
                border_color="#52525b", 
                border_width=1,
                fg_color="#27272a"  # Zinc 800
            )
            # Start pulse animation
            self._start_burst_pulse()
        else:
            self.burst_frame.pack_forget()
        
        # Delay entry - compact
        self.delay_label = ctk.CTkLabel(
            self.settings_frame, 
            text="Delay:", 
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.delay_label.pack(side="left")
        
        self.delay_entry = ctk.CTkEntry(
            self.settings_frame, 
            width=50, 
            height=24,
            placeholder_text="ms",
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            corner_radius=6,
            font=ctk.CTkFont(size=11)
        )
        self.delay_entry.insert(0, str(action_data.get("delay_ms", 100)))
        self.delay_entry.pack(side="left", padx=(2, 2))
        self.delay_entry.bind("<FocusOut>", lambda e: self._on_change())
        self.delay_entry.bind("<Return>", lambda e: self._on_change())
        self.delay_entry.bind("<KeyRelease>", lambda e: self._update_delay_display())
        
        # Dynamic delay display
        self.delay_display = ctk.CTkLabel(
            self.settings_frame, 
            text=self._format_delay(action_data.get("delay_ms", 100)), 
            font=ctk.CTkFont(size=10),
            text_color=COLORS["accent"],
            width=50
        )
        self.delay_display.pack(side="left")

        # Coordinates section - wrap/flow layout
        self.coords_section = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=6)
        self.coords_section.pack(fill="x", padx=10, pady=(4, 8))
        
        # Header row with label and add button
        self.coords_header = ctk.CTkFrame(self.coords_section, fg_color="transparent")
        self.coords_header.pack(fill="x", padx=6, pady=(6, 2))
        
        self.coords_label = ctk.CTkLabel(
            self.coords_header, 
            text="📍 Coordinates", 
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.coords_label.pack(side="left")
        
        self.add_coord_btn = ctk.CTkButton(
            self.coords_header, 
            text="+", 
            width=24,
            height=24,
            fg_color=COLORS["success"],
            hover_color="#e4e4e7",
            text_color="#09090b",
            corner_radius=12,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.add_coord_row
        )
        self.add_coord_btn.pack(side="right")
        
        # Wrap frame for coordinates (using grid layout)
        self.coords_frame = ctk.CTkFrame(self.coords_section, fg_color="transparent")
        self.coords_frame.pack(fill="x", padx=6, pady=(2, 6))
        self.COORDS_PER_ROW = 4  # Max coordinates per row
        
        # Load existing coords or add default
        coords = action_data.get("coords", [])
        if not coords:
            coords = [{"x": action_data.get("x", 0), "y": action_data.get("y", 0)}]
        
        for c in coords:
            self._add_coord_row_internal(c.get("x", 0), c.get("y", 0))

    def add_coord_row(self):
        self._add_coord_row_internal(0, 0)
        self._reflow_coords()
        self._on_change()
    
    def _add_coord_row_internal(self, x, y):
        row = CoordRow(self.coords_frame, x, y, on_pick=self._on_coord_pick, on_delete=self._on_coord_delete)
        self.coord_rows.append(row)
        self._reflow_coords()
    
    def _reflow_coords(self):
        """Reposition all coord chips in a wrap/grid layout."""
        for widget in self.coords_frame.winfo_children():
            widget.grid_forget()
        
        for i, row in enumerate(self.coord_rows):
            grid_row = i // self.COORDS_PER_ROW
            grid_col = i % self.COORDS_PER_ROW
            row.grid(row=grid_row, column=grid_col, padx=2, pady=2, sticky="w")
    
    def _on_coord_pick(self, coord_row):
        self.pick_callback(coord_row)
    
    def _on_coord_delete(self, coord_row):
        if len(self.coord_rows) > 1:
            self.coord_rows.remove(coord_row)
            coord_row.destroy()
            self._reflow_coords()
            self._on_change()

    def bind_hotkey(self):
        self.hotkey_btn.configure(text="⌨ ...", fg_color=COLORS["warning"])
        self.bind_callback(self)

    def get_data(self):
        coords = [{"x": r.get_coord()[0], "y": r.get_coord()[1]} for r in self.coord_rows]
        try:
            delay_ms = int(self.delay_entry.get())
        except ValueError:
            delay_ms = 100
        try:
            burst_count = int(self.burst_entry.get())
            if burst_count < 1:
                burst_count = 1
        except ValueError:
            burst_count = 5
        return {
            "name": self.name_entry.get(),
            "hotkey": self.hotkey_btn.cget("text").replace("⌨️ ", "").replace("⌨ ", ""),
            "coords": coords,
            "mode": self.mode_menu.get(),
            "delay_ms": delay_ms,
            "burst_count": burst_count,
            "enabled": self.is_enabled
        }
    
    def _toggle_enabled(self):
        """Toggle action enabled/disabled state."""
        self.is_enabled = not self.is_enabled
        if self.is_enabled:
            self.toggle_btn.configure(
                text="●",
                fg_color=COLORS["success"],
                text_color="#09090b",
                hover_color="#e4e4e7"
            )
            # Restore normal card appearance
            self.configure(fg_color=COLORS["bg_card"])
        else:
            self.toggle_btn.configure(
                text="○",
                fg_color=COLORS["bg_card_hover"],
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["border"]
            )
            # Dim the card when disabled
            self.configure(fg_color="#09090b")
        self._on_change()
    
    def _on_mode_change(self, mode):
        """Handle mode change - show/hide burst count input and update colors."""
        if mode == "Burst":
            # Show burst frame after mode menu
            self.burst_frame.pack(side="left", padx=(0, 8), after=self.mode_menu)
            # Change to danger/warning colors for burst mode
            self.mode_menu.configure(
                fg_color="#3f3f46",  # Zinc 700
                button_color="#52525b",  # Zinc 600
                button_hover_color="#71717a"  # Zinc 500
            )
            self.burst_entry.configure(
                border_color="#52525b",
                fg_color="#27272a"
            )
            self._start_burst_pulse()
            if not self._burst_notified:
                self._burst_notified = True
                self._show_burst_notification()
        else:
            self.burst_frame.pack_forget()
            # Stop pulse animation
            self._stop_burst_pulse()
            # Hide notification if exists
            self._hide_burst_notification()
            # Reset to normal colors
            self.mode_menu.configure(
                fg_color=COLORS["bg_dark"],
                button_color=COLORS["bg_card_hover"],
                button_hover_color=COLORS["accent"]
            )
            # Reset coordinate buttons to normal
            for coord_row in self.coord_rows:
                coord_row.coord_btn.configure(
                    fg_color=COLORS["bg_card_hover"],
                    border_color=COLORS["border"]
                )
            # Reset card to normal
            self.configure(
                border_color=COLORS["border"], 
                border_width=1,
                fg_color=COLORS["bg_card"]
            )
        self._on_change()
    
    def _start_burst_pulse(self):
        """Start pulsing animation for burst mode."""
        self._burst_pulse_running = True
        self._burst_pulse_state = 0
        self._pulse_burst_card()
    
    def _pulse_burst_card(self):
        """Animate the card background with a subtle pulse."""
        if not self._burst_pulse_running:
            return
        
        try:
            # Pulse between dark red shades
            colors = ["#450a0a", "#551010", "#601515", "#551010"] # Dark Red Pulse
            color = colors[self._burst_pulse_state % len(colors)]
            self.configure(fg_color=color)
            self._burst_pulse_state += 1
            self._burst_pulse_id = self.after(400, self._pulse_burst_card)
        except:
            pass
    
    def _stop_burst_pulse(self):
        """Stop the burst pulse animation."""
        self._burst_pulse_running = False
        if hasattr(self, '_burst_pulse_id'):
            try:
                self.after_cancel(self._burst_pulse_id)
            except:
                pass
    
    def _show_burst_notification(self):
        """Show a persistent notification about burst mode."""
        # Create notification label (persistent while burst mode is active)
        self.burst_notice = ctk.CTkLabel(
            self.header_frame,
            text="⚠️ Burst Mode",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#fafafa",
            fg_color="#3f3f46",
            corner_radius=4,
            padx=6,
            pady=2
        )
        self.burst_notice.pack(side="right", padx=5)
    
    def _hide_burst_notification(self):
        """Hide the burst notification."""
        if hasattr(self, 'burst_notice') and self.burst_notice:
            try:
                self.burst_notice.destroy()
                self.burst_notice = None
                self._burst_notified = False  # Allow notification to show again if burst is reselected
            except:
                pass
    
    def _on_change(self):
        if self.on_change_callback:
            self.on_change_callback()
    
    def _format_delay(self, ms):
        """Format milliseconds with seconds conversion."""
        try:
            ms = int(ms)
            if ms >= 1000:
                seconds = ms / 1000
                if seconds == int(seconds):
                    return f"= {int(seconds)}s"
                else:
                    return f"= {seconds:.1f}s"
            else:
                return f"= {ms}ms"
        except (ValueError, TypeError):
            return ""
    
    def _update_delay_display(self):
        """Update the delay display label in realtime."""
        try:
            ms = self.delay_entry.get()
            self.delay_display.configure(text=self._format_delay(ms))
        except:
            pass

class CustomTitleBar(ctk.CTkFrame):
    def __init__(self, master, title="", close_command=None, minimize_command=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self, text=title, font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.title_label.pack(side="left", padx=10)
        
        # Buttons
        self.close_btn = ctk.CTkButton(
            self, text="×", width=40, height=30,
            fg_color="transparent", hover_color="#c42b1c",
            text_color=COLORS["text_primary"],
            command=close_command if close_command else master.destroy
        )
        self.close_btn.pack(side="right")
        
        if minimize_command:
            self.min_btn = ctk.CTkButton(
                self, text="-", width=40, height=30,
                fg_color="transparent", hover_color=COLORS["bg_card_hover"],
                text_color=COLORS["text_primary"],
                command=minimize_command
            )
            self.min_btn.pack(side="right")
        
        # Drag bindings
        self.bind("<Button-1>", self.start_drag)
        self.bind("<B1-Motion>", self.do_drag)
        self.title_label.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<B1-Motion>", self.do_drag)
        
    def start_drag(self, event):
        self.x_offset = event.x
        self.y_offset = event.y
        
    def do_drag(self, event):
        window = self.winfo_toplevel()
        x = window.winfo_x() + (event.x - self.x_offset)
        y = window.winfo_y() + (event.y - self.y_offset)
        window.geometry(f"+{x}+{y}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("S-Trade-Executor")
        self.overrideredirect(True) # Remove default title bar
        
        # Border color (using accent_secondary or specific border color)
        self.configure(fg_color=COLORS["border"]) 
        self.attributes("-topmost", True)
        
        self.initial_position_set = False
        
        # Height calculation constants
        self.TITLE_BAR_HEIGHT = 30
        self.HEADER_HEIGHT = 56
        self.STATUS_HEIGHT = 40
        self.CARD_HEIGHT = 160  # Approximate height per action card
        self.CARD_PADDING = 12
        self.MIN_HEIGHT = 300
        self.MAX_CARDS_VISIBLE = 3
        
        self.executor = Executor()
        self.config_manager = ConfigManager()
        self.actions = []
        
        self.picking_coord_row = None
        self.binding_action = None
        self.is_paused = False
        
        self.setup_ui()
        self.load_config()
        self._update_window_height()  # Set initial height
        
        self.executor.set_status_callback(self.update_status_safe)
        self.executor.click_indicator_callback = self._show_click_indicator
        self.executor.execution_start_callback = self._on_execution_start
        self.executor.execution_end_callback = self._on_execution_end
        self.executor.start_listening()
        self.update_state_display()
        
        # Glow effect for cursor during execution
        self._cursor_glow = None
        self._glow_running = False
        
        # Test indicators
        self.test_indicators = []
        self.active_test_card = None

    def setup_ui(self):
        # Container for border effect
        self.main_container = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.main_container.pack(fill="both", expand=True, padx=1, pady=1)
        
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(3, weight=1) # Scroll frame is now row 3

        # ===== TITLE BAR =====
        self.title_bar = CustomTitleBar(
            self.main_container, 
            title="S-Trade-Executor", 
            height=30,
            close_command=self.on_closing,
            minimize_command=self.iconify
        )
        self.title_bar.grid(row=0, column=0, sticky="ew")

        # ===== HEADER =====
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color=COLORS["bg_card"], corner_radius=0)
        self.header_frame.grid(row=1, column=0, sticky="ew")
        
        self.pause_btn = ctk.CTkButton(
            self.header_frame, 
            text="● Active", 
            width=90,
            height=32,
            fg_color=COLORS["success"],
            hover_color="#e4e4e7",
            text_color="#09090b",
            corner_radius=16,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.toggle_pause
        )
        self.pause_btn.pack(side="left", padx=15, pady=12)

        self.add_btn = ctk.CTkButton(
            self.header_frame, 
            text="+ New Action", 
            width=100,
            height=32,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#09090b",
            corner_radius=8,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.add_action
        )
        self.add_btn.pack(side="right", padx=(10, 25), pady=12)
        
        self.help_btn = ctk.CTkButton(
            self.header_frame, 
            text="?", 
            width=32,
            height=32,
            fg_color="transparent",
            hover_color=COLORS["bg_card_hover"],
            text_color=COLORS["text_secondary"],
            corner_radius=16,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.show_help
        )
        self.help_btn.pack(side="right", padx=(0, 5), pady=12)

        # ===== ACTION LIST =====
        self.scroll_frame = ctk.CTkScrollableFrame(
            self.main_container, 
            fg_color="transparent",
            scrollbar_button_color=COLORS["bg_card_hover"],
            scrollbar_button_hover_color=COLORS["accent"]
        )
        self.scroll_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=5)

        # ===== STATUS BAR =====
        self.status_frame = ctk.CTkFrame(self.main_container, fg_color=COLORS["bg_card"], corner_radius=0)
        self.status_frame.grid(row=4, column=0, sticky="ew")
        
        self.state_indicator = ctk.CTkLabel(
            self.status_frame, 
            text="●", 
            font=ctk.CTkFont(size=14),
            text_color=COLORS["success"]
        )
        self.state_indicator.pack(side="left", padx=(15, 5), pady=8)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame, 
            text="Ready",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", pady=8)
        
        self.version_label = ctk.CTkLabel(
            self.status_frame, 
            text="v1.0",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.version_label.pack(side="right", padx=15, pady=8)
        
        # Cancel on mouse move toggle
        self.cancel_mouse_var = ctk.BooleanVar(value=False)
        self.cancel_mouse_switch = ctk.CTkSwitch(
            self.status_frame,
            text="Cancel on Move",
            variable=self.cancel_mouse_var,
            command=self._toggle_cancel_on_move,
            width=40,
            height=20,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"],
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["accent"]
        )
        self.cancel_mouse_switch.pack(side="right", padx=(0, 10), pady=8)
    
    def _toggle_cancel_on_move(self):
        """Toggle cancel on mouse move feature."""
        self.executor.cancel_on_mouse_move = self.cancel_mouse_var.get()
        state = "enabled" if self.cancel_mouse_var.get() else "disabled"
        self.status_label.configure(text=f"Cancel on move {state}")

    def add_action(self, data=None, is_new=False):
        if data is None:
            data = {"name": "New Action", "hotkey": "Bind Key", "coords": [{"x": 0, "y": 0}], "mode": "Single", "delay_ms": 1000}
            is_new = True
        
        frame = ActionFrame(
            self.scroll_frame, 
            data, 
            self.delete_action, 
            self.start_picking, 
            self.wait_for_hotkey, 
            self.test_action, 
            on_change_callback=self._on_action_change
        )
        frame.pack(fill="x", pady=6)
        self.actions.append(frame)
        self._update_window_height()
        self.auto_save()
        
        # Auto-start guided flow for new actions
        if is_new:
            # Start with hotkey binding first
            self.after(100, lambda: self._start_guided_setup(frame))

    def test_action(self, action_frame):
        # Toggle logic: If clicking same card, clear it. If different, clear old and show new.
        if self.active_test_card == action_frame:
            self._clear_test_indicators()
            self.active_test_card = None
            self.status_label.configure(text="Test cleared")
            return

        self._clear_test_indicators()
        self.active_test_card = action_frame
        
        data = action_frame.get_data()
        coords = data.get('coords', [])
        
        for i, coord in enumerate(coords):
            # No delay for showing all at once, or small delay for effect
            self.after(i * 50, lambda c=coord, idx=i+1: self._show_crosshair(c['x'], c['y'], idx))
        
        self.status_label.configure(text=f"Testing {len(coords)} coordinate(s) - Click Test again to hide")

    def _clear_test_indicators(self):
        """Clear all active test indicators."""
        for indicator in self.test_indicators:
            try:
                indicator.destroy()
            except:
                pass
        self.test_indicators.clear()

    def _show_crosshair(self, x, y, index=None):
        size = 50
        half = size // 2
        
        indicator = ctk.CTkToplevel(self)
        indicator.geometry(f"{size}x{size}+{x-half}+{y-half}")
        indicator.overrideredirect(True)
        indicator.attributes("-topmost", True)
        indicator.attributes("-transparentcolor", "black")
        indicator.configure(fg_color="black")
        
        # Add to list
        self.test_indicators.append(indicator)
        
        canvas = tk.Canvas(indicator, width=size, height=size, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        line_color = COLORS["accent"]
        canvas.create_line(0, half, size, half, fill=line_color, width=2)
        canvas.create_line(half, 0, half, size, fill=line_color, width=2)
        canvas.create_oval(half-5, half-5, half+5, half+5, outline=line_color, width=2)
        canvas.create_oval(half-20, half-20, half+20, half+20, outline=line_color, width=1)
        
        if index is not None:
            # Draw sequence number
            canvas.create_text(
                half + 10, half - 10, 
                text=str(index), 
                fill=COLORS["accent"], 
                font=("Arial", 12, "bold")
            )
            
        # Click to dismiss this specific indicator (optional, but good UX)
        indicator.bind("<Button-1>", lambda e: self._dismiss_indicator(indicator))
        canvas.bind("<Button-1>", lambda e: self._dismiss_indicator(indicator))
    
    def _dismiss_indicator(self, indicator):
        try:
            indicator.destroy()
            if indicator in self.test_indicators:
                self.test_indicators.remove(indicator)
            if not self.test_indicators:
                self.active_test_card = None
        except:
            pass
    
    def _show_click_indicator(self, x, y):
        """Show a quick visual indicator at click position during autoclick."""
        # Use after to run on main thread since this is called from executor thread
        self.after(0, lambda: self._create_click_ripple(x, y))
    
    def _create_click_ripple(self, x, y):
        """Create ripple effect at click position."""
        size = 40
        half = size // 2
        
        try:
            indicator = ctk.CTkToplevel(self)
            indicator.geometry(f"{size}x{size}+{x-half}+{y-half}")
            indicator.overrideredirect(True)
            indicator.attributes("-topmost", True)
            indicator.attributes("-transparentcolor", "black")
            indicator.configure(fg_color="black")
            
            canvas = tk.Canvas(indicator, width=size, height=size, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            
            # Create expanding ring effect
            ring_color = COLORS["success"]
            ring = canvas.create_oval(half-5, half-5, half+5, half+5, outline=ring_color, width=3)
            
            def expand(step=0):
                if step >= 12:
                    try:
                        indicator.destroy()
                    except:
                        pass
                    return
                try:
                    # Expand the ring
                    expand_size = 5 + step * 2
                    canvas.coords(ring, 
                        half - expand_size, half - expand_size,
                        half + expand_size, half + expand_size)
                    # Fade out
                    indicator.attributes("-alpha", 1.0 - (step * 0.08))
                    self.after(40, lambda: expand(step + 1))
                except:
                    pass
            
            expand()
        except:
            pass
    
    def _on_execution_start(self):
        """Called when autoclick execution starts."""
        self.after(0, self._create_cursor_glow)
    
    def _on_execution_end(self):
        """Called when autoclick execution ends."""
        self.after(0, self._destroy_cursor_glow)
    
    def _create_cursor_glow(self):
        """Create a glow effect that follows the cursor."""
        if self._cursor_glow:
            return  # Already exists
        
        self._glow_running = True
        size = 60
        
        try:
            glow = ctk.CTkToplevel(self)
            glow.overrideredirect(True)
            glow.attributes("-topmost", True)
            glow.attributes("-transparentcolor", "black")
            glow.configure(fg_color="black")
            glow.geometry(f"{size}x{size}")
            
            canvas = tk.Canvas(glow, width=size, height=size, bg="black", highlightthickness=0)
            canvas.pack(fill="both", expand=True)
            
            half = size // 2
            # Create glow rings
            glow_color = COLORS["success"]
            canvas.create_oval(half-20, half-20, half+20, half+20, outline=glow_color, width=2)
            canvas.create_oval(half-15, half-15, half+15, half+15, outline=glow_color, width=2)
            canvas.create_oval(half-8, half-8, half+8, half+8, outline=glow_color, width=3)
            
            self._cursor_glow = glow
            self._glow_canvas = canvas
            self._glow_size = size
            
            # Start position update loop
            self._update_glow_position()
            
            # Start pulsing effect
            self._glow_pulse_state = 0
            self._pulse_glow()
        except Exception as e:
            print(f"Failed to create cursor glow: {e}")
    
    def _update_glow_position(self):
        """Update glow position to follow cursor."""
        if not self._glow_running or not self._cursor_glow:
            return
        
        try:
            # Get current mouse position
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            x, y = pt.x, pt.y
            
            half = self._glow_size // 2
            self._cursor_glow.geometry(f"{self._glow_size}x{self._glow_size}+{x-half}+{y-half}")
            
            # Continue updating
            self.after(16, self._update_glow_position)  # ~60fps
        except:
            pass
    
    def _pulse_glow(self):
        """Pulsing animation for the glow."""
        if not self._glow_running or not self._cursor_glow:
            return
        
        try:
            # Pulse between 0.5 and 1.0 alpha
            alpha = 0.6 + 0.4 * (1 + __import__('math').sin(self._glow_pulse_state * 0.2)) / 2
            self._cursor_glow.attributes("-alpha", alpha)
            self._glow_pulse_state += 1
            
            self.after(50, self._pulse_glow)
        except:
            pass
    
    def _destroy_cursor_glow(self):
        """Destroy the cursor glow effect."""
        self._glow_running = False
        if self._cursor_glow:
            try:
                self._cursor_glow.destroy()
            except:
                pass
            self._cursor_glow = None

    def delete_action(self, frame):
        # Stop any running animations
        self._stop_blinking()
        self._stop_status_blinking()
        self._guided_action = None
        self._blinking_coord_row = None
        
        frame.destroy()
        self.actions.remove(frame)
        self._update_window_height()
        self.refresh_executor()
        self.auto_save()
        
        # Reset status to ready state
        self.update_state_display()
    
    def _update_window_height(self):
        """Dynamically adjust window height based on number of cards (max 3 visible)."""
        num_cards = min(len(self.actions), self.MAX_CARDS_VISIBLE)
        if num_cards == 0:
            content_height = 50  # Empty state height
        else:
            content_height = (self.CARD_HEIGHT + self.CARD_PADDING) * num_cards
        
        total_height = self.TITLE_BAR_HEIGHT + self.HEADER_HEIGHT + content_height + self.STATUS_HEIGHT + 20
        total_height = max(total_height, self.MIN_HEIGHT)
        
        if not self.initial_position_set:
            # Calculate center position
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            window_width = 520
            
            x = (screen_width - window_width) // 2
            y = (screen_height - total_height) // 2
            
            self.geometry(f"{window_width}x{total_height}+{x}+{y}")
            self.initial_position_set = True
        else:
            # Keep current position, just update size
            self.geometry(f"520x{total_height}")

    def start_picking(self, coord_row):
        self.picking_coord_row = coord_row
        self.status_label.configure(text="🎯 Middle-click to pick coordinate...")
        
        self.mouse_listener = mouse.Listener(on_click=self.on_pick_click)
        self.mouse_listener.start()

    def on_pick_click(self, x, y, button, pressed):
        if not pressed:
            return
        
        if button == mouse.Button.middle:
            if self.picking_coord_row:
                # Stop blinking animations if running
                if hasattr(self, '_blinking_coord_row') and self._blinking_coord_row:
                    self._stop_blinking(self._blinking_coord_row.coord_btn, COLORS["bg_card_hover"])
                    self._blinking_coord_row = None
                self._stop_status_blinking()
                
                self.picking_coord_row.set_coord(int(x), int(y))
                self.picking_coord_row = None
                self.status_label.configure(text="✅ Coordinate set! Setup complete.", text_color=COLORS["success"])
                
                # Reset status color after delay
                self.after(2000, lambda: self.status_label.configure(text_color=COLORS["text_secondary"]))
                
                self.refresh_executor()
                self.auto_save()
            return False

    def wait_for_hotkey(self, action_frame):
        self.binding_action = action_frame
        self.status_label.configure(text="⌨️ Press any key to bind...")
        threading.Thread(target=self._listen_for_key).start()
    
    def _start_blinking(self, widget, attr="fg_color", color1=None, color2=None, interval=400):
        """Start blinking animation on a widget. Returns animation ID."""
        if color1 is None:
            color1 = COLORS["warning"]
        if color2 is None:
            color2 = COLORS["accent_secondary"]
        
        self._blink_state = True
        
        def blink():
            if not hasattr(self, '_blink_running') or not self._blink_running:
                return
            try:
                if attr == "fg_color":
                    widget.configure(fg_color=color1 if self._blink_state else color2)
                elif attr == "text_color":
                    widget.configure(text_color=color1 if self._blink_state else color2)
                self._blink_state = not self._blink_state
                self._blink_id = self.after(interval, blink)
            except:
                pass
        
        self._blink_running = True
        blink()
    
    def _stop_blinking(self, widget=None, restore_color=None, attr="fg_color"):
        """Stop blinking animation."""
        self._blink_running = False
        if hasattr(self, '_blink_id'):
            try:
                self.after_cancel(self._blink_id)
            except:
                pass
        if widget and restore_color:
            try:
                if attr == "fg_color":
                    widget.configure(fg_color=restore_color)
                elif attr == "text_color":
                    widget.configure(text_color=restore_color)
            except:
                pass
    
    def _start_status_blinking(self, text, interval=500):
        """Start blinking status text."""
        self._status_blink_state = True
        self._status_text = text
        
        def blink_status():
            if not hasattr(self, '_status_blink_running') or not self._status_blink_running:
                return
            try:
                if self._status_blink_state:
                    self.status_label.configure(text=self._status_text, text_color=COLORS["warning"])
                else:
                    self.status_label.configure(text=self._status_text, text_color=COLORS["accent"])
                self._status_blink_state = not self._status_blink_state
                self._status_blink_id = self.after(interval, blink_status)
            except:
                pass
        
        self._status_blink_running = True
        blink_status()
    
    def _stop_status_blinking(self):
        """Stop status blinking."""
        self._status_blink_running = False
        if hasattr(self, '_status_blink_id'):
            try:
                self.after_cancel(self._status_blink_id)
            except:
                pass
        self.status_label.configure(text_color=COLORS["text_secondary"])
    
    def _start_guided_setup(self, action_frame):
        """Start guided setup flow for new action: bind key first, then coordinate."""
        self._guided_action = action_frame
        action_frame.hotkey_btn.configure(text="⌨ ...", fg_color=COLORS["warning"])
        
        # Start blinking animations
        self._start_blinking(action_frame.hotkey_btn, "fg_color", COLORS["warning"], COLORS["accent_secondary"])
        self._start_status_blinking("Step 1/2: ⌨️ Press hotkey to bind...")
        
        threading.Thread(target=self._listen_for_key_guided).start()
    
    def _listen_for_key_guided(self):
        """Listen for hotkey during guided setup."""
        import keyboard
        key = keyboard.read_hotkey(suppress=False)
        if hasattr(self, '_guided_action') and self._guided_action:
            action_frame = self._guided_action
            
            # Stop blinking and restore
            self.after(0, lambda: self._stop_blinking(action_frame.hotkey_btn, COLORS["accent"]))
            self.after(0, self._stop_status_blinking)
            
            self.after(0, lambda: action_frame.hotkey_btn.configure(
                text=f"⌨ {key}", 
                fg_color=COLORS["accent"]
            ))
            self.after(0, lambda: self.status_label.configure(
                text=f"✅ Bound to '{key}'!", 
                text_color=COLORS["success"]
            ))
            self.after(0, self.refresh_executor)
            self.after(0, self.auto_save)
            # Continue to coordinate picking
            self.after(800, lambda: self._continue_guided_setup(action_frame))
    
    def _continue_guided_setup(self, action_frame):
        """Continue guided setup: pick first coordinate."""
        self._guided_action = None
        if action_frame.coord_rows:
            coord_row = action_frame.coord_rows[0]
            coord_row.coord_btn.configure(text="...", fg_color=COLORS["warning"])
            
            # Start blinking for coordinate button and status
            self._start_blinking(coord_row.coord_btn, "fg_color", COLORS["warning"], COLORS["accent_secondary"])
            self._start_status_blinking("Step 2/2: 🎯 Middle-click to pick coordinate...")
            
            # Store reference for stopping animation
            self._blinking_coord_row = coord_row
            self.start_picking(coord_row)

    def _listen_for_key(self):
        import keyboard
        key = keyboard.read_hotkey(suppress=False)
        if self.binding_action:
            self.after(0, lambda: self.binding_action.hotkey_btn.configure(
                text=f"⌨ {key}", 
                fg_color=COLORS["accent"]
            ))
            self.after(0, lambda: self.status_label.configure(text=f"✅ Bound to '{key}'"))
            self.binding_action = None
            self.after(0, self.refresh_executor)
            self.after(0, self.auto_save)

    def update_status_safe(self, message):
        self.after(0, lambda: self.status_label.configure(text=message))

    def refresh_executor(self):
        self.executor.unregister_all()
        if not self.is_paused:
            for action in self.actions:
                data = action.get_data()
                # Only register enabled actions with valid hotkeys
                if data.get("enabled", True) and data["hotkey"] and data["hotkey"] not in ["None", "Bind Key", "Press..."]:
                    # Pass get_data callback instead of static data
                    # This allows reading fresh settings at execution time
                    self.executor.register_hotkey(data["hotkey"], action.get_data)
        self.update_state_display()
    
    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.executor.unregister_all()
        else:
            self.refresh_executor()
        self.update_state_display()
    
    def update_state_display(self):
        if self.is_paused:
            self.state_indicator.configure(text="○", text_color=COLORS["danger"])
            self.pause_btn.configure(text="▶ Resume", fg_color=COLORS["danger"], hover_color="#52525b", text_color="#fafafa")
            self.status_label.configure(text="Paused")
        else:
            # Count only enabled actions with valid hotkeys
            active_count = sum(1 for a in self.actions 
                if a.get_data().get("enabled", True) and 
                a.get_data()["hotkey"] not in ["None", "Bind Key", "Press..."])
            total_count = len(self.actions)
            
            if active_count == 0:
                self.state_indicator.configure(text="○", text_color=COLORS["warning"])
                self.pause_btn.configure(text="● Active", fg_color=COLORS["success"], hover_color="#e4e4e7", text_color="#09090b")
                self.status_label.configure(text="Standby - No active shortcuts")
            else:
                self.state_indicator.configure(text="●", text_color=COLORS["success"])
                self.pause_btn.configure(text="● Active", fg_color=COLORS["success"], hover_color="#e4e4e7", text_color="#09090b")
                self.status_label.configure(text=f"Ready - {active_count}/{total_count} shortcut(s) active")

    def _on_action_change(self):
        """Handle changes in action cards (name, hotkey, enabled state)."""
        self.auto_save()
        self.refresh_executor()

    def auto_save(self):
        """Automatically save current configuration."""
        data = [a.get_data() for a in self.actions]
        self.config_manager.save_actions(data)

    def load_config(self):
        """Load saved configuration."""
        actions = self.config_manager.get_actions()
        for action_data in actions:
            self.add_action(action_data)
        self.refresh_executor()

    def show_help(self):
        """Show help dialog with usage instructions."""
        help_window = ctk.CTkToplevel(self)
        help_window.title("Help - S-Trade-Executor")
        help_window.geometry("450x520")
        help_window.resizable(False, False)
        help_window.overrideredirect(True) # Remove default title bar
        help_window.attributes("-topmost", True)
        help_window.configure(fg_color=COLORS["border"]) # Border color
        
        # Center the window
        help_window.transient(self)
        help_window.grab_set()
        
        # Container for border
        container = ctk.CTkFrame(help_window, fg_color=COLORS["bg_dark"], corner_radius=0)
        container.pack(fill="both", expand=True, padx=1, pady=1)
        
        # Custom Title Bar
        title_bar = CustomTitleBar(
            container, 
            title="Help - S-Trade-Executor", 
            height=30,
            close_command=help_window.destroy
        )
        title_bar.pack(fill="x")
        
        # Header
        header = ctk.CTkLabel(
            container, 
            text="📖 Panduan Penggunaan",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["accent"]
        )
        header.pack(pady=(20, 15))
        
        # Content frame with scroll
        content_frame = ctk.CTkScrollableFrame(
            container, 
            fg_color=COLORS["bg_card"],
            corner_radius=10
        )
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        help_sections = [
            ("🚀 Memulai", 
             "1. Klik '+ New Action' untuk membuat action baru\n"
             "2. Tekan tombol keyboard untuk bind hotkey\n"
             "3. Middle-click untuk memilih koordinat target"),
            
            ("⌨️ Hotkey", 
             "• Klik tombol hotkey untuk mengubah\n"
             "• Tekan kombinasi tombol yang diinginkan\n"
             "• Contoh: F1, Ctrl+Shift+A, dll"),
            
            ("📍 Koordinat", 
             "• Klik tombol koordinat, lalu middle-click\n"
             "  di posisi target di layar\n"
             "• Klik '+' untuk menambah koordinat\n"
             "• Klik '×' untuk menghapus koordinat"),
            
            ("⚙️ Pengaturan", 
             "• Mode: Single (1x), Double (2x), Burst (5x)\n"
             "• Delay: Jeda antar klik (dalam ms)\n"
             "  1000 ms = 1 detik"),
            
            ("▶ Test (Toggle)", 
             "• Klik 'Test' untuk menampilkan crosshair (Show)\n"
             "• Klik lagi untuk menyembunyikan (Hide)\n"
             "• Klik pada crosshair untuk menghapusnya"),
            
            ("⏸ Pause/Resume", 
             "• Klik tombol 'Active/Resume' untuk\n"
             "  menghentikan sementara semua hotkey\n"
             "• Indikator merah = Paused (Aman)"),
             
             ("ℹ️ Tentang",
              "S-Trade-Executor v1.0\n"
              "Simple & Fast Trade Execution Tool")
        ]
        
        for title, content in help_sections:
            section_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            section_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                section_frame, 
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["accent"],
                anchor="w"
            ).pack(fill="x")
            
            ctk.CTkLabel(
                section_frame,
                text=content,
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"],
                anchor="w",
                justify="left"
            ).pack(fill="x", padx=(10, 0))



    def on_closing(self):
        """Clean up all resources before closing the application."""
        try:
            # Stop all animations and timers
            self._destroy_cursor_glow()
            
            # Stop burst pulse animations for all action cards
            for action in self.actions:
                if hasattr(action, '_stop_burst_pulse'):
                    action._stop_burst_pulse()
            
            # Unregister all keyboard hooks
            self.executor.stop_listening()
            
            # Clear all callbacks to prevent any pending calls
            self.executor.status_callback = None
            self.executor.click_indicator_callback = None
            self.executor.execution_start_callback = None
            self.executor.execution_end_callback = None
            
            # Destroy the window
            self.destroy()
        except:
            pass
        finally:
            # Force exit the process to ensure no hanging threads
            import os
            os._exit(0)

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
