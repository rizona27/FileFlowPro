# ui_components.py
import tkinter as tk
from tkinter import ttk

class UIComponents:
    """UI组件和样式管理"""

    MORANDI_BG = '#F5F5F5'
    MORANDI_ACCENT = '#A8B5B8'
    MORANDI_DARK = '#6B7F7F'
    MORANDI_LIGHT = '#D8E2E2'
    MORANDI_TEXT = '#333333'
    
    @staticmethod
    def setup_styles():
        """配置莫兰迪色系样式"""
        style = ttk.Style()

        style.configure('TFrame', background=UIComponents.MORANDI_BG)
        style.configure('TLabel', background=UIComponents.MORANDI_BG, 
                       foreground=UIComponents.MORANDI_TEXT, font=('Arial', 10))
        style.configure('TCheckbutton', background=UIComponents.MORANDI_BG)
        style.configure('TEntry', fieldbackground='white')
        style.configure('TButton', 
                       font=('Arial', 10),
                       background=UIComponents.MORANDI_ACCENT,
                       foreground='white',
                       borderwidth=1,
                       relief='raised')
        style.map('TButton',
                 background=[('active', UIComponents.MORANDI_DARK), 
                           ('pressed', UIComponents.MORANDI_DARK),
                           ('disabled', '#CCCCCC')],
                 foreground=[('disabled', '#999999')])

        style.configure('TProgressbar', 
                       background=UIComponents.MORANDI_ACCENT,
                       troughcolor=UIComponents.MORANDI_LIGHT,
                       borderwidth=0,
                       lightcolor=UIComponents.MORANDI_ACCENT,
                       darkcolor=UIComponents.MORANDI_ACCENT)

        style.configure('red.Horizontal.TProgressbar', 
                       background='#D8A5A5',
                       troughcolor=UIComponents.MORANDI_LIGHT)

        style.configure('TLabelframe', 
                       background=UIComponents.MORANDI_BG,
                       relief='solid',
                       borderwidth=1)
        style.configure('TLabelframe.Label', 
                       background=UIComponents.MORANDI_BG, 
                       foreground=UIComponents.MORANDI_DARK,
                       font=('Arial', 10, 'bold'))
        
        return style

    @staticmethod
    def create_scrollable_frame(parent):
        """创建可滚动的框架"""
        canvas = tk.Canvas(parent, bg=UIComponents.MORANDI_BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        return canvas, scrollbar, scrollable_frame