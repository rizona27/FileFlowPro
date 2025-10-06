# dialogs.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
from organizer_core import FileOrganizer
from config import (DEFAULT_IMAGE_FORMATS, DEFAULT_VIDEO_FORMATS, DEFAULT_DOCUMENT_FORMATS, 
                   SETTINGS_FILE)
from base_dialog import BaseDialog

class FormatDialog(BaseDialog):
    def __init__(self, parent, organizer):
        self.organizer = organizer
        
        self.custom_image_formats = (self.organizer.image_formats - DEFAULT_IMAGE_FORMATS).copy()
        self.custom_video_formats = (self.organizer.video_formats - DEFAULT_VIDEO_FORMATS).copy()
        self.custom_document_formats = (self.organizer.document_formats - DEFAULT_DOCUMENT_FORMATS).copy()
        self.custom_other_formats = self.organizer.other_formats.copy()
        
        super().__init__(parent, "文件格式设置 - FileFlow Pro", 'format_dialog')
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        formats_frame = ttk.LabelFrame(main_frame, text="默认识别格式", padding="5")
        formats_frame.pack(fill=tk.X, pady=(0, 10))
        
        formats_text = ttk.Frame(formats_frame)
        formats_text.pack(fill=tk.X, pady=5)
        
        img_frame = ttk.Frame(formats_text)
        img_frame.pack(fill=tk.X, pady=2)
        ttk.Label(img_frame, text="图片:", font=("Arial", 9)).pack(side=tk.LEFT)
        img_formats_text = ttk.Label(img_frame, text=".bmp .gif .jpeg .jpg .png .heic", 
                                    font=("Arial", 9))
        img_formats_text.pack(side=tk.LEFT, padx=(5, 0))
        
        vid_frame = ttk.Frame(formats_text)
        vid_frame.pack(fill=tk.X, pady=2)
        ttk.Label(vid_frame, text="视频:", font=("Arial", 9)).pack(side=tk.LEFT)
        vid_formats_text = ttk.Label(vid_frame, text=".3gp .avi .flv .mkv .mov .mp4 .mpeg .mpg", 
                                    font=("Arial", 9))
        vid_formats_text.pack(side=tk.LEFT, padx=(5, 0))
        
        doc_frame = ttk.Frame(formats_text)
        doc_frame.pack(fill=tk.X, pady=2)
        ttk.Label(doc_frame, text="文档:", font=("Arial", 9)).pack(side=tk.LEFT)
        doc_formats_text = ttk.Label(doc_frame, text=".doc .docx .xls .xlsx .ppt .pptx .txt .csv .pdf", 
                                    font=("Arial", 9))
        doc_formats_text.pack(side=tk.LEFT, padx=(5, 0))
        
        add_frame = ttk.Frame(main_frame)
        add_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(add_frame, text="自定义添加的格式:").pack(side=tk.LEFT, padx=5)
        self.new_format_var = tk.StringVar()
        
        vcmd = (self.register(self.validate_format), '%P')
        new_format_entry = ttk.Entry(add_frame, textvariable=self.new_format_var, width=10, 
                                   validate="key", validatecommand=vcmd)
        new_format_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(add_frame, text="添加", 
                  command=lambda: self.add_format(self.new_format_var.get())).pack(side=tk.LEFT, padx=5)
        
        custom_frame = ttk.LabelFrame(main_frame, text="自定义格式列表", padding="5")
        custom_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        listbox_frame = ttk.Frame(custom_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.custom_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE, height=4)
        self.custom_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.custom_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.custom_listbox.config(yscrollcommand=scrollbar.set)

        self.custom_listbox.bind("<MouseWheel>", self.on_mousewheel)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)

        ttk.Button(button_frame, text="还原默认", 
                  command=self.restore_defaults).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="删除选中", 
                  command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="确定", 
                  command=self.apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", 
                  command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.load_current_formats()
    
    def on_mousewheel(self, event):
        """处理鼠标滚轮事件"""
        self.custom_listbox.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def validate_format(self, value):
        """验证格式输入，只允许英文、数字和点号，不超过6个字符"""
        if value == "":
            return True
        if len(value) > 6:
            return False
        return all(c.isalnum() or c == '.' for c in value)
    
    def load_current_formats(self):
        """加载当前自定义格式到列表"""
        self.custom_listbox.delete(0, tk.END)
        
        all_custom_formats = sorted(
            self.custom_image_formats | 
            self.custom_video_formats | 
            self.custom_document_formats | 
            self.custom_other_formats
        )
        
        for fmt in all_custom_formats:
            self.custom_listbox.insert(tk.END, fmt)
    
    def add_format(self, fmt):
        """添加新格式"""
        if not fmt:
            return

        if not fmt.startswith('.'):
            fmt = '.' + fmt
        fmt = fmt.lower()

        current_formats = (self.custom_image_formats | DEFAULT_IMAGE_FORMATS | 
                           self.custom_video_formats | DEFAULT_VIDEO_FORMATS |
                           self.custom_document_formats | DEFAULT_DOCUMENT_FORMATS |
                           self.custom_other_formats)
        
        if fmt in current_formats:
            messagebox.showinfo("提示", f"格式 '{fmt}' 已存在，无需重复添加")
            return
        
        self.custom_other_formats.add(fmt)
        self.load_current_formats()      
        self.new_format_var.set("")
    
    def delete_selected(self):
        """删除选中的格式"""
        selection = self.custom_listbox.curselection()
        if not selection:
            return
            
        to_delete = [self.custom_listbox.get(selection[0])]
        
        self.custom_image_formats -= set(to_delete)
        self.custom_video_formats -= set(to_delete)
        self.custom_document_formats -= set(to_delete)
        self.custom_other_formats -= set(to_delete)
        self.load_current_formats()
    
    def restore_defaults(self):
        """还原默认格式"""
        self.custom_image_formats = set()
        self.custom_video_formats = set()
        self.custom_document_formats = set()
        self.custom_other_formats = set()
        self.load_current_formats()
    
    def apply_changes(self):
        """应用更改，更新 organizer 实例"""
        
        self.organizer.set_formats(self.custom_image_formats, 
                                   self.custom_video_formats,
                                   self.custom_document_formats,
                                   self.custom_other_formats)
        
        self.organizer.save_settings()
        
        self.destroy()

