import os
from logger import *
#from qb_tool import *
import traceback
import requests
import re
import sys
import json
import subprocess
import time
file_list = {}
class MyCustomError(Exception):
    def __init__(self, code, message,logger):
        self.code = code
        self.message = message
        super().__init__(self.message)


def send_logger(logger,filename,title,initial_comment=None,content=None):
    filename = filename + '.md'
    if content:
        slack_log_file = {"content": content, "filename": filename, "title": title,}
    else:
        logger_file=get_logger_path(logger)
        with open(logger_file,'r',encoding='utf-8') as file:
            content=file.read()
            slack_log_file= {"content": content,"filename":filename,"title": title,}
    send_files(files=[slack_log_file],channel_name='下载器交互',initial_comment=initial_comment)

def print_function_name(func):
    def wrapper(*args, **kwargs):
        logger = kwargs.get('logger', None)
        if logger:
            original_formats = [handler.formatter for handler in logger.handlers]
            set_logger_format(logger=logger, func_name=func.__name__)
            try:
                logger.debug(f"调用函数 {func.__name__}，参数: args={args}, kwargs={kwargs}")
                return func(*args, **kwargs)
            except MyCustomError as e:

                logger.error("捕获到自定义错误：")
                tb = traceback.format_exc()
                logger.warning(f'错误是{e}\n{tb}')
                logger.error(f"错误码：{e.code}")
                logger.error(f"错误消息：{e.message}")
                send_logger(logger=logger,filename=logger.name,title=logger.name,initial_comment=f'错误码：{e.code}\n 错误消息：{e.message}')
            except Exception as e:
                tb = traceback.format_exc()
                error_message = str(e)  # 获取错误信息
                logger.warning(f'错误是{e}\n{tb}')
                send_logger(logger=logger, filename=logger.name, title=logger.name, initial_comment=f'错误消息：{error_message}')
                exit(200)
            finally:
                if logger:
                    for handler, original_format in zip(logger.handlers, original_formats):
                        handler.setFormatter(original_format)
        else:
            return func(*args, **kwargs)

    return wrapper

def extract_season_number(season_string):
    # Use regular expression to extract digits from the string
    season_number = re.search(r'\d+', season_string)

    if season_number:
        # Convert the extracted digits to an integer
        return int(season_number.group())
    else:
        # If no digits found, return a default value or raise an exception, as per your requirement
        return None

def special_make(name):
    have_extension = False
    media_extension = [".mp4",".mkv",".avi"]
    for media_flag in media_extension:
        if media_flag in name:
            have_extension = True
            break
    if have_extension:
        name = re.sub(pattern=r"[-|_][a-z]{0,2}[0-9]{0,2}\.",repl=".",string=name)
    else:
        name = re.sub(pattern=r"[-|_][a-z]{0,2}[0-9]{0,2}$", repl=".", string=name)

    return name
    
def delete_special_chart(name):
    name = special_make(name)
    """
    flag = "-"
    part_stats={}
    parts = name.split(flag)  # 分隔符号

    # 统计每个部分出现的次数，并计算其占比
    for part in parts:
        part_len = len(part)
        part_ratio = part_len / len(name)
        part_stats[part] = {'length': part_len, 'ratio': part_ratio}

    # 找到占比最大的部分
    max_ratio_part = max(part_stats, key=lambda p: part_stats[p]['ratio'])
    """
    max_ratio_part = name
    return max_ratio_part

