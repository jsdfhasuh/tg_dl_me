import os
from logger import *

import sys
import json


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
