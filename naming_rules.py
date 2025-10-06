# naming_rules.py
import tkinter as tk
from tkinter import ttk, messagebox
import re
from base_dialog import BaseDialog

class NamingRulesDialog(BaseDialog):
    def __init__(self, parent, organizer):
        self.organizer = organizer
        super().__init__(parent, "命名规则设置 - FileFlow Pro", 'naming_rules_dialog')
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        folder_naming_frame = ttk.LabelFrame(main_frame, text="文件夹命名模式", padding="10")
        folder_naming_frame.pack(fill=tk.X, pady=(0, 10))

        folder_mode_frame = ttk.Frame(folder_naming_frame)
        folder_mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(folder_mode_frame, text="命名模式:").pack(side=tk.LEFT, padx=5)
        self.folder_mode_var = tk.StringVar(value=self.organizer.folder_naming_mode)
        
        ttk.Radiobutton(folder_mode_frame, text="默认命名", 
                       variable=self.folder_mode_var, value="default",
                       command=self.on_folder_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(folder_mode_frame, text="自定义命名", 
                       variable=self.folder_mode_var, value="custom",
                       command=self.on_folder_mode_change).pack(side=tk.LEFT, padx=5)
        
        if self.organizer.folder_naming_mode == "custom":
            pattern = self.organizer.folder_naming_pattern
            if '{index}' in pattern:
                prefix = pattern.split('{index}')[0]
                prefix = prefix.rstrip(' -_[]()')
            else:
                prefix = pattern
        else:
            prefix = ""
            
        self.folder_custom_var = tk.StringVar(value=prefix)
        self.folder_custom_entry = ttk.Entry(folder_mode_frame, textvariable=self.folder_custom_var, width=15)
        
        mode_frame = ttk.Frame(folder_naming_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(mode_frame, text="整理模式:").pack(side=tk.LEFT, padx=5)
        self.mode_var = tk.StringVar(value=self.organizer.organization_mode)
        
        self.yearly_radio = ttk.Radiobutton(mode_frame, text="按年分类", 
                       variable=self.mode_var, value="yearly",
                       command=self.update_preview)
        self.yearly_radio.pack(side=tk.LEFT, padx=5)
        
        self.monthly_radio = ttk.Radiobutton(mode_frame, text="按月分类", 
                       variable=self.mode_var, value="monthly",
                       command=self.update_preview)
        self.monthly_radio.pack(side=tk.LEFT, padx=5)
        
        self.daily_radio = ttk.Radiobutton(mode_frame, text="按天分类", 
                       variable=self.mode_var, value="daily",
                       command=self.update_preview)
        self.daily_radio.pack(side=tk.LEFT, padx=5)

        file_naming_frame = ttk.LabelFrame(main_frame, text="文件命名模式", padding="10")
        file_naming_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_mode_var = tk.StringVar(value=self.organizer.file_naming_mode)
        
        file_mode_frame = ttk.Frame(file_naming_frame)
        file_mode_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_mode_frame, text="命名模式:").pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(file_mode_frame, text="默认命名", 
                       variable=self.file_mode_var, value="default",
                       command=self.on_file_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(file_mode_frame, text="自定义命名", 
                       variable=self.file_mode_var, value="custom",
                       command=self.on_file_mode_change).pack(side=tk.LEFT, padx=5)

        self.custom_file_frame = ttk.Frame(file_naming_frame)
        self.custom_file_frame.pack(fill=tk.X, pady=5)

        file_components_frame = ttk.Frame(self.custom_file_frame)
        file_components_frame.pack(fill=tk.X, pady=5)
        
        file_check_frame = ttk.Frame(file_components_frame)
        file_check_frame.pack(fill=tk.X, pady=5)

        current_pattern = self.organizer.naming_pattern
        self.file_year_var = tk.BooleanVar(value='{year}' in current_pattern or '年' in current_pattern)
        self.file_month_var = tk.BooleanVar(value='{month}' in current_pattern or '月' in current_pattern)
        self.file_day_var = tk.BooleanVar(value='{day}' in current_pattern or '日' in current_pattern)
        self.file_sequence_var = tk.BooleanVar(value=True)
        
        self.year_check = ttk.Checkbutton(file_check_frame, text="年份", 
                       variable=self.file_year_var,
                       command=self.update_file_pattern)
        self.year_check.pack(side=tk.LEFT, padx=5)
        
        self.month_check = ttk.Checkbutton(file_check_frame, text="月份", 
                       variable=self.file_month_var,
                       command=self.update_file_pattern)
        self.month_check.pack(side=tk.LEFT, padx=5)
        
        self.day_check = ttk.Checkbutton(file_check_frame, text="日期", 
                       variable=self.file_day_var,
                       command=self.update_file_pattern)
        self.day_check.pack(side=tk.LEFT, padx=5)
        
        separator_frame = ttk.Frame(main_frame)
        separator_frame.pack(fill=tk.X, pady=10)

        separator_row1 = ttk.Frame(separator_frame)
        separator_row1.pack(fill=tk.X, pady=5)

        folder_sep_frame = ttk.Frame(separator_row1)
        folder_sep_frame.pack(side=tk.LEFT, padx=(0, 20))
        
        ttk.Label(folder_sep_frame, text="文件夹分隔符:").pack(side=tk.LEFT, padx=5)
        current_folder_pattern = self.organizer.folder_naming_pattern
        default_separator = " "
        if "-" in current_folder_pattern and "{" in current_folder_pattern:
            parts = current_folder_pattern.split("{")[0]
            if "-" in parts:
                default_separator = "-"
            elif "_" in parts:
                default_separator = "_"
        self.folder_separator_var = tk.StringVar(value=default_separator)
        self.folder_separator_combo = ttk.Combobox(folder_sep_frame, textvariable=self.folder_separator_var,
                                             values=["-", "_", " "],
                                             state="readonly", width=8)
        self.folder_separator_combo.pack(side=tk.LEFT, padx=5)
        self.folder_separator_combo.bind('<<ComboboxSelected>>', lambda e: self.update_preview())
        
        file_sep_frame = ttk.Frame(separator_row1)
        file_sep_frame.pack(side=tk.LEFT)
        
        ttk.Label(file_sep_frame, text="文件分隔符:").pack(side=tk.LEFT, padx=5)
        current_file_pattern = self.organizer.naming_pattern
        default_file_separator = " "
        if " " in current_file_pattern:
            default_file_separator = " "
        elif "-" in current_file_pattern:
            default_file_separator = "-"
        elif "_" in current_file_pattern:
            default_file_separator = "_"
        elif "年" in current_file_pattern:
            default_file_separator = "年月日"
        self.file_separator_var = tk.StringVar(value=default_file_separator)
        self.file_separator_combo = ttk.Combobox(file_sep_frame, textvariable=self.file_separator_var,
                                           values=["年月日", "-", "_", " "],
                                           state="readonly", width=8)
        self.file_separator_combo.pack(side=tk.LEFT, padx=5)
        self.file_separator_combo.bind('<<ComboboxSelected>>', lambda e: self.update_file_pattern())
        
        separator_row2 = ttk.Frame(separator_frame)
        separator_row2.pack(fill=tk.X, pady=5)
        
        ttk.Label(separator_row2, text="序列号修饰符:").pack(side=tk.LEFT, padx=5)
        current_wrapper = self.organizer.sequence_wrapper
        default_wrapper = "[]"
        if current_wrapper == "()":
            default_wrapper = "()"
        elif current_wrapper == "":
            default_wrapper = "无"
        self.wrapper_var = tk.StringVar(value=default_wrapper)
        wrapper_combo = ttk.Combobox(separator_row2, textvariable=self.wrapper_var,
                                    values=["()", "[]", "无"],
                                    state="readonly", width=8)
        wrapper_combo.pack(side=tk.LEFT, padx=5)
        wrapper_combo.bind('<<ComboboxSelected>>', lambda e: self.update_file_pattern())
        
        preview_frame = ttk.Frame(main_frame)
        preview_frame.pack(fill=tk.X, pady=10)
        
        self.preview_var = tk.StringVar(value="")
        preview_entry = ttk.Entry(preview_frame, textvariable=self.preview_var, state='readonly', width=50)
        preview_entry.pack(fill=tk.X, pady=2)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="确定", command=self.apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.on_folder_mode_change()
        self.on_file_mode_change()
        self.update_file_pattern()
        self.update_preview()
    
    def on_folder_mode_change(self):
        """文件夹命名模式变化"""
        if self.folder_mode_var.get() == "default":
            self.yearly_radio.config(state=tk.NORMAL)
            self.monthly_radio.config(state=tk.NORMAL)
            self.daily_radio.config(state=tk.NORMAL)

            self.folder_custom_entry.pack_forget()

            self.folder_separator_combo.config(state=tk.DISABLED)
        else:
            self.yearly_radio.config(state=tk.DISABLED)
            self.monthly_radio.config(state=tk.DISABLED)
            self.daily_radio.config(state=tk.DISABLED)

            self.folder_custom_entry.pack(side=tk.LEFT, padx=5)
            self.folder_custom_entry.bind('<KeyRelease>', self.update_preview)

            self.folder_separator_combo.config(state=tk.NORMAL)
        self.update_preview()
    
    def on_file_mode_change(self):
        """文件命名模式变化"""
        if self.file_mode_var.get() == "default":
            self.year_check.config(state=tk.DISABLED)
            self.month_check.config(state=tk.DISABLED)
            self.day_check.config(state=tk.DISABLED)

            self.file_separator_combo.config(state=tk.DISABLED)
        else:

            self.year_check.config(state=tk.NORMAL)
            self.month_check.config(state=tk.NORMAL)
            self.day_check.config(state=tk.NORMAL)

            self.file_separator_combo.config(state=tk.NORMAL)

            if not (self.file_year_var.get() or self.file_month_var.get() or self.file_day_var.get()):
                self.file_year_var.set(True)
                
        self.update_file_pattern()
        self.update_preview()
    
    def validate_date_components(self):
        """验证至少有一个日期组件被选中"""
        if not (self.file_year_var.get() or self.file_month_var.get() or self.file_day_var.get()):
            self.file_year_var.set(True)
            return False
        return True
    
    def update_file_pattern(self):
        """更新文件命名模式"""
        self.validate_date_components()

        if self.file_mode_var.get() == "default":
            self.update_preview()
            return
            
        components = []
        separator = self.file_separator_var.get()
        
        if self.file_year_var.get():
            if separator == "年月日":
                components.append("{year}年")
            else:
                components.append("{year}")
                
        if self.file_month_var.get():
            if separator == "年月日":
                components.append("{month}月")
            else:
                components.append("{month}")
                
        if self.file_day_var.get():
            if separator == "年月日":
                components.append("{day}日")
            else:
                components.append("{day}")

        wrapper = self.wrapper_var.get()
        if wrapper == "无":
            components.append("{sequence}")
        else:
            components.append(wrapper[0] + "{sequence}" + wrapper[1])
        
        if components:
            if separator == "年月日":
                pattern = "".join(components)  
            else:
                pattern = separator.join(components)
        else:
            pattern = "请选择至少一个日期组件"
        
        self.update_preview()
    
    def sanitize_filename(self, name):
        """清理文件名中的非法字符"""
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        return re.sub(illegal_chars, '_', name)
    
    def update_preview(self, event=None):
        """更新命名预览"""
        try:
            if self.folder_mode_var.get() == "default":
                if self.mode_var.get() == "daily":
                    folder_preview = "2024-03-15"
                elif self.mode_var.get() == "monthly":
                    folder_preview = "2024-03"
                else:  
                    folder_preview = "2024"
            else:
                custom_name = self.folder_custom_var.get()
                separator = self.folder_separator_var.get()
                wrapper = self.wrapper_var.get()
                
                if wrapper == "无":
                    sequence = "1"
                elif wrapper and len(wrapper) >= 2:
                    sequence = f"{wrapper[0]}1{wrapper[1]}"
                else:
                    sequence = "1"
                    
                folder_preview = f"{custom_name}{separator}{sequence}"
                folder_preview = self.sanitize_filename(folder_preview)

            if self.file_mode_var.get() == "default":
                date_part = "2024-03-15" 
                wrapper = self.wrapper_var.get()
                if wrapper == "无":
                    sequence = "001"
                elif wrapper and len(wrapper) >= 2:
                    sequence = f"{wrapper[0]}001{wrapper[1]}"
                else:
                    sequence = "001"

                file_preview = f"{date_part} {sequence}.jpg"
            else:
                year_part = "2024"
                month_part = "03"
                day_part = "15"

                components = []
                separator = self.file_separator_var.get()
                
                if self.file_year_var.get():
                    if separator == "年月日":
                        components.append(f"{year_part}年")
                    else:
                        components.append(f"{year_part}")
                        
                if self.file_month_var.get():
                    if separator == "年月日":
                        components.append(f"{month_part}月")
                    else:
                        components.append(f"{month_part}")
                        
                if self.file_day_var.get():
                    if separator == "年月日":
                        components.append(f"{day_part}日")
                    else:
                        components.append(f"{day_part}")

                wrapper = self.wrapper_var.get()
                if wrapper == "无":
                    components.append("001")
                elif wrapper and len(wrapper) >= 2:
                    components.append(f"{wrapper[0]}001{wrapper[1]}")
                else:
                    components.append("001")
                
                if components:
                    if separator == "年月日":
                        file_preview = "".join(components) + ".jpg"
                    else:
                        file_preview = separator.join(components) + ".jpg"
                else:
                    file_preview = "请选择文件命名组件"

                file_preview = self.sanitize_filename(file_preview)
            
            preview = f"文件夹: {folder_preview} | 文件: {file_preview}"
            self.preview_var.set(preview)
        except Exception as e:
            self.preview_var.set(f"预览错误: {str(e)}")
    
    def apply_changes(self):
        """应用更改"""
        if self.file_mode_var.get() == "custom" and not self.validate_date_components():
            messagebox.showwarning("警告", "在自定义文件命名模式下，必须至少选择一个日期组件（年、月、日）")
            return

        self.organizer.set_organization_mode(self.mode_var.get())

        self.organizer.set_folder_naming_mode(self.folder_mode_var.get())
        if self.folder_mode_var.get() == "custom":
            custom_name = self.folder_custom_var.get()
            separator = self.folder_separator_var.get()
            wrapper = self.wrapper_var.get()
            
            if wrapper == "无":
                sequence_pattern = "{index}"
            else:
                sequence_pattern = wrapper[0] + "{index}" + wrapper[1]

            pattern = f"{custom_name}{separator}{sequence_pattern}"
            self.organizer.set_folder_naming_pattern(pattern)

        self.organizer.set_file_naming_mode(self.file_mode_var.get())
        if self.file_mode_var.get() == "custom":
            components = []
            separator = self.file_separator_var.get()
            
            if self.file_year_var.get():
                if separator == "年月日":
                    components.append("{year}年")
                else:
                    components.append("{year}")
                    
            if self.file_month_var.get():
                if separator == "年月日":
                    components.append("{month}月")
                else:
                    components.append("{month}")
                    
            if self.file_day_var.get():
                if separator == "年月日":
                    components.append("{day}日")
                else:
                    components.append("{day}")

            wrapper = self.wrapper_var.get()
            if wrapper == "无":
                components.append("{sequence}")
            else:
                components.append(wrapper[0] + "{sequence}" + wrapper[1])
            
            if components:
                if separator == "年月日":
                    pattern = "".join(components)
                else:
                    pattern = separator.join(components)
                self.organizer.set_naming_pattern(pattern)

        wrapper = self.wrapper_var.get()
        if wrapper == "无":
            self.organizer.set_sequence_wrapper("")
        else:
            self.organizer.set_sequence_wrapper(wrapper)

        self.organizer.save_settings()
        
        self.destroy()