def custom_sort(strings):
    common_prefix = os.path.commonprefix(strings) # 公共前缀
    common_suffix = os.path.commonprefix([string[::-1] for string in strings])[::-1] # 公共后缀

    # 去除公共前缀和公共后缀并排序
    sorted_strings = [string[len(common_prefix):-len(common_suffix)] for string in strings]
    # 根据长度再分类
    len_group={}
    for element in sorted_strings:
        length = len(element)
        if length in len_group:
            len_group[length].append(element)
        else:
            len_group[length]=[element]
    all_things = []
    for length in len_group:
        temp_things=len_group[length]
        temp_things.sort()
        all_things.extend(temp_things)

    # 如果排序后的列表为空，则赋予零
    if not all_things:
        all_things.append('0')

    # 反向映射到原来的元素
    sorted_strings = [common_prefix + string + common_suffix if string == '0' else common_prefix + string + common_suffix for string in all_things]

    return sorted_strings

def is_episode_within_range(episode, episode_list): # 判断剧集是否包含在内
    episode_season, episode_number = re.findall(r'[A-Z]+(\d+)E(\d+)', episode)[0]
    for range_string in episode_list:
        start, end = range_string.split('-')
        start_season, start_episode = re.findall(r'[A-Z]+(\d+)E(\d+)', start)[0]
        if episode_season != start_season:
            continue
        else:
            end_season, end_episode = re.findall(r'[A-Z]+(\d+)E(\d+)', end)[0]
            if int(start_episode) <= int(episode_number) <= int(end_episode):
                return True
            return False

def convert_episodes(episode_list): # 剧集列表转换成剧集范围 返回S01E01-S01E02，等的数组
    episodes = {}
    start = 0
    end = 0
    result = []
    if len(episode_list) > 1:
        # 整理所有的剧集，将季号和集号提取出来
        for episode in episode_list:
            
            season, ep = episode.split('E')
            season = int(season.replace('S',''))
            ep = int(ep)
            if season in episodes:
                episodes[season].append(ep)
            else:
                episodes[season] = [ep]
        for season in episodes:
            raw_episodes = episodes[season]
            while True:
                temp_episode=sorted(raw_episodes)
                start = temp_episode[0]
                temp_end = 0
                i = 1
                for episode in temp_episode:
                    if episode == start + i and episode != start:
                        i += 1
                        raw_episodes.pop(raw_episodes.index(episode))
                        temp_end = episode
                    elif episode == start:
                        continue
                    else:
                        result.append(f'S{season}{start}-S{season}{temp_end}')
                        break
                else:
                    result.append(f'S{season}E{start}-S{season}E{temp_end}')
                break
    else:
        result.append(episode_list)
    return result
    
            
            
        
    



def parse_episode_range(episode_range): # 剧集范围 转换成 剧集列表
    # 使用正则表达式从字符串中提取起始和结束的剧集号
    match = re.match(r'S(\d+)E(\d+)-S(\d+)E(\d+)', episode_range)

    if match:
        start_season = int(match.group(1))
        start_episode = int(match.group(2))
        end_season = int(match.group(3))
        end_episode = int(match.group(4))

        # 生成剧集号的列表
        episode_list = []
        for season in range(start_season, end_season + 1):
            if season == start_season:
                start = start_episode
            else:
                start = 1
            if season == end_season:
                end = end_episode
            else:
                end = 22  # 假设每个季度都有22集，您可以根据实际情况进行调整
            episode_list.extend(range(start, end + 1))

        return episode_list
    else:
        # 如果输入是单集（如"S01E12"），直接返回剧集号的列表
        match_single = re.match(r'S(\d+)E(\d+)', episode_range)
        if match_single:
            episode_number = int(match_single.group(2))
            return [episode_number]
        else:
            return []  # 返回空列表表示没有匹配到正确的剧集范围
def is_media_file(filename,min_file_size_mb=0,path=''):   #判断文件是否满足大小要求和后缀名要求
    media_extensions = ['.mp3', '.mp4', '.avi', '.mov', '.mkv', '.wav', '.flac','.ts','.iso','.wmv','.bdmv']
    file_extension = filename[filename.rfind('.'):].lower()

    # 获取文件大小（以字节为单位）
    if os.path.exists(path):
        if path:
            file_size = os.path.getsize(path)  # 文件大小以字节为单位
        else:
            file_size = 1 * 1024 * 1024
    else:
        file_size = 0

    # 将输入的兆字节转换为字节
    min_file_size = min_file_size_mb * 1024 * 1024  # 兆字节转换为字节

    # 判断文件是否是媒体文件，并且文件大小是否满足要求
    return file_extension in media_extensions and file_size >= min_file_size

