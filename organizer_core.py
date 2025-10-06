# organizer_core.py
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import time
import shutil
import json
import threading
import re

from config import (DEFAULT_IMAGE_FORMATS, DEFAULT_VIDEO_FORMATS, DEFAULT_DOCUMENT_FORMATS,
                    MAX_FILES_PER_FOLDER, BACKUP_FOLDER_NAME,
                    DEFAULT_OTHER_FILES_FOLDER, DEFAULT_NO_DATE_FOLDER, SETTINGS_FILE)
from file_operations import FileOperations
from metadata_extractor import MetadataExtractor


class FileOrganizer:
    def __init__(self):
        self.scanned_files = {'images': [], 'videos': [], 'documents': [], 'other': []}
        self.image_formats = set(DEFAULT_IMAGE_FORMATS)
        self.video_formats = set(DEFAULT_VIDEO_FORMATS)
        self.document_formats = set(DEFAULT_DOCUMENT_FORMATS)
        self.other_formats = set()
        self.duplicate_handling = "resort"  
        self.identical_files_removed = 0 
        self.naming_pattern = "{date}{separator}{sequence}"  
        self.folder_naming_pattern = "{year}-{index}"  
        self.date_priority_list = ["exif", "metadata", "filename", "filetime", "creationtime",
                                   "filesystem"]  
        self.rename_no_date_files = True  
        self.organize_other_files = True 
        self.other_files_folder = DEFAULT_OTHER_FILES_FOLDER  
        self.no_date_files_folder = DEFAULT_NO_DATE_FOLDER  
        self.organization_mode = "yearly"  
        self.sequence_wrapper = "[]" 
        self.folder_naming_mode = "default"  
        self.file_naming_mode = "default"  
        self.max_files_per_folder = MAX_FILES_PER_FOLDER  
        self.folder_separator = "-"  
        self.file_separator = ""  
        self.is_paused = False
        self.is_terminated = False
        self.rollback_log = []  
        self.final_folder_stats = {} 
        self.log_search_term = ""
        self.log_filter_level = "ALL" 
        self.operation_start_time = 0
        self.current_operation = ""
        self.estimated_remaining_time = 0
        self.load_settings()

    @staticmethod
    def get_sequence_format(total_count):
        """根据总文件数获取序列号的格式字符串，用于控制填充位数"""
        if total_count < 100:
            return "{:02d}"
        return "{:03d}"

    def _move_files_to_folders(self, dated_files, folder_structure, source_dir, dest_dir, progress_callback=None,
                               is_resort=False, progress_offset=0, progress_scale=100):
        """移动文件到整理的文件夹 - 修复版本，支持多级文件夹结构和正确的文件命名"""
        date_key_counts = defaultdict(lambda: {'images': 0, 'videos': 0, 'documents': 0, 'other': 0})
        for date_key, files in dated_files.items():
            for file_type in ['images', 'videos', 'documents', 'other']:
                if file_type in files:
                    date_key_counts[date_key][file_type] += len(files[file_type])

        year_file_counts = defaultdict(int)
        for date_key, files in dated_files.items():
            year = "未知日期" if date_key == "N" else date_key.split('-')[0]

            for file_type in ['images', 'videos', 'documents', 'other']:
                if file_type in files:
                    year_file_counts[year] += len(files[file_type])

        date_key_folder_assignments = {}
        for date_key, files in dated_files.items():
            if date_key == "N":
                total_files_in_date = sum(len(files[file_type]) for file_type in files)
                if total_files_in_date > 0:
                     date_key_folder_assignments[date_key] = [folder_structure.get("未知日期", [os.path.join(dest_dir, self.no_date_files_folder)])[0]] * total_files_in_date
                continue

            year = date_key.split('-')[0]
            total_files_in_date = sum(len(files[file_type]) for file_type in files)
            
            date_folders = folder_structure.get(date_key, [])
            if not date_folders:
                date_folders = folder_structure.get(year, [])
            
            folder_count = len(date_folders)
            if folder_count == 0:
                continue

            files_per_folder = [0] * folder_count
            assignment = []
            
            current_folder = 0
            remaining_files = total_files_in_date

            while remaining_files > 0:
                if current_folder >= folder_count:
                    last_folder_index = folder_count - 1
                    assignment.extend([date_folders[last_folder_index]] * remaining_files)
                    files_per_folder[last_folder_index] += remaining_files
                    break

                available_space = self.max_files_per_folder - files_per_folder[current_folder]

                files_to_assign = min(remaining_files, available_space)

                if files_to_assign > 0:
                    folder_path = date_folders[current_folder]
                    assignment.extend([folder_path] * files_to_assign)
                    
                    files_per_folder[current_folder] += files_to_assign
                    remaining_files -= files_to_assign
                
                if remaining_files > 0:
                    current_folder += 1

            for i, count in enumerate(files_per_folder):
                if count > self.max_files_per_folder:
                    if progress_callback:
                        self._progress_callback_wrapper(message=f"[Warning] 文件夹 {date_folders[i]} 文件数超出限制 ({count}/{self.max_files_per_folder})，正在重新分配...", core_callback=progress_callback)

                    assignment = []
                    base_files_per_folder = total_files_in_date // folder_count
                    remainder = total_files_in_date % folder_count
                    
                    for j in range(folder_count):
                        files_this_folder = base_files_per_folder + (1 if j < remainder else 0)
                        assignment.extend([date_folders[j]] * files_this_folder)
                    
                    break

            date_key_folder_assignments[date_key] = assignment

        if self.folder_naming_mode == "custom":
            sequence_counters = {'images': 0, 'videos': 0, 'documents': 0, 'other': 0}
        else:
            sequence_counters = {}
            for date_key in dated_files:
                sequence_counters[date_key] = {'images': 0, 'videos': 0, 'documents': 0, 'other': 0}

        current_counts = defaultdict(lambda: {'images': 0, 'videos': 0, 'documents': 0, 'other': 0})
        total_files = 0
        for files in dated_files.values():
            for file_type in ['images', 'videos', 'documents', 'other']:
                if file_type in files:
                    total_files += len(files[file_type])

        processed_files = 0
        self.final_folder_stats = {} 

        if total_files == 0:
            return

        unknown_folder = os.path.join(dest_dir, self.no_date_files_folder)
        other_folder = os.path.join(dest_dir, self.other_files_folder)

        for file_type in ['images', 'videos', 'documents', 'other']:
            for date_key, files in sorted(dated_files.items()):
                if progress_callback and self._progress_callback_wrapper(check_terminate=True, core_callback=progress_callback):
                    self.is_terminated = True
                    return

                if file_type not in files:
                    continue

                year = "未知日期" if date_key == "N" else date_key.split('-')[0]

                for i, (file_path, date) in enumerate(files[file_type]): 

                    if progress_callback and self._progress_callback_wrapper(check_terminate=True, core_callback=progress_callback):
                        self.is_terminated = True
                        return

                    original_path = os.path.abspath(file_path)

                    if year == "未知日期":
                        target_folder = unknown_folder
                    elif file_type == 'other' and not self.organize_other_files:
                        current_counts[date_key][file_type] += 1
                        processed_files += 1
                        continue
                    elif file_type == 'other':
                        target_folder = other_folder
                    else:
                        file_index = current_counts[date_key][file_type]
                        if date_key in date_key_folder_assignments and file_index < len(date_key_folder_assignments[date_key]):
                            target_folder = date_key_folder_assignments[date_key][file_index]
                        else:
                            if date_key in folder_structure and len(folder_structure[date_key]) > 0:
                                target_folder = folder_structure[date_key][0]
                            elif year in folder_structure and len(folder_structure[year]) > 0:
                                target_folder = folder_structure[year][0]
                            else:
                                target_folder = unknown_folder 

                    if self.folder_naming_mode == "custom":
                        current_sequence = sequence_counters[file_type]
                        sequence_counters[file_type] += 1
                    else:
                        current_sequence = sequence_counters[date_key][file_type]
                        sequence_counters[date_key][file_type] += 1

                    total_seq_count = date_key_counts[date_key][file_type] if self.folder_naming_mode != "custom" and date_key in date_key_counts else total_files
                    
                    seq_format = FileOrganizer.get_sequence_format(total_seq_count)
                    sequence_number_raw = seq_format.format(current_sequence + 1)

                    if self.sequence_wrapper and len(self.sequence_wrapper) >= 2:
                        wrapped_sequence = f"{self.sequence_wrapper[0]}{sequence_number_raw}{self.sequence_wrapper[-1]}"
                    else:
                        wrapped_sequence = sequence_number_raw
                        
                    
                    if date_key == "N" and not self.rename_no_date_files:
                        base_name = Path(file_path).stem
                    else:
                        if self.file_naming_mode == "default":
                            if date_key == "N":
                                date_part = "未知日期"
                            else:
                                if hasattr(date, 'strftime'):
                                    date_part = date.strftime("%Y-%m-%d")
                                else:
                                    try:
                                        if len(date_key) == 4:  
                                            date_part = f"{date_key}-01-01"
                                        elif len(date_key) == 7:  
                                            date_part = f"{date_key}-01"
                                        else:  
                                            date_part = date_key
                                    except:
                                        date_part = date_key

                            base_name = f"{date_part} {wrapped_sequence}"

                        else:
                            try:
                                year_part = ""
                                month_part = ""
                                day_part = ""

                                if date_key != "N":
                                    year_part = date.strftime("%Y")
                                    month_part = date.strftime("%m")
                                    day_part = date.strftime("%d")

                                temp_name = self.naming_pattern.format(
                                    date=date_key,
                                    sequence=sequence_number_raw, 
                                    wrapped_sequence=wrapped_sequence,
                                    year=year_part,
                                    month=month_part,
                                    day=day_part,
                                    separator=self.file_separator if self.file_separator != "无" else " " 
                                )

                                base_name = temp_name.strip()

                                base_name = re.sub(r'\s+', ' ', base_name)

                                custom_sep = self.file_separator if self.file_separator != "无" else " "
                                if custom_sep:
                                    custom_sep_pattern = re.escape(custom_sep)
                                    base_name = re.sub(f'(^[{custom_sep_pattern}\\s]+)|([{custom_sep_pattern}\\s]+$)', '', base_name)

                                if not base_name and wrapped_sequence:
                                    base_name = wrapped_sequence
                                
                            except Exception as e:
                                if date_key == "N":
                                    date_part = "未知日期"
                                else:
                                    date_part = date_key

                                base_name = f"{date_part}{self.file_separator if self.file_separator != '无' else ' '}{wrapped_sequence}"
                                if progress_callback:
                                    self._progress_callback_wrapper(message=f"[Warning] 自定义命名失败，使用默认命名: {str(e)}", core_callback=progress_callback)

                    file_ext = Path(file_path).suffix
                    new_filename = base_name + file_ext
                    new_file_path = os.path.join(target_folder, new_filename)

                    if os.path.exists(new_file_path):
                        unique_base_name = base_name.replace(wrapped_sequence, "").strip(self.file_separator if self.file_separator != "无" else " ")

                        if not unique_base_name:
                             unique_base_name = Path(file_path).stem
                        
                        unique_base_name = unique_base_name.strip(' -_')

                        new_file_path = FileOperations.get_unique_filename(target_folder, unique_base_name, file_ext)


                    if not is_resort:
                        if os.path.exists(new_file_path):
                            if FileOperations.are_files_identical(original_path, new_file_path):
                                try:
                                    os.remove(original_path)
                                    self.identical_files_removed += 1
                                    if progress_callback:
                                        self._progress_callback_wrapper(message=f"[Info] 删除完全相同的文件: {Path(original_path).name}", core_callback=progress_callback)
                                    current_counts[date_key][file_type] += 1
                                    processed_files += 1
                                    continue
                                except Exception as e:
                                    if progress_callback:
                                        self._progress_callback_wrapper(message=f"[Warning] 无法删除重复文件 {Path(original_path).name}: {str(e)}", core_callback=progress_callback)

                    try:
                        if original_path != new_file_path:
                            self.rollback_log.append(('move', original_path, new_file_path))
                            FileOperations.safe_move(original_path, new_file_path)
                        canonical_target_folder = os.path.abspath(target_folder)
                        self.final_folder_stats[canonical_target_folder] = self.final_folder_stats.get(canonical_target_folder, 0) + 1

                        current_counts[date_key][file_type] += 1
                        processed_files += 1
                        if progress_callback:
                            progress = int(processed_files / total_files * 100)
                            self.update_progress_estimate(progress)
                            self._progress_callback_wrapper(value=progress, message="", core_callback=progress_callback)

                    except Exception as e:
                        if progress_callback:
                            self._progress_callback_wrapper(message=f"[Error] 移动文件失败 {Path(original_path).name} -> {Path(new_file_path).name}: {str(e)}", core_callback=progress_callback)

        if progress_callback:
            self._progress_callback_wrapper(value=100, message="[Success] 所有文件移动完成", core_callback=progress_callback)

    def load_settings(self):
        """从文件加载设置"""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                self.image_formats = set(settings.get('image_formats', DEFAULT_IMAGE_FORMATS))
                self.video_formats = set(settings.get('video_formats', DEFAULT_VIDEO_FORMATS))
                self.document_formats = set(settings.get('document_formats', DEFAULT_DOCUMENT_FORMATS))
                self.other_formats = set(settings.get('other_formats', []))

                self.organization_mode = settings.get('organization_mode', 'yearly')
                self.folder_naming_mode = settings.get('folder_naming_mode', 'default')
                self.file_naming_mode = settings.get('file_naming_mode', 'default')
                self.naming_pattern = settings.get('naming_pattern', '{date}{separator}{sequence}')
                self.folder_naming_pattern = settings.get('folder_naming_pattern', '{year}-{index}')
                self.sequence_wrapper = settings.get('sequence_wrapper', '[]')

                self.folder_separator = settings.get('folder_separator', '-')
                self.file_separator = settings.get('file_separator', '') 

                self.date_priority_list = settings.get('date_priority_list',
                                                       ['exif', 'metadata', 'filename', 'filetime', 'creationtime',
                                                        'filesystem'])
                self.rename_no_date_files = settings.get('rename_no_date_files', True)
                self.organize_other_files = settings.get('organize_other_files', True)
                self.other_files_folder = settings.get('other_files_folder', DEFAULT_OTHER_FILES_FOLDER)
                self.no_date_files_folder = settings.get('no_date_files_folder', DEFAULT_NO_DATE_FOLDER)
                self.max_files_per_folder = settings.get('max_files_per_folder', MAX_FILES_PER_FOLDER)

        except (IOError, json.JSONDecodeError) as e:
            print(f"加载设置失败: {str(e)}")
        except Exception as e:
            print(f"未知错误加载设置: {str(e)}")

    def save_settings(self):
        """保存设置到文件"""
        try:
            settings = {
                'image_formats': list(self.image_formats),
                'video_formats': list(self.video_formats),
                'document_formats': list(self.document_formats),
                'other_formats': list(self.other_formats),

                'organization_mode': self.organization_mode,
                'folder_naming_mode': self.folder_naming_mode,
                'file_naming_mode': self.file_naming_mode,
                'naming_pattern': self.naming_pattern,
                'folder_naming_pattern': self.folder_naming_pattern,
                'sequence_wrapper': self.sequence_wrapper,

                'folder_separator': self.folder_separator,
                'file_separator': self.file_separator,

                'date_priority_list': self.date_priority_list,
                'rename_no_date_files': self.rename_no_date_files,
                'organize_other_files': self.organize_other_files,
                'other_files_folder': self.other_files_folder,
                'no_date_files_folder': self.no_date_files_folder,
                'max_files_per_folder': self.max_files_per_folder
            }

            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)

        except (IOError, TypeError) as e:
            print(f"保存设置失败: {str(e)}")
        except Exception as e:
            print(f"未知错误保存设置: {str(e)}")

    def set_folder_separator(self, separator):
        """设置文件夹分隔符"""
        self.folder_separator = separator

    def set_file_separator(self, separator):
        """设置文件分隔符"""

        self.file_separator = '' if separator == '无' else separator

    def set_log_search_term(self, search_term):
        """设置日志搜索关键词"""
        self.log_search_term = search_term.lower()

    def set_log_filter_level(self, level):
        """设置日志过滤级别"""
        self.log_filter_level = level

    def filter_logs(self, logs):
        """根据搜索词和过滤级别过滤日志 - 修复版本，大小写不敏感比较"""
        filtered = []
        for log in logs:
            log_level = log.get('level', '').upper()
            filter_level = self.log_filter_level.upper()

            if self.log_filter_level != "ALL" and log_level != filter_level:
                continue

            if self.log_search_term and self.log_search_term not in log.get('message', '').lower():
                continue

            filtered.append(log)
        return filtered

    def start_operation_timing(self, operation_name):
        """开始操作计时"""
        self.current_operation = operation_name
        self.operation_start_time = time.time()
        self.estimated_remaining_time = 0

    def update_progress_estimate(self, progress_percent):
        """更新进度预估"""
        if progress_percent > 0 and self.operation_start_time > 0:
            elapsed_time = time.time() - self.operation_start_time
            total_estimated_time = elapsed_time / (progress_percent / 100)
            self.estimated_remaining_time = total_estimated_time - elapsed_time

    def get_remaining_time_string(self):
        """获取剩余时间字符串"""
        if self.estimated_remaining_time <= 0:
            return "计算中..."

        if self.estimated_remaining_time >= 3600:
            return time.strftime("%Hh %Mm %Ss", time.gmtime(self.estimated_remaining_time))
        elif self.estimated_remaining_time >= 60:
            return time.strftime("%Mm %Ss", time.gmtime(self.estimated_remaining_time))
        else:
            return f"{int(self.estimated_remaining_time)}s"

    def pause_organizing(self):
        self.is_paused = True

    def resume_organizing(self):
        self.is_paused = False

    def terminate_organizing(self):
        """设置终止标记，允许当前正在执行的操作退出"""
        self.is_terminated = True

    def reset_state(self):
        """重置状态，准备下一次运行"""
        self.is_paused = False
        self.is_terminated = False
        self.rollback_log = []
        self.identical_files_removed = 0
        self.log_search_term = ""
        self.log_filter_level = "ALL"
        self.operation_start_time = 0
        self.current_operation = ""
        self.estimated_remaining_time = 0
        self.final_folder_stats = {}

    def set_naming_pattern(self, pattern):
        """设置文件命名模式"""
        self.naming_pattern = pattern

    def set_folder_naming_pattern(self, pattern):
        """设置文件夹命名模式"""
        self.folder_naming_pattern = pattern

    def set_date_priority_list(self, priority_list):
        """设置日期提取优先级列表"""
        self.date_priority_list = priority_list

    def set_rename_no_date_files(self, rename):
        """设置是否重命名无日期文件"""
        self.rename_no_date_files = rename

    def set_organize_other_files(self, organize):
        """设置是否整理其他文件"""
        self.organize_other_files = organize

    def set_other_files_folder(self, folder_name):
        """设置其他文件文件夹名称"""
        self.other_files_folder = folder_name

    def set_no_date_files_folder(self, folder_name):
        """设置无日期文件文件夹名称"""
        self.no_date_files_folder = folder_name

    def set_organization_mode(self, mode):
        """设置整理模式"""
        self.organization_mode = mode

    def set_sequence_wrapper(self, wrapper):
        """设置序列号包裹符号"""
        self.sequence_wrapper = wrapper

    def set_folder_naming_mode(self, mode):
        """设置文件夹命名模式"""
        self.folder_naming_mode = mode

    def set_file_naming_mode(self, mode):
        """设置文件命名模式"""
        self.file_naming_mode = mode

    def set_max_files_per_folder(self, max_files):
        """设置单个文件夹最大文件数"""
        self.max_files_per_folder = max_files

    def _progress_callback_wrapper(self, value=None, message=None, check_terminate=False, progress_offset=0,
                                   progress_scale=100, is_backup=False, core_callback=None):
        """核心回调函数的包装器，处理暂停/终止检查和进度缩放 - 修复消息为None的问题"""
        if check_terminate:
            if self.is_terminated:
                return True
            while self.is_paused:
                if core_callback:
                    core_callback(-1, "[Info] 任务已暂停，等待用户操作...")
                if self.is_terminated:
                    return True
                time.sleep(0.1)
            return False

        if core_callback:
            safe_message = message if message is not None else ""
            
            if is_backup and safe_message and re.match(r'^\d+/\d+$', safe_message.strip()):
                safe_message = ""  

            if value is not None and value >= 0:
                real_value = progress_offset + int(value * progress_scale / 100)
                real_value = min(100, real_value)
                core_callback(real_value, safe_message)
            else:
                core_callback(-1, safe_message)
            return

    def set_formats(self, image_formats, video_formats, document_formats, other_formats):
        """设置自定义格式"""
        self.image_formats = set(DEFAULT_IMAGE_FORMATS) | set(image_formats)
        self.video_formats = set(DEFAULT_VIDEO_FORMATS) | set(video_formats)
        self.document_formats = set(DEFAULT_DOCUMENT_FORMATS) | set(document_formats)
        self.other_formats = set(other_formats)

    def set_duplicate_handling(self, method):
        """设置重复文件处理方式"""
        self.duplicate_handling = method

    def log(self, message, tag='[Core]'):
        """简单的日志方法，用于在 GUI 外部运行时显示信息"""
        print(f"{tag} {message}")

    def scan_directory(self, directory, exclude_dir=None, is_resort=False):
        """扫描目录中的媒体文件 - 使用多线程优化
        is_resort: 是否为重新整理模式，重新整理时只扫描目标目录的直接内容
        """
        if exclude_dir:
            exclude_dir = os.path.abspath(exclude_dir)

        try:
            self.start_operation_timing("文件扫描")

            scanned_files = self._scan_directory_fallback(directory, exclude_dir, is_resort)
            
            for key in ['images', 'videos', 'documents', 'other']:
                if key not in scanned_files:
                    scanned_files[key] = []

            self.scanned_files = scanned_files

            return self.scanned_files

        except Exception as e:
            print(f"扫描目录失败: {str(e)}")
            return self._scan_directory_fallback(directory, exclude_dir, is_resort)

    def _scan_directory_fallback(self, directory, exclude_dir=None, is_resort=False):
        """回退的单线程目录扫描
        is_resort: 是否为重新整理模式，重新整理时只扫描目标目录的直接内容
        """
        images = []
        videos = []
        documents = []
        other_files = []

        directory = os.path.abspath(directory)
        if exclude_dir:
            exclude_dir = os.path.abspath(exclude_dir)

        if is_resort:
            try:
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)

                    if os.path.isfile(item_path):
                        file = item
                        if file.startswith('.') or file.endswith('.zip'):
                            continue

                        file_path = item_path
                        file_ext = Path(file).suffix.lower()

                        if exclude_dir and os.path.abspath(file_path).startswith(exclude_dir):
                            continue

                        if file_ext in self.image_formats:
                            images.append(file_path)
                        elif file_ext in self.video_formats:
                            videos.append(file_path)
                        elif file_ext in self.document_formats:
                            documents.append(file_path)
                        elif file_ext in self.other_formats:
                            other_files.append(file_path)
                        else:
                            other_files.append(file_path)
            except Exception as e:
                print(f"扫描目录失败: {str(e)}")
        else:
            for root, dirs, files in os.walk(directory):
                dirs[:] = [d for d in dirs if
                           not d.startswith('.') and BACKUP_FOLDER_NAME.lower() not in d.lower() and "BACKUP" not in d.upper()]
                
                if exclude_dir:
                    dirs[:] = [d for d in dirs if not os.path.abspath(os.path.join(root, d)).startswith(exclude_dir)]

                for file in files:
                    if file.startswith('.') or file.endswith('.zip'):
                        continue

                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()

                    if exclude_dir and os.path.abspath(file_path).startswith(exclude_dir):
                        continue

                    if file_ext in self.image_formats:
                        images.append(file_path)
                    elif file_ext in self.video_formats:
                        videos.append(file_path)
                    elif file_ext in self.document_formats:
                        documents.append(file_path)
                    elif file_ext in self.other_formats:
                        other_files.append(file_path)
                    else:
                        other_files.append(file_path)

        self.scanned_files = {'images': images, 'videos': videos, 'documents': documents, 'other': other_files}
        return self.scanned_files

    def organize_media(self, source_dir, dest_dir, backup=True, progress_callback=None, is_resort=False):
        """主要的整理功能"""
        if not is_resort:
            self.reset_state()

        os.makedirs(dest_dir, exist_ok=True)

        if progress_callback:
            self._progress_callback_wrapper(value=0, message="[Progress] 启动整理过程...", core_callback=progress_callback)

        if backup and not is_resort:
            self.start_operation_timing("备份操作")

            backup_callback = lambda val=None, msg=None, check_terminate=False: self._progress_callback_wrapper(
                value=val, message=msg, check_terminate=check_terminate,
                progress_offset=0, progress_scale=15, is_backup=True, core_callback=progress_callback
            )

            try:
                backup_path = FileOperations.create_zip_backup(source_dir, dest_dir, progress_callback=backup_callback)

                if backup_path == "TERMINATED":
                    if progress_callback:
                        self._progress_callback_wrapper(message="[Error] 备份操作被用户终止", core_callback=progress_callback)
                    self.is_terminated = True
                    return "TERMINATED"

                if progress_callback:
                    self._progress_callback_wrapper(value=15, message="[Progress] 备份完成，开始文件扫描...", core_callback=progress_callback)

            except Exception as e:
                if progress_callback:
                    self._progress_callback_wrapper(message=f"[Error] 备份失败: {str(e)}", core_callback=progress_callback)
                raise e

        else:
            if progress_callback:
                self._progress_callback_wrapper(value=15, message="[Info] 跳过备份，开始文件扫描...", core_callback=progress_callback)

        if progress_callback:
            self._progress_callback_wrapper(value=16, message="[Progress] 正在大规模扫描源目录...", core_callback=progress_callback)

        try:
            exclude_path = None if is_resort else dest_dir
            files = self.scan_directory(source_dir, exclude_path, is_resort)
            
            for key in ['images', 'videos', 'documents', 'other']:
                if key not in files:
                    files[key] = []
            all_media = files['images'] + files['videos'] + files['documents'] + files['other']

        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Error] 扫描目录失败: {str(e)}", core_callback=progress_callback)
            raise e

        if not all_media:
            if progress_callback:
                self._progress_callback_wrapper(value=100, message="[Success] 未找到媒体文件，完成", core_callback=progress_callback)
            return {
                'images_processed': 0, 'videos_processed': 0, 'documents_processed': 0, 'other_processed': 0,
                'folder_structure': {}, 'identical_files_removed': 0
            }

        if progress_callback:
            self._progress_callback_wrapper(value=18, message=f"[Info] 扫描完成: 找到 {len(all_media)} 个文件。", core_callback=progress_callback)
            self._progress_callback_wrapper(value=20, message="[Progress] 正在提取元数据和日期信息 (耗时操作)...", core_callback=progress_callback)

        try:
            metadata_progress_callback = lambda val=None, msg=None, check_terminate=False: self._progress_callback_wrapper(
                value=val, message=msg, check_terminate=check_terminate,
                progress_offset=20, progress_scale=5, core_callback=progress_callback
            )
            dated_files = self._group_files_by_date(all_media, metadata_progress_callback)
        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Error] 日期提取失败: {str(e)}", core_callback=progress_callback)
            raise e

        if progress_callback:
            self._progress_callback_wrapper(value=25, message="[Progress] 日期提取和分组完成。正在创建文件夹结构...", core_callback=progress_callback)

        try:
            folder_structure = self._create_folder_structure(dated_files, dest_dir)
        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Error] 创建文件夹结构失败: {str(e)}", core_callback=progress_callback)
            raise e

        move_progress_offset = 30
        move_progress_scale = 40
        if progress_callback:
            self._progress_callback_wrapper(value=move_progress_offset, message="[Progress] 开始移动和重命名文件...", core_callback=progress_callback)

        move_callback = lambda val=None, msg=None, check_terminate=False: self._progress_callback_wrapper(
            value=val, message=msg, check_terminate=check_terminate,
            progress_offset=move_progress_offset, progress_scale=move_progress_scale, core_callback=progress_callback
        )

        try:
            self._move_files_to_folders(dated_files, folder_structure, source_dir, dest_dir, move_callback, is_resort)
        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Error] 移动文件失败: {str(e)}", core_callback=progress_callback)
            raise e

        if self.is_terminated:
            return "TERMINATED"

        self._cleanup_and_renumber_folders(dest_dir, progress_callback)
        
        if progress_callback:
            self._progress_callback_wrapper(value=75, message="[Progress] 文件移动和清理完成", core_callback=progress_callback)

        total_files_processed = len(all_media) - self.identical_files_removed
        total_folders_used = len(self.final_folder_stats)
        
        folder_list_message = f"总计创建/使用了 {total_folders_used} 个目标文件夹。\n"
        
        if total_folders_used > 0:
            folder_list_message += "详细文件夹统计 (路径相对于目标目录):\n"
            
            sorted_stats = self._sort_folders_by_time(self.final_folder_stats, dest_dir)
            
            for folder_path, file_count in sorted_stats:
                relative_path = os.path.relpath(folder_path, dest_dir)
                folder_list_message += f"  - 文件夹: {relative_path}，文件数量: {file_count}\n"
        
        final_message = f"""[Success] --- 整理全部完成 ---
总计处理文件: {len(all_media)}
实际移动文件: {total_files_processed}
删除了 {self.identical_files_removed} 个完全相同的文件 (重复)
所有文件现已按日期顺序和序列号重命名
----------------------------------------
{folder_list_message.strip()}
----------------------------------------
全部完成 (100%)"""
        
        if progress_callback:
            self._progress_callback_wrapper(value=100, message=final_message, core_callback=progress_callback)

        result = {
            'images_processed': len(files['images']),
            'videos_processed': len(files['videos']),
            'documents_processed': len(files['documents']),
            'other_processed': len(files['other']),
            'folder_structure': folder_structure,
            'identical_files_removed': self.identical_files_removed
        }

        return result

    def _sort_folders_by_time(self, folder_stats, dest_dir):
        """按时间顺序对文件夹进行排序"""
        def extract_date_from_path(folder_path):
            """从文件夹路径中提取日期信息用于排序"""
            relative_path = os.path.relpath(folder_path, dest_dir)

            if relative_path == self.no_date_files_folder:
                return (9999, 13, 32)  
            if relative_path == self.other_files_folder:
                return (9999, 13, 31)  

            parts = relative_path.split(os.sep)
            year, month, day = 0, 0, 0
            
            for part in parts:
                if re.match(r'^\d{4}$', part):
                    year = int(part)
                elif re.match(r'^\d{1,2}$', part) and year > 0 and month == 0:
                    month = int(part)
                elif re.match(r'^\d{1,2}$', part) and year > 0 and month > 0 and day == 0:
                    day = int(part)
                elif '[' in part and ']' in part:
                    match = re.search(r'\[(\d+)-\d+\]', part)
                    if match:
                        index = int(match.group(1))
                        month = month * 100 + index
            
            return (year, month, day)

        return sorted(folder_stats.items(), key=lambda x: extract_date_from_path(x[0]))

    def resort_destination(self, dest_dir, progress_callback=None):
        """对目标目录进行重新整理 (70% - 100%)"""

        resort_callback = lambda val=None, msg=None, check_terminate=False: self._progress_callback_wrapper(
            value=val, message=msg, check_terminate=check_terminate,
            progress_offset=70, progress_scale=30, core_callback=progress_callback
        )

        if progress_callback:
            resort_callback(5, "[Progress] 正在重新扫描目标目录并进行哈希校验...")

        resort_result = self.organize_media(dest_dir, dest_dir, backup=False, progress_callback=resort_callback,
                                            is_resort=True)

        if self.is_terminated:
            return "TERMINATED"

        if progress_callback:
            resort_callback(100, "[Success] --- 重新整理完成 ---")

        resort_result['identical_files_removed'] = 0
        return resort_result

    def _group_files_by_date(self, file_paths, progress_callback=None):
        """按日期分组文件 - 修复版本，确保所有键都存在，并添加进度反馈"""
        dated_files = {}

        for i, file_path in enumerate(file_paths):
            abs_file_path = os.path.abspath(file_path)

            try:
                date = MetadataExtractor.get_file_date(abs_file_path, self.date_priority_list)
            except Exception as e:
                if progress_callback:
                    self._progress_callback_wrapper(message=f"[Warning] 提取文件日期失败 {Path(abs_file_path).name}: {str(e)}", core_callback=progress_callback)
                try:
                    date = datetime.fromtimestamp(os.path.getmtime(abs_file_path))
                except:
                    date = datetime.now()
            
            file_ext = Path(abs_file_path).suffix.lower()

            if date.year <= 1970:
                date_key = "N"  
            else:
                if self.organization_mode == "daily":
                    date_key = date.strftime("%Y-%m-%d")
                elif self.organization_mode == "monthly":
                    date_key = date.strftime("%Y-%m")
                else:  
                    date_key = date.strftime("%Y")

            if date_key not in dated_files:
                dated_files[date_key] = {'images': [], 'videos': [], 'documents': [], 'other': []}

            if file_ext in self.image_formats:
                dated_files[date_key]['images'].append((abs_file_path, date))
            elif file_ext in self.video_formats:
                dated_files[date_key]['videos'].append((abs_file_path, date))
            elif file_ext in self.document_formats:
                dated_files[date_key]['documents'].append((abs_file_path, date))
            else:
                dated_files[date_key]['other'].append((abs_file_path, date))

            if progress_callback and i % 10 == 0:  
                progress = int((i + 1) / len(file_paths) * 100)
                progress_callback(progress, "")

        for date_key in dated_files:
            for file_type in ['images', 'videos', 'documents', 'other']:
                if file_type in dated_files[date_key]:
                    dated_files[date_key][file_type].sort(key=lambda x: x[1])

        return dated_files

    def _create_folder_structure(self, dated_files, dest_dir):
        """创建文件夹结构 - 修复版本，支持多级文件夹"""
        folder_structure = {}

        date_key_counts = defaultdict(int)
        for date_key, files in dated_files.items():
            date_key_counts[date_key] = sum(len(files[file_type]) for file_type in files)

        unknown_folder = os.path.join(dest_dir, self.no_date_files_folder)
        os.makedirs(unknown_folder, exist_ok=True)
        folder_structure["未知日期"] = [unknown_folder]

        other_folder = os.path.join(dest_dir, self.other_files_folder)
        os.makedirs(other_folder, exist_ok=True)

        for date_key, file_count in date_key_counts.items():
            if date_key == "N" or file_count == 0:
                continue

            if self.folder_naming_mode == "default":
                if self.organization_mode == "daily":
                    parts = date_key.split('-')
                    year, month, day = parts[0], parts[1], parts[2]
                    base_folder = os.path.join(dest_dir, year, month, day)
                elif self.organization_mode == "monthly":
                    parts = date_key.split('-')
                    year, month = parts[0], parts[1]
                    base_folder = os.path.join(dest_dir, year, month)
                else:  
                    year = date_key
                    base_folder = os.path.join(dest_dir, year)

                folder_count = (file_count + self.max_files_per_folder - 1) // self.max_files_per_folder
                folder_count = max(1, folder_count)

                date_folders = []
                for i in range(folder_count):
                    if folder_count == 1:
                        folder_path = base_folder
                    else:
                        folder_name = f"[{i + 1}-{folder_count}]"
                        folder_path = os.path.join(base_folder, folder_name)
                    
                    os.makedirs(folder_path, exist_ok=True)
                    date_folders.append(folder_path)

                folder_structure[date_key] = date_folders
            else:
                folder_count = (file_count + self.max_files_per_folder - 1) // self.max_files_per_folder
                folder_count = max(1, folder_count)

                date_folders = []
                for i in range(folder_count):
                    try:
                        folder_name = self.folder_naming_pattern.format(
                            index=i + 1,
                            total=folder_count
                        )
                    except KeyError:
                        folder_name = f"文件夹{i+1}"
                        if hasattr(self, '_progress_callback_wrapper'):
                            self._progress_callback_wrapper(message=f"[Warning] 自定义文件夹命名模式失败，回退到默认: {folder_name}")

                    folder_path = os.path.join(dest_dir, folder_name)
                    os.makedirs(folder_path, exist_ok=True)
                    date_folders.append(folder_path)

                folder_structure[date_key] = date_folders

        return folder_structure

    def _cleanup_and_renumber_folders(self, directory, progress_callback=None):
        """清理空目录并重新编号文件夹"""
        if progress_callback:
            self._progress_callback_wrapper(message="[Progress] 正在清理空目录并重新编号文件夹...", core_callback=progress_callback)

        try:
            for root, dirs, files in os.walk(directory, topdown=False):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(dir_path):
                            os.rmdir(dir_path)
                            if progress_callback:
                                self._progress_callback_wrapper(message=f"[Info] 删除空目录: {dir_path}", core_callback=progress_callback)
                    except OSError:
                        pass

            self._renumber_folders(directory, progress_callback)

        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Warning] 清理和重新编号文件夹失败: {str(e)}", core_callback=progress_callback)

    def _renumber_folders(self, directory, progress_callback=None):
        """重新编号文件夹，确保序号正确反映实际文件夹数量"""
        try:
            year_folders = {}

            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path):
                    match = re.match(r'^(\d{4})\[(\d+)-(\d+)\]$', item)
                    if match:
                        year = match.group(1)
                        current_index = int(match.group(2))
                        total_count = int(match.group(3))

                        if year not in year_folders:
                            year_folders[year] = []

                        year_folders[year].append({
                            'path': item_path,
                            'name': item,
                            'current_index': current_index,
                            'total_count': total_count
                        })
                    elif re.match(r'^\d{4}$', item):
                        year = item
                        year_folders[year] = year_folders.get(year, []) + [{
                            'path': os.path.join(directory, item),
                            'name': item,
                            'current_index': 1,
                            'total_count': 1
                        }]

            for year, folders in year_folders.items():
                non_empty_folders = []
                for folder in folders:
                    try:
                        if os.listdir(folder['path']):
                            non_empty_folders.append(folder)
                    except OSError:
                        continue

                non_empty_folders.sort(key=lambda x: x['current_index'])

                new_total = len(non_empty_folders)
                for new_index, folder in enumerate(non_empty_folders, 1):
                    old_path = folder['path']

                    if new_total == 1:
                        new_name = year
                    else:
                        new_name = f"{year}[{new_index}-{new_total}]"

                    new_path = os.path.join(directory, new_name)

                    if old_path != new_path:
                        os.rename(old_path, new_path)
                        if progress_callback:
                            self._progress_callback_wrapper(message=f"[Info] 重命名文件夹: {os.path.basename(old_path)} -> {new_name}", core_callback=progress_callback)

        except Exception as e:
            if progress_callback:
                self._progress_callback_wrapper(message=f"[Warning] 重新编号文件夹失败: {str(e)}", core_callback=progress_callback)

    def rollback_operations(self, dest_dir):
        """回退所有操作"""
        self.log(f"[Core] 开始回退操作，共 {len(self.rollback_log)} 条记录")

        for operation, original_path, new_path in reversed(self.rollback_log):
            if operation == 'move':
                try:
                    if os.path.exists(new_path):
                        os.makedirs(os.path.dirname(original_path), exist_ok=True)
                        FileOperations.safe_move(new_path, original_path)
                except Exception as e:
                    self.log(f"[Core] 回退失败 {new_path} -> {original_path}: {str(e)}")

        self._cleanup_and_renumber_folders(dest_dir)

        self.rollback_log.clear()
        self.log("[Core] 回退操作完成")