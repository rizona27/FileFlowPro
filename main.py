# main.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time
import re
import base64
from io import BytesIO
from PIL import Image, ImageTk

from organizer_core import FileOrganizer
from dialogs import FormatDialog, PriorityDialog, OtherFilesDialog
from naming_rules import NamingRulesDialog
from ui_components import UIComponents
from config import WINDOW_SIZES, QR_CODE_BASE64
from base_dialog import BaseDialog

class ToolTip:
    """创建工具提示类 - 改进版本"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)
        self.widget.bind("<Motion>", self.move_tip)  

    def show_tip(self, event=None):
        """显示工具提示"""
        if self.tip_window:
            return
        
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)

        tw.configure(
            background='#2C3E50',  
            relief='flat',
            borderwidth=0
        )
        
        tw.attributes("-alpha", 0.95)
        
        label = tk.Label(tw, 
                        text=self.text, 
                        justify=tk.LEFT,
                        background='#2C3E50',  
                        foreground='#ECF0F1',  
                        relief="flat",
                        borderwidth=0,
                        font=("Arial", 10, "normal"),
                        padx=12, 
                        pady=8)
        label.pack()
        
        self.move_tip()

    def move_tip(self, event=None):
        """移动工具提示到合适位置，避免遮挡"""
        if not self.tip_window:
            return

        if event:
            x = event.x_root + 15
            y = event.y_root + 15
        else:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
        
        self.tip_window.update_idletasks()
        tip_width = self.tip_window.winfo_width()
        tip_height = self.tip_window.winfo_height()
        
        screen_width = self.tip_window.winfo_screenwidth()
        screen_height = self.tip_window.winfo_screenheight()

        if x + tip_width > screen_width:
            x = screen_width - tip_width - 10
        if y + tip_height > screen_height:
            y = self.widget.winfo_rooty() - tip_height - 10  
        
        self.tip_window.wm_geometry(f"+{int(x)}+{int(y)}")

    def hide_tip(self, event=None):
        """隐藏工具提示"""
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class ReadMeDialog(BaseDialog):
    def __init__(self, parent):
        super().__init__(parent, "程序说明 - FileFlow Pro", 'readme_dialog')
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, width=45, height=15,
                             bg='white', font=('Arial', 10))
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        readme_content = """
FileFlow Pro - 文件批量整理程序

【程序功能】
1. 格式支持
   - 图片格式: BMP,GIF,JPEG,JPG,PNG,HEIC...
   - 视频格式: AVI,MKV,MP4,MPEG...
   - 文档格式: DOC,XLS,PPT,TXT,PDF...
   - 支持添加其他自定义格式

2. 日期提取
   - 支持从元数据等提取日期
   - 可定义日期提取优先级
   - 识别多种日期格式

3. 文件组织
   - 支持按年、月、日三种整理模式
   - 可定义单文件夹文件数量
   - 可定义文件夹和文件命名规则

4. 安全机制
   - 整理前默认可选备份
   - 重复文件检测和去重
   - 操作可暂停、终止和回滚

【使用说明】
1. 选择源目录和目标目录
2. 根据需要设置文件格式、命名规则等
3. 强烈建议勾选"整理前备份"以确保数据安全
4. 点击"开始整理"执行文件整理操作

