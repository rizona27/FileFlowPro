# metadata_extractor.py
import os
from datetime import datetime
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS
import subprocess
import json
from file_operations import FileOperations
import re
from dateutil import parser  


class MetadataExtractor:

    _metadata_cache = {}
    @staticmethod
    def get_image_metadata(file_path):
        """从图片文件中提取元数据 - 增强格式兼容性"""
        cache_key = f"image_{file_path}"
        if cache_key in MetadataExtractor._metadata_cache:
            return MetadataExtractor._metadata_cache[cache_key]

        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    exif = {
                        TAGS.get(tag, tag): value
                        for tag, value in exif_data.items()
                    }

                    date_str = (exif.get('DateTimeOriginal') or 
                               exif.get('DateTime') or 
                               exif.get('DateCreated') or
                               exif.get('CreateDate'))
                    
                    if date_str:
                        date_str = date_str.split('.')[0].strip()

                        date_formats = [
                            '%Y:%m:%d %H:%M:%S',    
                            '%Y-%m-%d %H:%M:%S',    
                            '%Y/%m/%d %H:%M:%S',    
                            '%Y%m%d %H%M%S',        
                            '%Y:%m:%d',           
                            '%Y-%m-%d',          
                            '%Y/%m/%d',          
                            '%Y%m%d',              
                        ]
                        
                        for date_format in date_formats:
                            try:
                                result = datetime.strptime(date_str, date_format)

                                MetadataExtractor._metadata_cache[cache_key] = result
                                return result
                            except ValueError:
                                continue

                        try:
                            result = parser.parse(date_str)
                            MetadataExtractor._metadata_cache[cache_key] = result
                            return result
                        except (ValueError, TypeError):
                            pass

        except (IOError, OSError, Image.UnidentifiedImageError) as e:
            print(f"提取图片元数据失败 {file_path}: {str(e)}")
        except Exception as e:
            print(f"未知错误提取图片元数据 {file_path}: {str(e)}")

        MetadataExtractor._metadata_cache[cache_key] = None
        return None

    @staticmethod
    def get_video_metadata(file_path):
        """使用ffprobe从视频文件中提取元数据 - 增强时区处理"""
        cache_key = f"video_{file_path}"
        if cache_key in MetadataExtractor._metadata_cache:
            return MetadataExtractor._metadata_cache[cache_key]

        try:
            cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', file_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            if result.returncode == 0:
                metadata = json.loads(result.stdout)

                format_info = metadata.get('format', {})
                tags = format_info.get('tags', {})

                date_str = (tags.get('creation_time') or 
                           tags.get('date') or 
                           tags.get('time') or
                           tags.get('DATE') or
                           tags.get('creation_time'))

                if date_str:
                    if 'Z' in date_str or '+' in date_str:
                        try:
                            result = parser.parse(date_str)
                            result = result.astimezone().replace(tzinfo=None)
                            MetadataExtractor._metadata_cache[cache_key] = result
                            return result
                        except (ValueError, TypeError):
                            date_str = re.sub(r'[Zz].*$', '', date_str)  
                            date_str = re.sub(r'\+[0-9]{2}:[0-9]{2}$', '', date_str)  

                    date_str = date_str.split('.')[0].replace('T', ' ').strip()
                    
                    date_formats = [
                        '%Y-%m-%d %H:%M:%S',    
                        '%Y%m%d %H%M%S',        
                        '%Y-%m-%d',             
                        '%Y/%m/%d %H:%M:%S',    
                        '%Y:%m:%d %H:%M:%S',   
                    ]
                    
                    for date_format in date_formats:
                        try:
                            result = datetime.strptime(date_str, date_format)
                            MetadataExtractor._metadata_cache[cache_key] = result
                            return result
                        except ValueError:
                            continue

                    try:
                        result = parser.parse(date_str)
                        MetadataExtractor._metadata_cache[cache_key] = result
                        return result
                    except (ValueError, TypeError):
                        pass

        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError) as e:
            print(f"提取视频元数据失败 {file_path}: {str(e)}")
        except Exception as e:
            print(f"未知错误提取视频元数据 {file_path}: {str(e)}")

        MetadataExtractor._metadata_cache[cache_key] = None
        return None

    @staticmethod
    def clear_cache():
        """清空元数据缓存"""
        MetadataExtractor._metadata_cache.clear()

    @staticmethod
    def get_file_date(file_path, date_priority_list):
        """使用多种方法从文件获取日期，支持优先级列表 - 增强兼容性"""
        cache_key = f"date_{file_path}_{'_'.join(date_priority_list)}"
        if cache_key in MetadataExtractor._metadata_cache:
            return MetadataExtractor._metadata_cache[cache_key]

        date_sources = {}

        if file_path.lower().endswith(
                ('.jpg', '.jpeg', '.tiff', '.tif', '.png', '.heic', '.dng', '.raw', '.cr2', '.nef', '.arw')):
            date_sources["exif"] = MetadataExtractor.get_image_metadata(file_path)

        elif file_path.lower().endswith(
                ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.m4v', '.mpeg', '.mpg', '.3gp', '.webm')):
            date_sources["metadata"] = MetadataExtractor.get_video_metadata(file_path)

        filename = os.path.basename(file_path)
        date_sources["filename"] = FileOperations.extract_date_from_filename(filename)

        date_sources["filetime"] = FileOperations.get_file_modification_time(file_path)

        date_sources["creationtime"] = FileOperations.get_file_creation_time(file_path)

        date_sources["filesystem"] = FileOperations.get_file_system_metadata_time(file_path)

        result_date = None
        for source in date_priority_list:
            if source in date_sources and date_sources[source] and date_sources[source].year > 1970:
                result_date = date_sources[source]
                break

        if not result_date:
            result_date = date_sources["filetime"]

        MetadataExtractor._metadata_cache[cache_key] = result_date
        return result_date