def is_dvd_file(filename):
    media_extensions = ['.m2ts','.bdmv']
    file_extension = filename[filename.rfind('.'):].lower()
    return file_extension in media_extensions

def get_ext(file_name):  ##输入:文件名 输出:没有后缀的文件名和文件格式
    file_name_without_ext, file_ext = os.path.splitext(file_name)
    last_dot_index = file_name.rfind(".")
    if last_dot_index >= 0:
        file_name_without_ext = file_name_without_ext[:last_dot_index]
        file_ext = file_name_without_ext[last_dot_index:] + file_ext
    #print(file_name_without_ext)  # 输出 1.1.1.1
    #print(file_ext)  # 输出 .mp4
    return file_name_without_ext,file_ext


def get_file_inode(file_path):
    import os

    try:
        # 使用 os.stat 获取文件的统计信息
        file_stat = os.stat(file_path)

        # 获取文件的inode值
        inode = file_stat.st_ino
        print(f"The inode value of the file {file_path} is {inode}")
        return inode
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return 0
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return 0

def get_file_size(file_path):
    import os
    try:
        # 使用 os.path.getsize() 获取文件大小（以字节为单位）
        file_size = os.path.getsize(file_path)
        print(f"The size of the file {file_path} is {file_size} bytes.")
        return file_size
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return 0
    except Exception as e:
        print(f"An error occurred: {str(e)}")





@print_function_name
def create_single_links(src_path, dest_path, logger, link_type='hard',overwrite=True):
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and not overwrite:
        logger.info('文件已经存在,不进行覆写跳过')
        return
    elif os.path.exists(dest_path) and overwrite:
        os.remove(dest_path)
        logger.info('文件已经存在,进行覆写,首先进行删除')
    else:
        pass
    try:
        if link_type == 'hard':
            os.link(src_path, dest_path)
            logger.info(f"源路径：{src_path}，创建硬链接：{dest_path}")
        elif link_type == 'soft':
            os.symlink(src_path, dest_path)
            logger.info(f"源路径：{src_path}，创建软链接：{dest_path}")
        elif link_type == 'move':
            os.rename(src_path, dest_path)
            logger.info(f"移动文件：{src_path} -> {dest_path}")
        else:
            logger.error("无效的链接类型")
            return
    except OSError as e:
        if e.args[1] == 'File exists':
            logger.info('文件已经存在')
        else:
            logger.error(f"创建链接或移动文件失败：{src_path} -> {dest_path}，错误信息：{str(e)}")
            raise MyCustomError(code='2', message=f'{str(e)}', logger=logger)


def change_folder(source_folder, destination_folder,del_folder=""):
    global file_list
    # dest_root 最上层的目录
    for root, dirs, files in os.walk(source_folder):
        # 创建对应的目标文件夹路径
        dest_root = os.path.join(destination_folder, os.path.basename(source_folder))
        if del_folder:
            dest_root = os.path.dirname(dest_root)
        os.makedirs(dest_root, exist_ok=True)


        for file in files:
            src_path = os.path.join(root, file)
            dest_path = os.path.join(dest_root, file)
            file_list[src_path]=dest_path
        if not dirs:
            #print('当前没有子目录')
            pass
        else:
            for dir in dirs:
                source_folder2=os.path.join(source_folder,dir)
                change_folder(source_folder2, dest_root)
        return file_list
    
