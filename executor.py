import time
import threading
import ctypes
from typing import Optional, Tuple
from pynput.mouse import Button, Controller
import keyboard

# Ctypes definitions for low-level mouse input
PUL = ctypes.POINTER(ctypes.c_ulong)
class KeyBdInput(ctypes.Structure):
    _fields_ = [("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class HardwareInput(ctypes.Structure):
    _fields_ = [("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)]

class MouseInput(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)]

class Input_I(ctypes.Union):
    _fields_ = [("ki", KeyBdInput),
                ("mi", MouseInput),
                ("hi", HardwareInput)]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong),
                ("ii", Input_I)]

class Executor:
    def __init__(self):
        self.mouse = Controller()
        self.running = False
        self.hotkeys = {}  # Map hotkey string to action data
        self.listener = None
        self.status_callback = None
        self.click_indicator_callback = None  # Visual indicator for clicks
        self.execution_start_callback = None  # Called when execution starts
        self.execution_end_callback = None    # Called when execution ends
        
        # Cancel on mouse move feature
        self.cancel_on_mouse_move = False
        self._execution_cancelled = False
        self._initial_mouse_pos = None
        self._mouse_move_threshold = 10  # pixels

    def _send_input(self, flags, data=0, dx=0, dy=0):
        """Send low-level mouse input via user32.dll"""
        extra = ctypes.c_ulong(0)
        ii_ = Input_I()
        ii_.mi = MouseInput(dx, dy, data, flags, 0, ctypes.pointer(extra))
        x = Input(ctypes.c_ulong(0), ii_)
        ctypes.windll.user32.SendInput(1, ctypes.pointer(x), ctypes.sizeof(x))

    def click(self, x: int, y: int, button: str = 'left', mode: str = 'single', burst_count: int = 3):
        """Execute click(s) at specific coordinates with low latency."""
        
        # Move mouse first (using pynput for movement as it's reliable enough, or could use SetCursorPos)
        # ctypes.windll.user32.SetCursorPos(x, y) is faster
        ctypes.windll.user32.SetCursorPos(x, y)
        
        # Update initial position after moving to click target
        if self.cancel_on_mouse_move:
            self._initial_mouse_pos = self._get_mouse_pos()
        
        # Prepare click constants
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010
        
        down_flag = MOUSEEVENTF_LEFTDOWN if button == 'left' else MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_LEFTUP if button == 'left' else MOUSEEVENTF_RIGHTUP
        
        clicks_to_do = 1
        if mode == 'double':
            clicks_to_do = 2
        elif mode == 'burst':
            clicks_to_do = burst_count
            
        for _ in range(clicks_to_do):
            self._send_input(down_flag)
            self._send_input(up_flag)
            # Minimal sleep for stability if needed, but for trading speed is key. 
            # Some apps might miss it if too fast (0ms), so maybe 1-5ms.
            if clicks_to_do > 1:
                time.sleep(0.01) 

    def set_status_callback(self, callback):
        self.status_callback = callback
    
    def _get_mouse_pos(self):
        """Get current mouse position."""
        import ctypes.wintypes
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return (pt.x, pt.y)
    
    def _check_mouse_moved(self):
        """Check if mouse has moved beyond threshold from initial position."""
        if not self.cancel_on_mouse_move or not self._initial_mouse_pos:
            return False
        
        current = self._get_mouse_pos()
        dx = abs(current[0] - self._initial_mouse_pos[0])
        dy = abs(current[1] - self._initial_mouse_pos[1])
        
        return dx > self._mouse_move_threshold or dy > self._mouse_move_threshold

    def register_hotkey(self, key_combo: str, data_getter):
        """Register a hotkey to trigger an action.
        
        Args:
            key_combo: The hotkey combination string (e.g., 'ctrl+shift+a')
            data_getter: A callable that returns the current action data dict.
                        This allows reading fresh settings (like delay_ms) 
                        at execution time, not registration time.
        """
        
        def on_triggered():
            # Get fresh data each time the hotkey is triggered
            action_data = data_getter() if callable(data_getter) else data_getter
            
            coords = action_data.get('coords', [])
            # Backward compatibility
            if not coords:
                coords = [{"x": action_data.get('x', 0), "y": action_data.get('y', 0)}]
            
            total = len(coords)
            delay_ms = action_data.get('delay_ms', 100)
            name = action_data.get('name', 'Action')
            
            # Reset cancellation state and store initial mouse position
            self._execution_cancelled = False
            if self.cancel_on_mouse_move:
                self._initial_mouse_pos = self._get_mouse_pos()
            
            # Notify execution start
            if self.execution_start_callback:
                self.execution_start_callback()
            
            if self.status_callback:
                if total > 1:
                    self.status_callback(f"{name}: {total} clicks, {delay_ms}ms delay")
                else:
                    self.status_callback(f"Executing: {name}")
            
            for i, coord in enumerate(coords):
                # Check if cancelled due to mouse movement
                if self._check_mouse_moved():
                    self._execution_cancelled = True
                    if self.status_callback:
                        self.status_callback(f"⚠️ Cancelled: Mouse moved")
                    break
                
                if self.status_callback and total > 1:
                    self.status_callback(f"{name}: Click {i+1}/{total} @ {coord['x']},{coord['y']}")
                
                # Show visual indicator at click position
                if self.click_indicator_callback:
                    self.click_indicator_callback(coord['x'], coord['y'])
                
                self.click(
                    coord['x'], 
                    coord['y'], 
                    action_data.get('button', 'left'), 
                    action_data.get('mode', 'single').lower(), 
                    action_data.get('burst_count', 3)
                )
                
                # Update mouse position tracking after click
                if self.cancel_on_mouse_move:
                    self._initial_mouse_pos = self._get_mouse_pos()
                
                if i < total - 1:  # Don't delay after last click
                    # Countdown timer with status updates
                    remaining_ms = delay_ms
                    update_interval = 100  # Update every 100ms
                    
                    while remaining_ms > 0:
                        # Check for mouse movement during delay
                        if self._check_mouse_moved():
                            self._execution_cancelled = True
                            if self.status_callback:
                                self.status_callback(f"⚠️ Cancelled: Mouse moved")
                            break
                        
                        if self.status_callback:
                            # Format remaining time nicely
                            if remaining_ms >= 1000:
                                time_str = f"{remaining_ms/1000:.1f}s"
                            else:
                                time_str = f"{remaining_ms}ms"
                            self.status_callback(f"{name}: ⏱ {time_str} → Click {i+2}/{total}")
                        
                        sleep_time = min(update_interval, remaining_ms)
                        time.sleep(sleep_time / 1000.0)
                        remaining_ms -= sleep_time
                    
                    # Break outer loop if cancelled
                    if self._execution_cancelled:
                        break
            
            if not self._execution_cancelled and self.status_callback:
                self.status_callback(f"Done: {name} ({total} clicks)")
            
            # Notify execution end
            if self.execution_end_callback:
                self.execution_end_callback()
        
        try:
            keyboard.add_hotkey(key_combo, on_triggered)
            self.hotkeys[key_combo] = on_triggered
            return True
        except Exception as e:
            print(f"Failed to register hotkey {key_combo}: {e}")
            return False

    def unregister_all(self):
        keyboard.unhook_all()
        self.hotkeys.clear()

    def start_listening(self):
        # keyboard library listens in background automatically once hooks are added
        pass

    def stop_listening(self):
        self.unregister_all()