class PriorityDialog(BaseDialog):
    def __init__(self, parent, organizer):
        self.organizer = organizer
        super().__init__(parent, "筛选规则设置 - FileFlow Pro", 'priority_dialog')
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        priority_frame = ttk.LabelFrame(main_frame, text="日期提取优先级设置", padding="5")
        priority_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        ttk.Label(priority_frame, text="从上到下优先级递减:", font=("Arial", 9)).pack(anchor=tk.W, pady=(0, 5))
        
        priority_list_frame = ttk.Frame(priority_frame)
        priority_list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.priority_listbox = tk.Listbox(priority_list_frame, height=5, selectmode=tk.SINGLE)
        self.priority_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        self.priority_listbox.bind('<<ListboxSelect>>', self.on_priority_selection_change)
        
        priority_btn_frame = ttk.Frame(priority_list_frame)
        priority_btn_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.move_up_btn = ttk.Button(priority_btn_frame, text="上移", 
                  command=self.move_priority_up, width=8)
        self.move_up_btn.pack(pady=2)
        
        self.move_down_btn = ttk.Button(priority_btn_frame, text="下移", 
                  command=self.move_priority_down, width=8)
        self.move_down_btn.pack(pady=2)
        
        ttk.Button(priority_btn_frame, text="重置", 
                  command=self.reset_priorities, width=8).pack(pady=2)
        
        self.priority_items = []
        priority_map = {
            "exif": ("EXIF元数据 (照片文件)", "exif"),
            "metadata": ("视频元数据 (视频文件)", "metadata"),
            "filename": ("文件名模式", "filename"),
            "filetime": ("文件修改时间", "filetime"),
            "creationtime": ("文件创建时间", "creationtime"),
            "filesystem": ("文件系统元数据", "filesystem")
        }

        for key in self.organizer.date_priority_list:
            if key in priority_map:
                self.priority_items.append(priority_map[key])

        existing_keys = [item[1] for item in self.priority_items]
        for key, value in priority_map.items():
            if key not in existing_keys:
                self.priority_items.append(value)
        
        self.update_priority_listbox()
        self.on_priority_selection_change()

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(button_frame, text="确定", command=self.apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
    
    def on_priority_selection_change(self, event=None):
        """优先级选择变化时更新按钮状态"""
        selection = self.priority_listbox.curselection()
        if selection:
            index = selection[0]
            if index == 0:
                self.move_up_btn.config(state=tk.DISABLED)
            else:
                self.move_up_btn.config(state=tk.NORMAL)
            if index == len(self.priority_items) - 1:
                self.move_down_btn.config(state=tk.DISABLED)
            else:
                self.move_down_btn.config(state=tk.NORMAL)
        else:
            self.move_up_btn.config(state=tk.DISABLED)
            self.move_down_btn.config(state=tk.DISABLED)
    
    def move_priority_up(self):
        """上移选中的优先级项"""
        selection = self.priority_listbox.curselection()
        if selection:
            index = selection[0]
            if index > 0:
                self.priority_items[index], self.priority_items[index-1] = self.priority_items[index-1], self.priority_items[index]
                self.update_priority_listbox()
                self.priority_listbox.selection_set(index-1)
                self.on_priority_selection_change()
    
    def move_priority_down(self):
        """下移选中的优先级项"""
        selection = self.priority_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.priority_items) - 1:
                self.priority_items[index], self.priority_items[index+1] = self.priority_items[index+1], self.priority_items[index]
                self.update_priority_listbox()
                self.priority_listbox.selection_set(index+1)
                self.on_priority_selection_change()
    
    def reset_priorities(self):
        """重置优先级顺序"""
        self.priority_items = [
            ("EXIF元数据 (照片文件)", "exif"),
            ("视频元数据 (视频文件)", "metadata"), 
            ("文件名模式", "filename"),
            ("文件修改时间", "filetime"),
            ("文件创建时间", "creationtime"),
            ("文件系统元数据", "filesystem")
        ]
        self.update_priority_listbox()
        self.on_priority_selection_change()
    
    def update_priority_listbox(self):
        """更新优先级列表框"""
        self.priority_listbox.delete(0, tk.END)
        for text, key in self.priority_items:
            self.priority_listbox.insert(tk.END, text)
    
    def apply_changes(self):
        """应用更改"""
        priority_keys = [key for _, key in self.priority_items]
        self.organizer.set_date_priority_list(priority_keys)

        self.organizer.save_settings()
        
        self.destroy()