def create_folder_hard_links(source_folder, destination_folder, logger,link_type='hard',overwrite=True,save_top=True):  #文件夹层次的硬链接
    # 获取源文件夹中的所有文件和子文件夹
    global file_list
    if not save_top:
        file_list={}
        file_list = change_folder(source_folder=source_folder, destination_folder=destination_folder,
                                  del_folder=f'{os.path.basename(source_folder)}')
    else:
        file_list={}
        file_list = change_folder(source_folder=source_folder, destination_folder=destination_folder)
    pass
    for source_path in file_list:
        logger.info(f"raw{source_path},end{file_list[source_path]}")
        create_single_links(src_path=source_path, dest_path=file_list[source_path], logger=logger, link_type=link_type,overwrite=overwrite)
    logger.info('全部创建硬链接成功')
    return file_list



def check_files_exist(files, logger):  # 传递的是一个列表，键名是文件名，键值是路径
    error_files = []
    if len(files) == 0:
        return 0
    for file in files:
        if 'log' in file:
            continue
        if os.path.exists(files[file]):
            continue
        else:
            error_files.append(files[file])
    if len(error_files) == 0:
        return 1
    elif len(error_files) == len(files):
        logger.error(f'全部不存在')
        return 0
    else:    
        for file in error_files:
            logger.error(f'{file}不存在')
        
        return len(error_files) / len(files)


def check_path_type(path):
    if os.path.isfile(path):
        print(f"The path '{path}' is a file.")
    elif os.path.isdir(path):
        print(f"The path '{path}' is a directory.")
    else:
        print(f"The path '{path}' does not exist.")

@print_function_name
def download_image(url, save_path,logger=None):
    folder_path=os.path.dirname(save_path)
    os.makedirs(folder_path,exist_ok=True)
    try:
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功
        with open(save_path, 'wb') as file:
            file.write(response.content)
        return True
        #logger.info("图片下载完成")
    except requests.exceptions.RequestException as e:
        logger.error(f"图片下载失败: {e}")
        return False
    except IOError as e:
        logger.error(f"保存图片失败: {e}")
        return False


def delete_str(root_string, delete_string):
    new_string = root_string.replace(delete_string, "")
    return new_string

@print_function_name
def delete_file(file_path,logger):
    while True:
        try:
            os.remove(file_path)
            logger.info(f"文件 {file_path} 已成功删除")
            # 验证删除成功
            if not os.path.exists(file_path):
                logger.info(f"文件 {file_path} 成功验证不存在")
                return True
            else:
                logger.info(f"文件 {file_path} 存在，删除可能未成功")
                time.sleep(2)
        except FileNotFoundError:
            logger.info(f"文件 {file_path} 未找到")
            return True
        except Exception as e:
            logger.info(f"删除文件时发生错误：{e}")

def find_common_elements(array1, array2):  ##寻找相同的元素
    set1 = set(array1)
    set2 = set(array2)
    common_elements = set1.intersection(set2)
    return list(common_elements)

@print_function_name
def get_media_name(media_dir,media_files,logger):  # 遍历目录下的所有路径
    for root, dirs, files in os.walk(media_dir):
        print('root_dir:', root)  # 当前目录路径
        print('sub_dirs:', dirs)  # 当前路径下所有子目录
        print('files:', files)  # 当前路径下所有非目录子文件
        if not files:
            print('没有文件')
        else:
            for filename in os.listdir(media_dir):
                filepath = os.path.join(root, filename)
                if filename.lower().endswith('.xltd'):
                    logger.info('存在没有完成的文件，提前结束任务')
                    sys.exit(0)
                if os.path.isfile(filepath) and filename.lower().endswith(('.mp4', '.avi', '.mkv','.wmv')):
                    basename = os.path.splitext(filename)[0]
                    media_files[filename] = filepath
        if not dirs:
            print('当前没有子目录')
            pass
        else:
            for dir in dirs:
                media_files=get_media_name(media_dir=os.path.join(root,dir),media_files=media_files,logger=logger)
    return media_files