【注意事项】
- 建议首次使用前先在小批量文件上测试
- 确保有足够的磁盘空间进行备份
- 整理过程中请不要关闭程序
        """
        
        text_widget.insert(tk.END, readme_content)
        text_widget.config(state=tk.DISABLED)  
        
        contact_frame = ttk.Frame(main_frame)
        contact_frame.pack(fill=tk.X, pady=10)
        
        left_frame = ttk.Frame(contact_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 20))

        qr_frame = ttk.Frame(left_frame)
        qr_frame.pack(side=tk.LEFT, pady=(0, 5))
        
        if QR_CODE_BASE64 != "BASE64":
            try:
                qr_data = base64.b64decode(QR_CODE_BASE64)
                qr_image = Image.open(BytesIO(qr_data))
                qr_image = qr_image.resize((100, 100), Image.Resampling.LANCZOS)
                qr_photo = ImageTk.PhotoImage(qr_image)
                
                qr_label = tk.Label(qr_frame, image=qr_photo, bg='white')  
                qr_label.image = qr_photo  
                qr_label.pack()
                
                ToolTip(qr_label, "如果觉得不错\n打赏杯咖啡喝吧～")
            except Exception as e:
                qr_label = tk.Label(qr_frame, text="[二维码图片]", width=12, height=5, 
                                   relief="solid", borderwidth=1, bg='white')  
                qr_label.pack()
                ToolTip(qr_label, "如果觉得不错\n打赏杯咖啡喝吧～")
        else:
            qr_label = tk.Label(qr_frame, text="[二维码图片]", width=12, height=5, 
                               relief="solid", borderwidth=1, bg='white')  
            qr_label.pack()
            ToolTip(qr_label, "如果觉得不错\n打赏杯咖啡喝吧～")
        
        right_frame = ttk.Frame(contact_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        email_label = tk.Label(right_frame, text="Mail:\nrizona.cn@gmail.com", 
                              font=("Arial", 9, "bold"),
                              fg="#666666", 
                              justify=tk.RIGHT,
                              bg=UIComponents.MORANDI_BG)  
        email_label.pack(anchor=tk.E, pady=(0, 8))

        version_label = tk.Label(right_frame, text="Version: 1.0\nUpdated: 2025 Oct.", 
                               font=("Arial", 9, "bold"),
                               fg="#666666", 
                               justify=tk.RIGHT,
                               bg=UIComponents.MORANDI_BG)  
        version_label.pack(anchor=tk.E)

class BatchFileOrganizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FileFlow Pro - 文件批量整理程序")

        self.set_window_center(WINDOW_SIZES['main_window'])
        self.root.resizable(False, False)

        try:
            self.root.iconbitmap("app.ico")
        except:
            pass
        
        self.organizer = FileOrganizer()
        self.is_organizing = False
        self.is_paused = False 
        self.duplicate_var = tk.StringVar(value="resort")

        self.last_source_dir = ""
        self.last_dest_dir = ""

        self.log_search_var = tk.StringVar()
        self.log_filter_var = tk.StringVar(value="ALL")

        self.all_logs = []
        
        self.setup_ui()
        
        self.start_time = 0
        self.total_estimated_time = 0
    
    def set_window_center(self, geometry):
        """设置窗口在屏幕中央显示"""
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        width, height = map(int, geometry.split('x'))

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def setup_ui(self):
        self.root.configure(bg=UIComponents.MORANDI_BG)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=3, pady=(0, 15), sticky=(tk.W, tk.E))

        title_label = tk.Label(title_frame, 
                              text="FileFlow Pro", 
                              font=("Arial", 16, "bold"),
                              bg=UIComponents.MORANDI_BG,
                              fg=UIComponents.MORANDI_DARK)
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(title_frame,
                                text="文件批量整理",
                                font=("Arial", 10),
                                bg=UIComponents.MORANDI_BG,
                                fg=UIComponents.MORANDI_ACCENT)
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

        readme_link = tk.Label(title_frame,
                              text="ReadMe",
                              font=("Arial", 10, "underline"),
                              bg=UIComponents.MORANDI_BG,
                              fg=UIComponents.MORANDI_DARK,
                              cursor="hand2")
        readme_link.pack(side=tk.RIGHT)
        readme_link.bind("<Button-1>", lambda e: self.show_readme())

        dir_frame = ttk.LabelFrame(main_frame, text="目录设置", padding="10")
        dir_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)

        ttk.Label(dir_frame, text="源目录:").grid(row=0, column=0, sticky=tk.W, pady=5)
        source_button_frame = ttk.Frame(dir_frame)
        source_button_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        source_button_frame.columnconfigure(1, weight=1)
        
        self.source_browse_btn = ttk.Button(source_button_frame, text="浏览", command=self.browse_source, width=8)
        self.source_browse_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(source_button_frame, textvariable=self.source_var)
        self.source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

        ttk.Label(dir_frame, text="目标目录:").grid(row=1, column=0, sticky=tk.W, pady=5)
        dest_button_frame = ttk.Frame(dir_frame)
        dest_button_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        dest_button_frame.columnconfigure(1, weight=1)
        
        self.dest_browse_btn = ttk.Button(dest_button_frame, text="浏览", command=self.browse_dest, width=8)
        self.dest_browse_btn.grid(row=0, column=0, padx=(0, 5))
        
        self.dest_var = tk.StringVar()
        self.dest_entry = ttk.Entry(dest_button_frame, textvariable=self.dest_var)
        self.dest_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

        settings_frame = ttk.LabelFrame(main_frame, text="整理设置", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))

        options_row1 = ttk.Frame(settings_frame)
        options_row1.pack(fill=tk.X, pady=2)
        
        self.backup_var = tk.BooleanVar(value=True)
        self.backup_chkbtn = ttk.Checkbutton(options_row1, text="整理前备份", 
                       variable=self.backup_var)
        self.backup_chkbtn.pack(side=tk.LEFT, padx=(0, 20))

        options_row2 = ttk.Frame(settings_frame)
        options_row2.pack(fill=tk.X, pady=2)
        
        self.format_btn = ttk.Button(options_row2, text="文件格式设置", 
                  command=self.customize_formats)
        self.format_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.naming_btn = ttk.Button(options_row2, text="命名规则设置", 
                   command=self.setup_naming_rules)
        self.naming_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.priority_btn = ttk.Button(options_row2, text="筛选规则设置", 
                   command=self.setup_priority)
        self.priority_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.other_files_btn = ttk.Button(options_row2, text="其他处理设置", 
                   command=self.setup_other_files)
        self.other_files_btn.pack(side=tk.LEFT)

        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress = ttk.Progressbar(progress_frame, mode='determinate', maximum=100)
        self.progress.pack(fill=tk.X, expand=True)
        
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(pady=5)

        log_frame = ttk.LabelFrame(main_frame, text="操作日志", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=12, width=70, 
                               bg='white', fg=UIComponents.MORANDI_TEXT,
                               font=('Consolas', 9),
                               relief='solid',
                               borderwidth=1)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.log_text.tag_config('Error', foreground='#D32F2F')  
        self.log_text.tag_config('Warning', foreground='#FF8C00')  
        self.log_text.tag_config('Success', foreground='#388E3C')  
        self.log_text.tag_config('Progress', foreground='#1976D2')  
        self.log_text.tag_config('Info', foreground=UIComponents.MORANDI_TEXT)

        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)

        log_controls_frame = ttk.Frame(log_frame)
        log_controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))

        ttk.Label(log_controls_frame, text="搜索:").pack(side=tk.LEFT, padx=(0, 5))
        search_entry = ttk.Entry(log_controls_frame, textvariable=self.log_search_var, width=15)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind('<KeyRelease>', self.on_log_search)

        ttk.Label(log_controls_frame, text="级别:").pack(side=tk.LEFT, padx=(0, 5))
        filter_combo = ttk.Combobox(log_controls_frame, textvariable=self.log_filter_var,
                                  values=["ALL", "INFO", "WARNING", "ERROR", "SUCCESS", "PROGRESS"],
                                  state="readonly", width=10)
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind('<<ComboboxSelected>>', self.on_log_filter)

        ttk.Button(log_controls_frame, text="清空搜索", 
                  command=self.clear_log_search).pack(side=tk.LEFT)

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=5)

        self.start_btn = ttk.Button(button_frame, text="开始整理", 
                                    command=self.organize_files)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = ttk.Button(button_frame, text="暂停", 
                                    command=self.pause_organizing, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.clear_log_btn = ttk.Button(button_frame, text="清空日志", 
                                    command=self.clear_log)
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)

    def on_log_search(self, event=None):
        """日志搜索事件"""
        search_term = self.log_search_var.get()
        self.organizer.set_log_search_term(search_term)
        self.refresh_log_display()
    
    def on_log_filter(self, event=None):
        """日志过滤事件 - 修复版本，确保立即生效"""
        filter_level = self.log_filter_var.get()
        self.organizer.set_log_filter_level(filter_level)
        self.refresh_log_display()
    
    def clear_log_search(self):
        """清空搜索条件"""
        self.log_search_var.set("")
        self.log_filter_var.set("ALL")
        self.organizer.set_log_search_term("")
        self.organizer.set_log_filter_level("ALL")
        self.refresh_log_display()
    
    def refresh_log_display(self):
        """刷新日志显示 - 修复版本，确保过滤立即生效"""

        self.log_text.delete(1.0, tk.END)

        filtered_logs = self.organizer.filter_logs(self.all_logs)

        for log_entry in filtered_logs:
            self.log_text.insert(tk.END, log_entry['message'] + "\n", log_entry['level'])
        
        self.log_text.see(tk.END)

    def show_readme(self):
        """显示程序说明对话框"""
        ReadMeDialog(self.root)
        
    def browse_source(self):
        initial_dir = self.last_source_dir if self.last_source_dir else None
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.source_var.set(directory)
            self.last_source_dir = directory
            
    def browse_dest(self):
        if self.last_source_dir:
            initial_dir = os.path.dirname(self.last_source_dir)
        else:
            initial_dir = self.last_dest_dir if self.last_dest_dir else None
            
        directory = filedialog.askdirectory(initialdir=initial_dir)
        if directory:
            self.dest_var.set(directory)
            self.last_dest_dir = directory
            
    def customize_formats(self):
        FormatDialog(self.root, self.organizer)
        
    def setup_naming_rules(self):
        NamingRulesDialog(self.root, self.organizer)
    
    def setup_priority(self):
        """打开筛选规则设置对话框"""
        PriorityDialog(self.root, self.organizer)
        
    def setup_other_files(self):
        """打开其他处理设置对话框"""
        OtherFilesDialog(self.root, self.organizer)
            
    def organize_files(self):
        """开始新的整理任务"""
        if self.is_organizing:
            messagebox.showwarning("警告", "整理过程正在进行中")
            return
            
        source_dir = self.source_var.get()
        dest_dir = self.dest_var.get()
        
        if not source_dir or not os.path.exists(source_dir):
            messagebox.showerror("错误", "请选择有效的源目录")
            return
            
        if not dest_dir:
            if messagebox.askyesno("确认目标目录", "目标目录为空。确定要将文件整理到源目录中吗？"):
                dest_dir = source_dir
            else:
                return

        if not self.backup_var.get():
            result = messagebox.askyesno(
                "备份提示", 
                "您未勾选『整理前备份』选项。\n\n强烈建议进行备份，以防整理过程中出现意外情况导致文件丢失。\n\n是否继续整理？",
                icon=messagebox.WARNING
            )
            if not result:
                return
        
        self.log("\n--- 开始整理 ---", 'Info')
        self.log(f"源目录: {source_dir}", 'Info')
        self.log(f"目标目录: {dest_dir}", 'Info')
        if not self.backup_var.get():
            self.log("警告: 未进行备份，存在文件丢失风险", 'Warning')

        self.is_organizing = True
        self.is_paused = False 
        self.update_ui_state()
        
        self.progress['value'] = 0
        self.status_var.set("正在启动...")
        self.start_time = time.time()
        self.total_estimated_time = 0 

        thread = threading.Thread(target=self._organize_thread, args=(source_dir, dest_dir))
        thread.daemon = True
        thread.start()
        
    def pause_organizing(self):
        """暂停整理，并更新按钮为"终止"""
        if self.is_organizing and not self.is_paused:
            self.is_paused = True
            self.organizer.pause_organizing()
            self.root.after(0, self.update_ui_state)
            self.log("[Warning] 操作已暂停...", 'Warning')

    def continue_organizing(self):
        """恢复整理操作"""
        if self.is_organizing and self.is_paused:
            self.is_paused = False
            self.organizer.resume_organizing()
            self.root.after(0, self.update_ui_state)
            self.log("[Info] 操作已恢复...", 'Info')

    def terminate_organizing(self):
        """确认终止并触发回退"""
        if self.is_paused:
            if messagebox.askyesno("确认终止", "整理已暂停。您确定要终止操作并回退所有更改吗？此操作不可逆!"):
                self.organizer.terminate_organizing() 
                self.log("[Error] 收到终止请求，正在等待线程结束并执行回退...", 'Error')

            
    def update_ui_state(self):
        """根据整理状态更新 UI 元素"""
        is_running = self.is_organizing
        is_paused = self.is_paused

        input_state = tk.DISABLED if is_running else tk.NORMAL

        self.source_entry.config(state=input_state)
        self.source_browse_btn.config(state=input_state)
        self.dest_entry.config(state=input_state)
        self.dest_browse_btn.config(state=input_state)
        self.backup_chkbtn.config(state=input_state)
        self.format_btn.config(state=input_state)
        self.naming_btn.config(state=input_state)
        self.priority_btn.config(state=input_state)
        self.other_files_btn.config(state=input_state)
        
        if is_running:
            self.clear_log_btn.config(state=tk.DISABLED)
            
            self.pause_btn.config(state=tk.NORMAL)
            if is_paused:
                self.start_btn.config(text="继续", command=self.continue_organizing, state=tk.NORMAL)
                self.pause_btn.config(text="终止", command=self.terminate_organizing)
                self.progress.config(style='red.Horizontal.TProgressbar')
                self.status_var.set("已暂停，等待继续或终止...")
            else:
                self.start_btn.config(text="开始整理", command=self.organize_files, state=tk.DISABLED)
                self.pause_btn.config(text="暂停", command=self.pause_organizing)
                self.progress.config(style='TProgressbar') 
        
        else: 
            self.start_btn.config(text="开始整理", command=self.organize_files, state=tk.NORMAL)
            self.pause_btn.config(text="暂停", command=self.pause_organizing, state=tk.DISABLED)
            self.clear_log_btn.config(state=tk.NORMAL)
            self.progress.config(style='TProgressbar')
            self.status_var.set("就绪")


    def _organize_thread(self, source_dir, dest_dir):
        """在后台线程中执行整理操作"""
        exception_obj = None  
        
        try:
            result = self.organizer.organize_media(
                source_dir, 
                dest_dir,
                backup=self.backup_var.get(),
                progress_callback=self._update_progress_and_log
            )

            if result == "TERMINATED" or self.organizer.is_terminated:
                self.log("\n--- 操作已终止 ---", 'Error')
                self.organizer.rollback_operations(dest_dir) 
                self.root.after(0, lambda: messagebox.showwarning("终止", "整理操作已终止并已回退更改。"))
                return

            self.log("\n--- 开始重新整理目标目录以确保连续序号 (耗时操作) ---", 'Progress')
            resort_result = self.organizer.resort_destination(dest_dir, progress_callback=self._update_progress_and_log)

            if resort_result == "TERMINATED" or self.organizer.is_terminated:
                self.log("\n--- 操作已终止 ---", 'Error')
                self.organizer.rollback_operations(dest_dir) 
                self.root.after(0, lambda: messagebox.showwarning("终止", "整理操作已终止并已回退更改。"))
                return

            self.log("\n--- 整理全部完成 ---", 'Success')
            self.log(f"总计处理文件: {result['images_processed'] + result['videos_processed'] + result['documents_processed'] + result['other_processed']}", 'Success')
            self.log(f"删除了 {result['identical_files_removed']} 个完全相同的文件 (重复)", 'Success')
            self.log("所有文件现已按日期顺序和序列号重命名", 'Success')
                
            self.root.after(0, lambda: messagebox.showinfo("成功", "媒体文件整理操作完成!"))

        except Exception as e:
            exception_obj = e  
            self.log(f"\n[Error] 整理过程中出错: {str(e)}", 'Error')
            
        finally:
            self.is_organizing = False
            self.is_paused = False
            self.organizer.reset_state() 
            self._update_progress_and_log(100, "[Success] 全部完成")
            self.root.after(0, self.update_ui_state) 

            if exception_obj is not None:
                error_msg = str(exception_obj)
                self.root.after(0, lambda: messagebox.showerror("错误", f"整理失败: {error_msg}"))
    
    def _update_progress_and_log(self, value, status_with_tag):
        """更新进度条和状态，并处理特殊日志值 - 修复版本：进度信息不记录到日志"""
        def update_ui():

            tag_match = status_with_tag.split(']')
            tag_raw = tag_match[0].lstrip('[').strip() if len(tag_match) > 1 else 'Info'
            message = status_with_tag.replace(f"[{tag_raw}]", "").strip()

            if self.is_paused and not self.organizer.is_paused:
                 self.is_paused = False
                 self.update_ui_state()

            if value >= 0 and value <= 100:
                self.progress['value'] = value

                if value > 5 and value < 100 and not self.is_paused:
                    self.organizer.update_progress_estimate(value)
                    remaining_time = self.organizer.get_remaining_time_string()
                    
                    self.status_var.set(f"{message} | 预估剩余: {remaining_time} ({value}%)")
                else:
                    self.status_var.set(f"{message} ({value}%)")
            elif value == 100:
                self.progress['value'] = 100
                self.status_var.set("完成")

            if value == -1 or (value >= 0 and message):
                self.log(message, tag_raw) 

        self.root.after(0, update_ui)
            
    def log(self, message, tag='Info'):
        """向日志文本区添加消息，并应用颜色标签"""
        log_entry = {
            'message': message,
            'level': tag,
            'timestamp': time.time()
        }
        self.all_logs.append(log_entry)

        if (self.organizer.log_filter_level == "ALL" or tag.upper() == self.organizer.log_filter_level.upper()) and \
           (not self.organizer.log_search_term or self.organizer.log_search_term in message.lower()):
            self.log_text.insert(tk.END, message + "\n", tag)
            self.log_text.see(tk.END)

        self.root.update_idletasks()
        
    def clear_log(self):
        """清空日志，如果日志为空则给出反馈"""
        if self.log_text.get(1.0, tk.END).strip():
            self.log_text.delete(1.0, tk.END)
            self.all_logs.clear()
            self.log("[Info] 日志已清空", 'Info')
        else:
            self.log("[Info] 日志已经是空的", 'Info')

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchFileOrganizerApp(root)
    root.mainloop()