class OtherFilesDialog(BaseDialog):
    def __init__(self, parent, organizer):
        self.organizer = organizer
        super().__init__(parent, "其他处理设置 - FileFlow Pro", 'other_files_dialog')
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        other_files_frame = ttk.LabelFrame(main_frame, text="其他文件处理", padding="8")
        other_files_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        self.organize_other_var = tk.BooleanVar(value=self.organizer.organize_other_files)
        organize_other_chk = ttk.Checkbutton(other_files_frame, text="整理不在已知格式列表中的文件", 
                       variable=self.organize_other_var,
                       command=self.on_organize_other_change)
        organize_other_chk.pack(anchor=tk.W, pady=2)
        
        other_folder_frame = ttk.Frame(other_files_frame)
        other_folder_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(other_folder_frame, text="整理到文件夹:").pack(side=tk.LEFT)
        self.other_folder_var = tk.StringVar(value=self.organizer.other_files_folder)
        self.other_folder_entry = ttk.Entry(other_folder_frame, textvariable=self.other_folder_var, width=20)
        self.other_folder_entry.pack(side=tk.LEFT, padx=5)
        
        self.other_folder_browse_btn = ttk.Button(other_folder_frame, text="浏览", 
                                                 command=self.browse_other_folder)
        self.other_folder_browse_btn.pack(side=tk.LEFT, padx=5)
        
        if not self.organizer.organize_other_files:
            self.other_folder_entry.config(state=tk.DISABLED)
            self.other_folder_browse_btn.config(state=tk.DISABLED)

        rename_frame = ttk.Frame(other_files_frame)
        rename_frame.pack(fill=tk.X, pady=5)
        
        self.rename_no_date_var = tk.BooleanVar(value=self.organizer.rename_no_date_files)
        rename_chk = ttk.Checkbutton(rename_frame, text="重命名无法提取日期的文件", 
                       variable=self.rename_no_date_var,
                       command=self.on_rename_no_date_change)
        rename_chk.pack(side=tk.LEFT)

        no_date_folder_frame = ttk.Frame(other_files_frame)
        no_date_folder_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(no_date_folder_frame, text="整理到文件夹:").pack(side=tk.LEFT)
        self.no_date_folder_var = tk.StringVar(value=self.organizer.no_date_files_folder)
        self.no_date_folder_entry = ttk.Entry(no_date_folder_frame, textvariable=self.no_date_folder_var, width=20)
        self.no_date_folder_entry.pack(side=tk.LEFT, padx=5)
        
        self.no_date_folder_browse_btn = ttk.Button(no_date_folder_frame, text="浏览", 
                                                   command=self.browse_no_date_folder)
        self.no_date_folder_browse_btn.pack(side=tk.LEFT, padx=5)

        if not self.organizer.rename_no_date_files:
            self.no_date_folder_entry.config(state=tk.DISABLED)
            self.no_date_folder_browse_btn.config(state=tk.DISABLED)

        folder_limit_frame = ttk.Frame(other_files_frame)
        folder_limit_frame.pack(fill=tk.X, pady=5)

        folder_limit_enabled = self.organizer.max_files_per_folder > 0
        self.folder_limit_var = tk.BooleanVar(value=folder_limit_enabled)
        folder_limit_chk = ttk.Checkbutton(folder_limit_frame, text="限制单个文件夹文件数量", 
                       variable=self.folder_limit_var,
                       command=self.on_folder_limit_change)
        folder_limit_chk.pack(side=tk.LEFT)

        limit_input_frame = ttk.Frame(other_files_frame)
        limit_input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(limit_input_frame, text="数量限制:").pack(side=tk.LEFT)

        vcmd = (self.register(self.validate_number), '%P')
        limit_value = self.organizer.max_files_per_folder if folder_limit_enabled else 1000
        self.folder_limit_value_var = tk.StringVar(value=str(limit_value))
        self.folder_limit_entry = ttk.Entry(limit_input_frame, textvariable=self.folder_limit_value_var, 
                                           width=10, validate="key", validatecommand=vcmd)
        self.folder_limit_entry.pack(side=tk.LEFT, padx=5)

        if not folder_limit_enabled:
            self.folder_limit_entry.config(state=tk.DISABLED)

        hint_label = ttk.Label(other_files_frame, text="(整百以上，如100、200、300)", 
                              font=("Arial", 9, "italic"), foreground="#666666")
        hint_label.pack(anchor=tk.W, pady=(0, 5))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=8)
        
        ttk.Button(button_frame, text="确定", command=self.apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def validate_number(self, value):
        """验证输入是否为数字"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
        
    def on_organize_other_change(self):
        """整理其他文件复选框变化"""
        if self.organize_other_var.get():
            self.other_folder_entry.config(state=tk.NORMAL)
            self.other_folder_browse_btn.config(state=tk.NORMAL)
        else:
            self.other_folder_entry.config(state=tk.DISABLED)
            self.other_folder_browse_btn.config(state=tk.DISABLED)
    
    def on_rename_no_date_change(self):
        """重命名无日期文件复选框变化"""
        if self.rename_no_date_var.get():
            self.no_date_folder_entry.config(state=tk.NORMAL)
            self.no_date_folder_browse_btn.config(state=tk.NORMAL)
        else:
            self.no_date_folder_entry.config(state=tk.DISABLED)
            self.no_date_folder_browse_btn.config(state=tk.DISABLED)
    
    def on_folder_limit_change(self):
        """文件夹文件数量限制复选框变化"""
        if self.folder_limit_var.get():
            self.folder_limit_entry.config(state=tk.NORMAL)
            current_value = self.folder_limit_value_var.get()
            if not current_value or current_value == '0':
                self.folder_limit_value_var.set("1000")
        else:
            self.folder_limit_entry.config(state=tk.DISABLED)
    
    def browse_other_folder(self):
        """浏览其他文件文件夹"""
        directory = filedialog.askdirectory()
        if directory:
            self.other_folder_var.set(directory)
    
    def browse_no_date_folder(self):
        """浏览无日期文件文件夹"""
        directory = filedialog.askdirectory()
        if directory:
            self.no_date_folder_var.set(directory)
    
    def apply_changes(self):
        """应用更改"""
        folder_limit = 0  
        if self.folder_limit_var.get():
            try:
                folder_limit = int(self.folder_limit_value_var.get())
                if folder_limit <= 0:
                    messagebox.showerror("错误", "数量输入有误")
                    return
                if folder_limit % 100 != 0:
                    messagebox.showerror("错误", "数量输入有误")
                    return
            except ValueError:
                messagebox.showerror("错误", "数量输入有误")
                return

        self.organizer.set_rename_no_date_files(self.rename_no_date_var.get())
        self.organizer.set_organize_other_files(self.organize_other_var.get())
        self.organizer.set_other_files_folder(self.other_folder_var.get())
        self.organizer.set_no_date_files_folder(self.no_date_folder_var.get())
        self.organizer.set_max_files_per_folder(folder_limit)

        self.organizer.save_settings()
        
        self.destroy()