def write_dict_to_json(data, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w",encoding='utf-8') as json_file:
        json.dump(data, json_file, ensure_ascii=False,indent=4)
    print(f"字典已写入 JSON 文件: {filename}")

def read_dict_from_json(filename):
    try:
        with open(filename, "r",encoding='utf-8') as json_file:
            loaded_data = json.load(json_file)
        if loaded_data:
            return loaded_data
        else:
            return {}
    except FileNotFoundError:
        write_dict_to_json(data={},filename=filename)
        return {}

def remove_dict_from_json(filename, key):
    with open(filename, "r") as json_file:
        data = json.load(json_file)
    if key in data:
        del data[key]
        print(f"键 '{key}' 已从字典中删除")
    else:
        print(f"键 '{key}' 不存在于字典中")
    write_dict_to_json(data=data,filename=filename)


def get_folder_path_or_parent_folder(input_path):
    # 使用os.path.isdir()来检查输入路径是否是一个文件夹
    if os.path.isdir(input_path):
        return input_path  # 如果是文件夹，直接返回路径

    # 使用os.path.isfile()来检查输入路径是否是一个文件
    elif os.path.isfile(input_path):
        # 使用os.path.dirname()来获取文件所在的文件夹路径
        folder_path = os.path.dirname(input_path)
        return folder_path

    else:
        return "Invalid path"  # 如果路径既不是文件夹也不是文件，则返回无效路径消息
@print_function_name
def check_file_exist_by_inode(file,logger):  # 通过检查file inode exist
    end_path=file['end_path']
    old_inode = file.get('file_inode',0)
    if not old_inode:
        old_inode = 0
    old_size = file.get('file_size',0)
    if not old_size:
        old_size = 0
    new_inode = get_file_inode(file_path=end_path)
    new_size = get_file_size(file_path=end_path)
    if new_inode == int(old_inode):
        logger.info('same file')
        return True
    else:
        return False

def get_video_resolution_ffmpeg(file_path):
    command = f"ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 '{file_path}' "
    try:
        result = subprocess.check_output(command, shell=True).decode('utf-8')
        width, height = map(int, re.findall(r'\d+', result))
        resolution = f"{width}x{height}"
        return resolution
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

def format_resolution(resolution):
    if 'x' not in resolution:
        return "Unknown"
    width, height = resolution.split('x')
    if width and height:
        if width == '1920' and height == '1080':
            return "1080P"
        elif width == '1280' and height == '720':
            return "720P"
        elif width == '3840' and height == '2160':
            return "2160P"
        # Add more cases as needed
        else:
            return f"{width}x{height}"
    return "Unknown"

def read_array_from_file(file_path):
    """
    从文件中读取数组并返回。
    如果文件不存在，返回空数组。
    """
    try:
        with open(file_path, 'r') as file:
            my_array = [line.strip() for line in file.readlines()]
        return my_array
    except FileNotFoundError:
        print(f'文件 {file_path} 未找到.')
        return []
    except Exception as e:
        print(f'发生错误: {e}')
        return []


def write_array_to_file(file_path, my_array):
    """
    将数组写入文件。
    如果文件不存在，创建新文件。
    """
    try:
        with open(file_path, 'w') as file:
            for item in my_array:
                file.write(f'{item}\n')
        print(f'数组已成功写入文件: {file_path}')
    except Exception as e:
        print(f'发生错误: {e}')



if __name__ == '__main__':
    source_path = sys.argv[0]
    log_path = os.path.dirname(os.path.abspath(__file__))
    logger = get_logger(name=f'test_tool', path=log_path, func_name='main')
    get_file_inode(file_path='/mnt/unraid/电影/completed/爱情神话 (2021)/爱情神话 (2021)-2160P.mkv')
    get_file_size(file_path='/mnt/unraid/电影/completed/爱情神话 (2021)/爱情神话 (2021)-2160P.mkv')