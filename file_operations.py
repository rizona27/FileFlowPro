# file_operations.py
import os
import shutil
import zipfile
import hashlib
from datetime import datetime
from pathlib import Path
import re
import threading
from collections import defaultdict
import time


class FileOperations:
    """文件操作工具类"""

    _metadata_cache = {}
    _cache_lock = threading.Lock()

    _scan_threads = []
    _scan_results = defaultdict(list)
    _scan_progress = {'total': 0, 'scanned': 0}
    
    @staticmethod
    def extract_date_from_filename(filename):
        """尝试从文件名模式中提取日期 - 增强精度版本"""

        patterns = [
            r'(IMG_|VID_|PANO_|MVIMG_)(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',
            
            r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})',

            r'(Screenshot_|Photo_|Video_|Recording_)(\d{4})(\d{2})(\d{2})',

            r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})',

            r'(\d{4})[-_]?(\d{2})(?!\d)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    
                    if len(groups) >= 4 and groups[0] in ('IMG_', 'VID_', 'PANO_', 'MVIMG_', 'Screenshot_', 'Photo_', 'Video_', 'Recording_'):
                        year, month, day = groups[1], groups[2], groups[3]
                        return FileOperations._validate_and_create_date(year, month, day)

                    elif len(groups) >= 3:
                        year, month, day = groups[0], groups[1], groups[2]
                        return FileOperations._validate_and_create_date(year, month, day)

                    elif len(groups) == 2:
                        year, month = groups[0], groups[1]
                        return FileOperations._validate_and_create_date(year, month, "01")
                        
                except (ValueError, TypeError) as e:
                    continue
                    
        return None
    
    @staticmethod
    def _validate_and_create_date(year_str, month_str, day_str="01"):
        """验证并创建日期对象"""
        try:
            if len(year_str) == 2:
                year_int = int(year_str)
                year_str = '20' + year_str if year_int < 50 else '19' + year_str
            
            year = int(year_str)
            month = int(month_str)
            day = int(day_str)

            if (1900 <= year <= 2100 and 
                1 <= month <= 12 and 
                1 <= day <= 31):
                return datetime(year, month, day)
                
        except (ValueError, TypeError):
            pass
            
        return None

    @staticmethod
    def get_file_modification_time(file_path):
        """获取文件修改时间，有回退机制"""
        try:
            stat = os.stat(file_path)
            mod_time = stat.st_mtime
            return datetime.fromtimestamp(mod_time)
        except (OSError, IOError) as e:
            print(f"获取文件修改时间失败 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
        except Exception as e:
            print(f"未知错误获取文件修改时间 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
    
    @staticmethod
    def get_file_creation_time(file_path):
        """获取文件创建时间"""
        try:
            stat = os.stat(file_path)
            create_time = stat.st_ctime
            return datetime.fromtimestamp(create_time)
        except (OSError, IOError) as e:
            print(f"获取文件创建时间失败 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
        except Exception as e:
            print(f"未知错误获取文件创建时间 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
    
    @staticmethod
    def get_file_system_metadata_time(file_path):
        """获取文件系统元数据时间（最后访问时间等）"""
        try:
            stat = os.stat(file_path)
            access_time = stat.st_atime
            return datetime.fromtimestamp(access_time)
        except (OSError, IOError) as e:
            print(f"获取文件系统元数据时间失败 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
        except Exception as e:
            print(f"未知错误获取文件系统元数据时间 {file_path}: {str(e)}")
            return datetime(1900, 1, 1)
    
    @staticmethod
    def create_zip_backup(source_dir, dest_dir, progress_callback=None):
        """创建原始文件的ZIP备份到目标目录，支持进度回调和终止检查"""
        if not os.path.exists(source_dir):
            return False

        timestamp = datetime.now().strftime("%y%m%d")
        backup_filename = f"{timestamp}-BACKUP.zip"
        backup_path = os.path.join(dest_dir, backup_filename)

        os.makedirs(dest_dir, exist_ok=True)

        all_files = []
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not "BACKUP" in d.upper() and not d.startswith('.')]
            for file in files:
                if not file.startswith('.') and not file.endswith('.zip'):
                    all_files.append(os.path.join(root, file))
        
        total_files = len(all_files)
        files_backed_up = 0
        
        if total_files == 0:
            return None 
            
        if progress_callback:
            progress_callback(0, f"[Progress] 发现 {total_files} 个文件，正在进行压缩...")
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in all_files:
                    if progress_callback and progress_callback(check_terminate=True):
                         zipf.close() 
                         os.remove(backup_path) 
                         return "TERMINATED"

                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname)
                    
                    files_backed_up += 1

                    update_frequency = max(1, total_files // 50)
                    if progress_callback and (files_backed_up % update_frequency == 0 or files_backed_up == total_files):
                        progress_percent = int(files_backed_up / total_files * 100)
                        progress_callback(progress_percent, f"[Progress] 正在压缩文件 ({files_backed_up}/{total_files})")
                
                if progress_callback:
                     progress_callback(100, "[Progress] 压缩完成")

            return backup_path
        except (zipfile.BadZipFile, OSError, IOError) as e:
            print(f"创建备份失败: {str(e)}")
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except OSError:
                    pass
            raise e
        except Exception as e:
            print(f"未知错误创建备份: {str(e)}")
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except OSError:
                    pass
            raise e
    
    @staticmethod
    def safe_move(src, dst):
        """安全移动文件，如果需要则创建目录，并删除源目录中的空父目录"""
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            
            FileOperations.remove_empty_dir(os.path.dirname(src))
        except (OSError, IOError, shutil.Error) as e:
            print(f"移动文件失败 {src} -> {dst}: {str(e)}")
            raise e
        except Exception as e:
            print(f"未知错误移动文件 {src} -> {dst}: {str(e)}")
            raise e

    @staticmethod
    def remove_empty_dir(directory):
        """递归删除所有空的父目录"""
        while directory and directory != os.path.dirname(directory):
            try:
                os.rmdir(directory)
                directory = os.path.dirname(directory)
            except OSError:
                break
    
    @staticmethod
    def get_sequence_format(total_files):
        """根据总文件数确定序列号格式"""
        if total_files >= 10000:
            return "{:05d}"
        elif total_files >= 1000:
            return "{:04d}"
        elif total_files >= 100:
            return "{:03d}"
        else:
            return "{:02d}"
    
    @staticmethod
    def get_unique_filename(directory, base_name, extension):
        """获取唯一的文件名，避免覆盖"""
        original_path = os.path.join(directory, base_name + extension)
        if not os.path.exists(original_path):
            return original_path

        counter = 1
        while True:
            new_filename = f"{base_name}_{counter}{extension}"
            new_path = os.path.join(directory, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1
    
    @staticmethod
    def calculate_md5(file_path, block_size=65536):
        """计算文件的MD5哈希值 - 优化大文件处理"""
        hash_md5 = hashlib.md5()
        try:
            file_size = os.path.getsize(file_path)

            if file_size > 10 * 1024 * 1024: 
                return FileOperations._calculate_sampling_hash(file_path)

            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(block_size), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError) as e:
            print(f"计算MD5失败 {file_path}: {str(e)}")
            return None
        except Exception as e:
            print(f"未知错误计算MD5 {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_sampling_hash(file_path, sample_size=3):
        """对大文件使用抽样哈希算法"""
        file_size = os.path.getsize(file_path)
        hash_md5 = hashlib.md5()
        
        try:
            with open(file_path, "rb") as f:
                sample_positions = [
                    0,  
                    file_size // 2,  
                    file_size - 8192  
                ]
                
                for pos in sample_positions:
                    if pos < 0:
                        pos = 0
                    if pos >= file_size:
                        continue
                        
                    f.seek(pos)
                    sample = f.read(4096)  
                    if sample:
                        hash_md5.update(sample)

                hash_md5.update(str(file_size).encode())
                
            return hash_md5.hexdigest()
        except Exception as e:
            print(f"抽样哈希计算失败 {file_path}: {str(e)}")
            return None
    
    @staticmethod
    def are_files_identical(file1, file2):
        """检查两个文件是否完全相同（通过优化哈希）"""

        try:
            size1 = os.path.getsize(file1)
            size2 = os.path.getsize(file2)
            if size1 != size2:
                return False

            if size1 > 10 * 1024 * 1024:
                hash1 = FileOperations._calculate_sampling_hash(file1)
                hash2 = FileOperations._calculate_sampling_hash(file2)
            else:
                hash1 = FileOperations.calculate_md5(file1)
                hash2 = FileOperations.calculate_md5(file2)
            
            if hash1 and hash2 and hash1 == hash2:
                return True
            return False
        except (OSError, IOError) as e:
            print(f"检查文件相同性失败 {file1}, {file2}: {str(e)}")
            return False
        except Exception as e:
            print(f"未知错误检查文件相同性 {file1}, {file2}: {str(e)}")
            return False
    
    @staticmethod
    def scan_directory_threaded(directory, file_formats, progress_callback=None):
        """多线程扫描目录 - 修复文件计数问题"""
        FileOperations._scan_results.clear()
        FileOperations._scan_progress = {'total': 0, 'scanned': 0}
        FileOperations._scan_threads = []

        total_files = 0
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.startswith('.'):
                    continue
                file_ext = Path(file).suffix.lower()
                found = False
                for formats in file_formats.values():
                    if file_ext in formats:
                        found = True
                        break
                if not found:
                    found = True
                if found:
                    total_files += 1
        
        FileOperations._scan_progress['total'] = total_files

        thread_count = min(4, os.cpu_count() or 1) 
        chunks = FileOperations._split_directory_scan(directory, thread_count)
        
        for i, chunk_dirs in enumerate(chunks):
            thread = threading.Thread(
                target=FileOperations._scan_worker,
                args=(chunk_dirs, file_formats, i)
            )
            FileOperations._scan_threads.append(thread)
            thread.daemon = True
            thread.start()

        for thread in FileOperations._scan_threads:
            thread.join()

        final_results = {}
        for file_type in file_formats.keys():
            final_results[file_type] = list(set(FileOperations._scan_results[file_type]))
        
        return final_results
    
    @staticmethod
    def _split_directory_scan(directory, num_chunks):
        """将目录扫描任务分割成多个块"""
        all_dirs = [directory]

        for root, dirs, _ in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for d in dirs:
                all_dirs.append(os.path.join(root, d))

        chunk_size = max(1, len(all_dirs) // num_chunks)
        chunks = [all_dirs[i:i + chunk_size] for i in range(0, len(all_dirs), chunk_size)]
        
        return chunks[:num_chunks]  
    
    @staticmethod
    def _scan_worker(directories, file_formats, thread_id):
        """扫描工作线程 - 修复文件分类逻辑"""
        for directory in directories:
            try:
                for root, dirs, files in os.walk(directory):
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        if file.startswith('.'):
                            continue
                            
                        file_path = os.path.join(root, file)
                        file_ext = Path(file).suffix.lower()
                        
                        with FileOperations._cache_lock:
                            FileOperations._scan_progress['scanned'] += 1
                        
                        found = False
                        for file_type, formats in file_formats.items():
                            if file_ext in formats:
                                with FileOperations._cache_lock:
                                    FileOperations._scan_results[file_type].append(file_path)
                                found = True
                                break

                        if not found:
                            with FileOperations._cache_lock:
                                FileOperations._scan_results['other'].append(file_path)
            except Exception as e:
                print(f"扫描线程 {thread_id} 错误: {str(e)}")