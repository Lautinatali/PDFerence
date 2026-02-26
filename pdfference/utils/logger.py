"""
Unified logging system for PDFerence.
Logs to file, console, and collects for UI display.
"""
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional


class Logger:
    """
    Unified logger that writes to file + console + UI buffer.
    Use for all logging across the application.
    """
    
    def __init__(self, name: str, log_dir: Optional[Path] = None):
        self.name = name
        self.log_dir = log_dir or Path("./logs")
        self.log_dir.mkdir(exist_ok=True, parents=True)
        
        # Internal logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # File handler (DEBUG level)
        log_file = self.log_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        
        # Console handler (INFO level)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # For Streamlit UI feedback (timestamped lines)
        self.ui_lines: list[str] = []
    
    def debug(self, msg: str):
        """Log debug message (file only)."""
        self.logger.debug(msg)
    
    def info(self, msg: str):
        """Log info message."""
        self.logger.info(msg)
        self._add_ui(f"ℹ️  {msg}")
    
    def warning(self, msg: str):
        """Log warning message."""
        self.logger.warning(msg)
        self._add_ui(f"⚠️  {msg}")
    
    def error(self, msg: str):
        """Log error message."""
        self.logger.error(msg)
        self._add_ui(f"❌ {msg}")
    
    def success(self, msg: str):
        """Log success message (info level, custom emoji)."""
        self.logger.info(msg)
        self._add_ui(f"✅ {msg}")
    
    def get_ui_output(self) -> str:
        """Return formatted UI output (for Streamlit)."""
        return "\n".join(self.ui_lines)
    
    def clear_ui_buffer(self):
        """Clear UI buffer (call after rendering)."""
        self.ui_lines.clear()
    
    def _add_ui(self, msg: str):
        """Add timestamped message to UI buffer."""
        ts = datetime.now().strftime("%H:%M:%S")
        self.ui_lines.append(f"[{ts}] {msg}")
