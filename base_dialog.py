import tkinter as tk
from tkinter import ttk
from config import WINDOW_SIZES

class BaseDialog(tk.Toplevel):
    """对话框基类，彻底解决窗口闪烁问题"""
    
    def __init__(self, parent, title, window_size_key):
        super().__init__(parent)
        
        self.withdraw() 

        self.title(title)
        self.geometry(WINDOW_SIZES[window_size_key])
        self.resizable(False, False)

        try:
            self.iconbitmap("app.ico")
        except:
            pass

        self.attributes('-toolwindow', True)
        self.transient(parent)
        self.grab_set()
        self.setup_ui()
        self.update_idletasks()
        self.center_on_parent(parent)
        self.deiconify()
        self.focus_set()
    
    def setup_ui(self):
        """子类必须重写此方法来构建UI"""
        raise NotImplementedError("子类必须实现setup_ui方法")
    
    def center_on_parent(self, parent):
        """将窗口居中显示在父窗口中心"""
        parent.update_idletasks()
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()
        
        try:
            dialog_width, dialog_height = map(int, self.geometry().split('+')[0].split('x'))
        except ValueError:
            dialog_width = self.winfo_width()
            dialog_height = self.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.geometry(f'{dialog_width}x{dialog_height}+{x}+{y}')