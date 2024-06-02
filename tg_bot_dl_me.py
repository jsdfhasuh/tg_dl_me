import asyncio
from telethon import TelegramClient, events
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import requests
import difflib
import os
import re
import time
import asyncio
import asyncio.subprocess
import sys
import logger
import unicodedata
import configparser
from tool import write_dict_to_json,read_dict_from_json

from telethon.tl.types import MessageMediaWebPage
# Remember to use your own values from my.telegram.org!
api_id = 0  # your telegram api id
api_hash = ''  # your telegram api hash
proxy = ''
max_num = 5 # 同时下载数量
# filter file name/文件名过滤
filter_list = []
#filter chat id /过滤某些频道不下载
blacklist = []
filter_file_name = []  # 过滤文件名字
#top_path=r'D:\test'
top_path=''

chat_id=0
offset_id=0
find_key_word = ""
tasks = []
all_history = {}
all_history_ing = {}
group_message = {}
group_history = {}
file_message_history = {}
get_message_history = {}



def read_config(path):
    config = configparser.ConfigParser()
    # 读取配置文件
    with open(os.path.join(path,'config.ini'), 'r', encoding='utf-8') as file:
        config.read_file(file)
    return config

def count_chinese_characters(input_string):
    count = 0
    for char in input_string:
        if 'CJK UNIFIED' in unicodedata.name(char):
            count += 1
    return count


def check_chienese_characters(input_string):
    for char in input_string:
        if 'CJK UNIFIED' not in unicodedata.name(char):
            return False
    return True


def validateTitle(title):
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    new_title = re.sub(r_str, "_", title)  # 替换为下划线
    return new_title

def read_local_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content,True
    except FileNotFoundError:
        logger.info(f"文件 '{file_path}' 未找到.")
        return "",False
    except IOError:
        logger.info(f"无法读取文件 '{file_path}'.")
        return "",False

def save_to_local_file(file_path, data):
    try:
        with open(file_path, 'w') as file:
            file.write(data)
        logger.info(f"数据已成功保存到文件 '{file_path}'.")
    except IOError:
        logger.info(f"无法写入文件 '{file_path}'.")

# 文件夹/文件名称处理 魔改的
def validateTitle2(title):
    global i
    i=i+1
    r_str = r"[\/\\\:\*\?\"\<\>\|\n]"  # '/ \ : * ? " < > |'
    #r_str2 = r"\#[^ ]+"  # '/ \ : * ? " < > |'
    
    new_title = re.sub(r_str, ".", title)  # 替换为下划线
    #new_title2 = re.sub(r_str2, "", new_title)  # 删除多余字符
    new_title3 = re.sub(r' ', "", new_title)  # 删除多余字符
    new_title5 = new_title3[:40]
    if new_title5 != "":
        # 去掉字符串最后的非中文字符
        i = 0
        max = len(new_title5)
        while i < max:
            i += 1
            if check_chienese_characters(new_title5[-i]):
                new_title5 = new_title5[:-i]
                break
    return new_title5

def validate_folder_name(folder_name):
    # 定义非法字符
    invalid_chars = r"[\/\\\:\*\?\"\<\>\|\n]"
    # 使用正则表达式替换非法字符为下划线
    valid_name = re.sub(invalid_chars, "_", folder_name)
    # 限制文件夹名的长度，例如最长为50个字符
    valid_name = valid_name[:50]
    return valid_name


# 获取相册标题
async def get_group_caption(message):
    global group_history
    group_caption = ""
    # 获取实体
    entity = await client.get_entity(message.to_id)
    group_lower_edge = 0
    group_higher_edge = 0
    if group_history.get(message.grouped_id):
        group_lower_edge = group_history[message.grouped_id]['group_lower_edge']
        group_higher_edge = group_history[message.grouped_id]['group_higher_edge']
        group_caption = group_history[message.grouped_id]['group_caption']
    else:
        group_history[message.grouped_id]={'group_lower_edge':group_lower_edge,'group_higher_edge':group_higher_edge,'group_caption':""}
    limit = 10
    offset = 9
    if group_caption:
        return group_caption
    while True:
        # 获取下边界
        i = 0
        #logger.info(f'开始获取下边界')
        async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=message.id - 9, limit=limit):
            if message.grouped_id in group_history:
                group_history[message.grouped_id]['group_lower_edge'] = group_lower_edge
            if group_lower_edge:
                break
            #print(msg.id)
            i += 1
            if msg.grouped_id != message.grouped_id:
                pass
            elif i == 0 and msg.grouped_id == message.grouped_id:
                offset += 10
                limit += 10
                break
            elif msg.grouped_id == message.grouped_id:
                #logger.info(f'找到下边界{msg.id}')
                group_lower_edge = msg.id
                group_history[msg.grouped_id]['group_lower_edge'] = group_lower_edge
                limit = 10
                offset = 9
                if msg.text != "":
                    group_caption = msg.text
                    group_history[msg.grouped_id]['group_caption'] = msg.text
                    return group_caption
        break
    while True:
        # 获取上边界
        #logger.info(f'开始获取上边界')
        i = 0
        async for msg in client.iter_messages(entity=entity, reverse=False, offset_id=message.id + 9, limit=limit):
            if message.grouped_id in group_history:
                group_history[message.grouped_id]['group_higher_edge'] = group_higher_edge
            if group_higher_edge:
                break
            #print(msg.id)
            i += 1
            if msg.grouped_id != message.grouped_id:
                pass
            elif i == 0 and msg.grouped_id == message.grouped_id:
                offset += 10
                limit += 10
                break
            elif msg.grouped_id == message.grouped_id:
                #logger.info(f'找到上边界{msg.id}')
                group_higher_edge = msg.id
                group_history[msg.grouped_id]['group_higher_edge'] = group_higher_edge
                if msg.text != "":
                    group_caption = msg.text
                    group_history[msg.grouped_id]['group_caption'] = msg.text
                    return group_caption
        break
    # 在拥有两边边界之后，找txt
    async for msg in client.iter_messages(entity=entity, reverse=True, offset_id=group_lower_edge-1, limit=group_higher_edge - group_lower_edge):
        if msg.text != "":
            group_caption = msg.text
            group_history[msg.grouped_id]['group_caption'] = msg.text
            return group_caption
    if group_caption == "":
        return group_caption


# 获取本地时间
def get_local_time():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


# 判断相似率
def get_equal_rate(str1, str2):
    return difflib.SequenceMatcher(None, str1, str2).quick_ratio()


# 返回文件大小
def bytes_to_string(byte_count):
    suffix_index = 0
    while byte_count >= 1024:
        byte_count /= 1024
        suffix_index += 1

    return '{:.2f}{}'.format(
        byte_count, [' bytes', 'KB', 'MB', 'GB', 'TB'][suffix_index]
    )

def read_all_json(history_jsons):
    all_json = {}
    for key in history_jsons:
        if os.path.exists(history_jsons[key]):
            tmp_json = read_dict_from_json(history_jsons[key])
            for key in tmp_json:
                all_json[key] = tmp_json[key]
        else:
            continue
    return all_json


def record_message_id(message_id,file_name):
    global  file_message_history
    if file_name in file_message_history:
        file_message_history[file_name].append(message_id)
    else:
        file_message_history[file_name] = [message_id]


def check_all_history_ing(key_name):
    global all_history_ing
    if key_name in all_history_ing:
        return False
    else:
        return True




async def worker(name,json_path):
    while True:
        logger.info(f"woker{name}——开始准备下载")
        json_data = read_dict_from_json(json_path)
        queue_item = await queue.get()
        message = queue_item[0]
        file_name = queue_item[1]
        file_path = queue_item[2]
        key = queue_item[3]
        for filter_file in filter_file_name:
            if filter_file in file_name:
                logger.info(f'存在排除名字{filter_file}')
                return

        logger.info(f"woker{name}——开始下载： {file_name} 文件完整路径：{file_path}")
        file_download_folder =  os.path.join(os.path.dirname(file_path),'.tmp')
        os.makedirs(file_download_folder,exist_ok=True)
        file_download_path = os.path.join(file_download_folder,file_name)
        temp_message=await client.send_message('me', f'woker{name}——开始下载： {file_name}')
        record_message_id(message_id=temp_message.id, file_name=file_name)
        try:
            loop = asyncio.get_event_loop()
            task = loop.create_task(client.download_media(message, file_download_path))
            #await fast_download(client=client, msg=message,download_folder=file_save_path)
            await asyncio.wait_for(task, timeout=7200)
            os.rename(file_download_path, file_path)
        except asyncio.TimeoutError:
            os.remove(file_path)
            new_message = await client.get_messages(message.chat, ids=message.id)
            await queue.put((new_message,file_name))

            logger.info('timeout!,重新加入队列')
        except OSError as e:
            logger.info(f"{get_local_time()} - {file_name} {e}")
            logger.info(f'错误{e}，不加入队列')
        except Exception as e:
            logger.info(f"{get_local_time()} - {file_name} {e}")
            os.remove(file_path)
            logger.info(f'错误{e}，重新加入队列')
            new_message = await client.get_messages(message.chat, ids=message.id)
            await queue.put((new_message,file_name))
        finally:
            if os.path.exists(file_download_path):
                os.remove(file_download_path)
            logger.info(f"woker{name}——{file_name}下载完成")
            info = all_history_ing[key]
            json_data[key] = info
            all_history[key] = info
            write_dict_to_json(filename=json_path,data=json_data)
            for message_id in file_message_history[file_name]:
                await client.delete_messages('me', message_id)
            queue.task_done()

async def get_message_by_me():
    num_items = queue.qsize()
    if num_items > max_num*3:
        pass
    else:
        async for message in client.iter_messages('me', reverse=False, limit=None):
            if message.media:
                # 如果是一组媒体
                if message.grouped_id and message.text == "":
                    caption = await get_group_caption(message)
                else:
                    caption = message.text
                # 过滤文件名称中的广告等词语
                if len(filter_list) and caption != "":
                    for filter_keyword in filter_list:
                        caption = caption.replace(filter_keyword, "")
                # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                caption = "" if caption == "" else f'{validateTitle2(caption)} - '[:50]
                file_name = ''
                # 如果是文件
                if message.document:
                    if message.media.document.mime_type == "image/webp":
                        continue
                    if message.media.document.mime_type == "application/x-tgsticker":
                        continue
                    for i in message.document.attributes:
                        try:
                            file_name = i.file_name
                        except:
                            continue
                    if file_name == '':
                        file_name = f'{message.id} - {caption}.{message.document.mime_type.split("/")[-1]}'
                        logger.info(file_name)
                    else:
                        # 如果文件名中已经包含了标题，则过滤标题
                        if get_equal_rate(caption, file_name) > 0.6:
                            caption = ""
                        file_name = f'{message.id} - {caption}{file_name}'
                elif message.photo:
                    file_name = f'{message.id} - {caption}{message.photo.id}.jpg'
                else:
                    continue
                logger.info('正在查阅本地信息')
                file_save_path = os.path.join(top_path,'me',file_name)
                if os.path.exists(file_save_path):
                    logger.info(f"{file_name}该文件存在，跳过")
                    continue
                    # os.remove(os.path.join(file_save_path, file_name))
                else:
                    num_items = queue.qsize()
                    logger.info(f'队列拥有的任务:{num_items}')
                    while num_items > max_num:
                        num_items = queue.qsize()
                        await asyncio.sleep(30)
                    logger.info(f"{file_name}放入队列")
                    await queue.put((message,file_name))



async def get_message():
    global chat_id
    global find_key_word
    global get_message_history
    global offset_id
    local_offset_id = 0
    send_message_ids = []
    root = 0
    sleep_time = 1
    get_message_history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_message_history.json')
    logger.info('开始频道抓取下载')
    if chat_id:
        entity = await client.get_entity(chat_id)
        chat_title = entity.title
        logger.info(f'频道抓取_{get_local_time()} - 开始下载：{chat_title}({entity.id}) - {offset_id}')
        last_msg_id = 0
        reverse = True
        number = 0
        if offset_id <0:
            number = abs(offset_id)
            offset_id = 0
            reverse = False
        if find_key_word:
            logger.info(f'有查找关键字{find_key_word}')
        if f'{chat_title}_{offset_id}_{reverse}_{find_key_word}' in get_message_history:
            local_offset_id = get_message_history[f'{chat_title}_{offset_id}_{reverse}_{find_key_word}']['processed_id']
            logger.info(f'从历史记录中恢复{chat_title}  message plan to task queue.first message is：{offset_id},reverse is {reverse}')
        else:
            get_message_history[f'{chat_title}_{offset_id}_{reverse}_{find_key_word}'] = {'chat_id': chat_id, 'root_offset_id': offset_id, 'reverse': reverse, 'find_key_word': find_key_word,'processed_id':offset_id}
        i = 0
        await client.send_message('me',f'{chat_title}  message plan to task queue.first message is：{offset_id},reverse is {reverse}')
        if local_offset_id:
            find_offset_id = local_offset_id
        else:
            find_offset_id = offset_id
        sleep_count = 0
        async for message in client.iter_messages(entity, offset_id=find_offset_id, reverse=reverse, limit=None):
            get_message_history[f'{chat_title}_{offset_id}_{reverse}_{find_key_word}'] = {'chat_id': chat_id, 'root_offset_id': offset_id, 'reverse': reverse, 'find_key_word': find_key_word,'processed_id':message.id}
            write_dict_to_json(data=get_message_history,filename=get_message_history_file)
            sleep_count += 1
            if sleep_count == 20:
                sleep_count = 0
                await asyncio.sleep(sleep_time)
                logger.info(f'休息{sleep_time}秒')
                send_message_ids.append(await client.send_message('me', f'休息{sleep_time}秒'))
            if len(send_message_ids):
                for id in send_message_ids:
                    await client.delete_messages('me', id)
            send_message_ids.append(await client.send_message('me', f'message {message.id} processing'))
            if number and i >= number:
                logger.info('结束抓取')
                break
            else:
                if message.media:
                    # await message_handler(message, event)
                    root_chanal_title = ""
                    group_message = ""

                    root_chanal_title = message.sender.title

                    # 如果是一组媒体
                    if message.grouped_id is not None:
                        tmp_group_message = await get_group_caption(message)
                        if tmp_group_message:
                            group_message = tmp_group_message
                            logger.info(f"{message.id}这条消息是与其他消息整合在一起的,{group_message}")
                        else:
                            logger.info(f"{message.id}这条消息是与其他消息整合在一起的,但是没有找到标题")
                            if group_message:
                                logger.info(f'{message.id}使用之前的标题{group_message}')
                            else:
                                group_id = message.grouped_id
                                logger.info(f'{message.id}没有找到标题,用grouped_id代替{group_message}')
                    else:
                        logger.info("这条消息是单独的")
                        group_message = ""
                    if find_key_word:
                        for element in [group_message,message.text]:
                            if element:
                                if find_key_word in element:
                                    break
                        else:
                            continue

                    caption = message.text
                    # 过滤文件名称中的广告等词语
                    if len(filter_list) and caption != "":
                        for filter_keyword in filter_list:
                            caption = caption.replace(filter_keyword, "")
                    # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
                    caption = "" if caption == "" else f'{validateTitle2(caption)} - '[:50]
                    file_name = ''
                    # 如果是文件
                    if message.document:
                        if message.media.document.mime_type == "application/x-tgsticker":
                            continue
                        elif 'text' in message.media.document.mime_type:
                            type = 'text'
                            type_name = '.txt'
                        elif 'video' in message.media.document.mime_type:
                            type = 'video'
                            type_name = '.mp4'
                        for i in message.document.attributes:
                            if hasattr(i, 'file_name'):
                                file_name = i.file_name
                                logger.info(f'文件名字：{file_name}')
                                break
                        if file_name == '':
                            file_name = f'{message.id}.{message.document.mime_type.split("/")[-1]}'
                        else:
                            file_name = f'{file_name}'
                    elif message.photo:
                        file_name = f'{message.photo.id}.jpg'
                        type_name = '.jpg'
                        type = 'image'
                    else:
                        continue

                    # 根据中文字符的多少判断使用那个作为file_name
                    
                    num1 = count_chinese_characters(file_name)
                    num2 = count_chinese_characters(caption)
                    if num2 > num1:
                        file_name = f"{caption}{type_name}"
                    else:
                        file_name = file_name

                    root_folder_path = os.path.join(top_path)
                    if root_chanal_title:
                        root_folder_path = os.path.join(root_folder_path, validate_folder_name(root_chanal_title))
                    if group_message:
                            root_folder_path = os.path.join(root_folder_path, validate_folder_name(group_message))
                    elif group_id:
                        root_folder_path = os.path.join(root_folder_path, validate_folder_name(str(group_id)))
                    else:
                        file_name = f'{message.id}-{file_name}'
                    os.makedirs(root_folder_path, exist_ok=True)
                    if len(file_name) < 6:
                        file_name = f'{message.id}-{file_name}'
                    # 获取正在执行的任务
                    for element in all_history_ing:
                        old_file_name = all_history_ing[element]['file_name']
                        if old_file_name == file_name:
                            file_name = f'{message.id}-{file_name}'
                            break
                    else:
                        pass
                    file_save_path = os.path.join(root_folder_path, file_name)
                    key_name = ""
                    # 获取必要消息
                    if type == 'text':
                        size = message.media.document.size
                        tmp_file_name = message.media.document.attributes[0].file_name.split('.')[0]
                        key_name = f'{type}_{tmp_file_name}_{size}'
                        if check_all_history_ing(key_name=key_name):
                            all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type,'save_path':file_save_path}
                        else:
                            logger.info(f"{file_name}该文件已经在下载路径，跳过")
                            continue
                        pass
                    elif type == 'video':
                        size = message.media.document.size
                        tmp_file_name = message.media.document.attributes[1].file_name
                        tmp_file_name, ext = os.path.splitext(tmp_file_name)
                        height = message.media.document.attributes[0].h
                        weight = message.media.document.attributes[0].w
                        duration = message.media.document.attributes[0].duration
                        if check_all_history_ing(key_name=key_name):
                            all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type, 'save_path': file_save_path,'height':height,'weight':weight,'duration':duration}
                        else:
                            logger.info(f"{file_name}该文件已经在下载路径，跳过")
                            continue
                    elif type == 'image':
                        size = message.photo.sizes[-1].sizes[-1]
                        height = message.photo.sizes[-1].h
                        weight = message.photo.sizes[-1].w
                        key_name = f'{type}_{file_name}_{size}_{height}_{weight}'
                        if check_all_history_ing(key_name=key_name):
                            all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type, 'save_path': file_save_path,'height':height,'weight':weight}
                        else:
                            logger.info(f"{file_name}该文件已经在下载路径，跳过")
                            continue
                    temp_file_name = file_name

                    # 判断之前的历史记录
                    if key_name and key_name in all_history:
                        history_path = all_history[key_name]['save_path']
                        if os.path.exists(history_path) :
                            if os.path.getsize(history_path) == all_history_ing[key_name]['size']:
                                logger.info(f"{file_name}该文件已经下载过，跳过")
                                #await client.delete_messages('me', message.id)
                                continue
                            else:
                                logger.info(f"{file_name}该文件没有下载，但本地有相同文件名")
                                file_name = f'{message.id}-{file_name}'
                    elif os.path.exists(file_save_path):
                        logger.info(f"{file_name}该文件没有成功下载，删除源文件")
                        os.remove(file_save_path)
                    
                    if temp_file_name != file_name:
                        logger.info(f"文件名字被修改{temp_file_name}-->{file_name}")
                        file_save_path = os.path.join(root_folder_path, file_name)
                        all_history_ing[key_name]['file_name'] = file_name
                        all_history_ing[key_name]['save_path'] = file_save_path
                    num_items = queue.qsize()
                    logger.info(f'队列拥有的任务:{num_items}')
                    logger.info(f"{file_name}放入队列")
                    await queue.put((message, file_name, file_save_path, key_name))
                    send_message_ids.append(await client.send_message('me', f'{message.id}  message finish'))
                    last_msg_id = message.id
            i += 1
        await client.send_message('me',f'{chat_title} all message added to task queue, last message is：{last_msg_id}')
        chat_id=0
        offset_id=0


@events.register(events.NewMessage())
async def my_event_handler(event):
    global chat_id
    global offset_id
    global loop
    global task
    global group_message
    global find_key_word
    type = ""
    group_id = 0
    chat = await event.get_chat()
    try:
        myself=chat.is_self
    except Exception as E:
        #logger.info(f'没有检测到is_self')
        return
    if myself:
        message = event.message
        if message.media:
            #await message_handler(message, event)
            root_chanal_title = ""
            # 如果是转发的消息，则获取原始频道名字
            if message.forward:
                root_chanal_title = message.forward.chat.title
            else:
                pass
            # 如果是一组媒体
            if message.grouped_id is not None:
                tmp_group_message = await get_group_caption(message)
                if tmp_group_message:
                    group_message = tmp_group_message
                    logger.info(f"{message.id}这条消息是与其他消息整合在一起的,{group_message}")
                else:
                    logger.info(f"{message.id}这条消息是与其他消息整合在一起的,但是没有找到标题")
                    if group_message:
                        logger.info(f'{message.id}使用之前的标题{group_message}')
                    else:
                        group_id = message.grouped_id
                        logger.info(f'{message.id}没有找到标题,用grouped_id代替{group_message}')
            else:
                logger.info("这条消息是单独的")
                group_message = ""
            caption = message.text #该信息内容
            # 过滤文件名称中的广告等词语
            if len(filter_list) and caption != "":
                for filter_keyword in filter_list:
                    caption = caption.replace(filter_keyword, "")
            # 如果文件文件名不是空字符串，则进行过滤和截取，避免文件名过长导致的错误
            caption = "" if caption == "" else f'{validateTitle2(caption)}'
            file_name = ''
            # 如果是文件
            if message.document:
                if message.media.document.mime_type == "application/x-tgsticker":
                    return 0
                elif 'text' in message.media.document.mime_type:
                    type = 'text'
                    type_name = '.txt'
                elif 'video' in message.media.document.mime_type:
                    type = 'video'
                    type_name = '.mp4'
                for i in message.document.attributes:
                    if hasattr(i, 'file_name'):
                        file_name = i.file_name
                        logger.info(f'文件名字：{file_name}')
                        break
                if file_name == '':
                    file_name = f'{message.id}.{message.document.mime_type.split("/")[-1]}'
                else:
                    file_name = f'{file_name}'
            elif message.photo:
                file_name = f'{message.photo.id}.jpg'
                type_name = '.jpg'
                type = 'image'
            else:
                return 0
            
            # 根据中文字符的多少判断使用那个作为file_name
            num1 = count_chinese_characters(file_name)
            num2 = count_chinese_characters(caption)
            if num2 > num1:
                file_name = f"{caption}{type_name}"
            else:
                file_name = file_name
            
            root_folder_path = os.path.join(top_path, 'me')
            if root_chanal_title:
                root_folder_path = os.path.join(root_folder_path, validate_folder_name(root_chanal_title))
                #logger.info(f'root_chanal_title message:{message.id},root_folder_path:{root_folder_path}')
            if group_message:
                root_folder_path = os.path.join(root_folder_path, validate_folder_name(group_message))
            elif group_id:
                root_folder_path = os.path.join(root_folder_path, validate_folder_name(str(group_id)))
            else:
                file_name = f'{message.id}-{file_name}'
                #logger.info(f'group_message message:{message.id},root_folder_path:{root_folder_path}')
            os.makedirs(root_folder_path, exist_ok=True)
            if len(file_name) < 6:
                file_name = f'{message.id}-{file_name}'
            # 获取正在执行的任务
            for element in all_history_ing:
                old_file_name = all_history_ing[element]['file_name']
                if old_file_name == file_name:
                    file_name = f'{message.id}-{file_name}'
                    break
            else:
                pass
            file_save_path = os.path.join(root_folder_path, file_name)

            key_name=""


            # 获取必要消息
            if type == 'text':
                size = message.media.document.size
                tmp_file_name = message.media.document.attributes[0].file_name.split('.')[0]
                key_name = f'{type}_{tmp_file_name}_{size}'
                if check_all_history_ing(key_name=key_name):
                    all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type,'save_path':file_save_path}
                else:
                    logger.info(f"{file_name}该文件已经在下载路径，跳过")
                    message = await event.reply(f"{file_name}该文件已经在下载路径，跳过")
                    return 0
                pass
            elif type == 'video':
                size = message.media.document.size
                tmp_file_name = file_name
                tmp_file_name, ext = os.path.splitext(tmp_file_name)
                height = message.media.document.attributes[0].h
                weight = message.media.document.attributes[0].w
                duration = message.media.document.attributes[0].duration
                key_name = f'{type}_{size}_{height}_{weight}_{duration}'
                if check_all_history_ing(key_name=key_name):
                    all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type, 'save_path': file_save_path,'height':height,'weight':weight,'duration':duration}
                else:
                    logger.info(f"{file_name}该文件已经在下载路径，跳过")
                    message = await event.reply(f"{file_name}该文件已经在下载路径，跳过")
                    return 0
            elif type == 'image':
                size = message.photo.sizes[-1].sizes[-1]
                height = message.photo.sizes[-1].h
                weight = message.photo.sizes[-1].w
                key_name = f'{type}_{file_name}_{size}_{height}_{weight}'
                if check_all_history_ing(key_name=key_name):
                    all_history_ing[key_name] = {'file_name': file_name, 'size': size, 'type': type, 'save_path': file_save_path,'height':height,'weight':weight}
                else:
                    logger.info(f"{file_name}该文件已经在下载路径，跳过")
                    message = await event.reply(f"{file_name}该文件已经在下载路径，跳过")
                        #await client.delete_messages('me', message.id)
                    return 0
            temp_file_name = file_name


            # 判断之前的历史记录
            if key_name and key_name in all_history:
                history_path = all_history[key_name]['save_path']
                if os.path.exists(history_path) :
                    if os.path.getsize(history_path) == all_history_ing[key_name]['size']:
                        logger.info(f"{file_name}该文件已经下载过，跳过")
                        message = await event.reply(f"{file_name}该文件已经下载过，跳过")
                        #await client.delete_messages('me', message.id)
                        return 0
                    else:
                        logger.info(f"{file_name}该文件没有下载，但本地有相同文件名")
                        file_name = f'{message.id}-{file_name}'
            elif os.path.exists(file_save_path):
                logger.info(f"{file_name}该文件没有成功下载，删除源文件")
                os.remove(file_save_path)
            
            if temp_file_name != file_name:
                logger.info(f"文件名字被修改{temp_file_name}-->{file_name}")
                file_save_path = os.path.join(root_folder_path, file_name)
                all_history_ing[key_name]['file_name'] = file_name
                all_history_ing[key_name]['save_path'] = file_save_path
            num_items = queue.qsize()
            logger.info(f'队列拥有的任务:{num_items}')
            logger.info(f"message_id:{message.id},{file_name}放入队列,下载路径是{file_save_path}")
            tmp_message = await event.reply(f'{file_name}加入下载队列!')
            record_message_id(message_id=tmp_message.id, file_name=file_name)
            await queue.put((message, file_name, file_save_path,key_name))
        if message.text:
            text = event.message.text.split(' ')
            if '清空group' in text:
                await event.reply('清空group_message')
                group_message = ""
                return
            if '开始频道下载' in text:
                if len(text) == 1:
                    await event.reply('参数错误，请按照参考格式输入:\n\n ''<i>/start https://t.me/fkdhlg 0 </i>\n\n''Tips:如果不输入offset_id，默认从第一条开始下载。',parse_mode='HTML')
                    return
                elif len(text) == 2:
                    chat_id = text[1]
                    try:
                        entity = await client.get_entity(chat_id)
                        chat_title = entity.title
                        offset_id = 0
                        loop = asyncio.get_event_loop()
                        task = loop.create_task(get_message())
                        tasks.append(task)
                        await event.reply(f'开始从{chat_title}的第一条消息下载。')
                    except:
                        await event.reply('chat输入错误，请输入频道或群组的链接')
                        return
                elif len(text) == 3:
                    chat_id = text[1]
                    offset_id = int(text[2])
                    try:
                        entity = await client.get_entity(chat_id)
                        chat_title = entity.title
                        loop = asyncio.get_event_loop()
                        task = loop.create_task(get_message())
                        tasks.append(task)
                        await event.reply(f'开始从{chat_title}的第{offset_id}条消息下载。')
                    except:
                        await event.reply('chat输入错误，请输入频道或群组的链接')
                        return
                elif len(text) == 4:
                        chat_id = text[1]
                        offset_id = int(text[2])
                        find_key_word= text[3]
                        try:
                            entity = await client.get_entity(chat_id)
                            chat_title = entity.title
                            loop = asyncio.get_event_loop()
                            task = loop.create_task(get_message())
                            tasks.append(task)
                            await event.reply(f'开始从{chat_title}的第{offset_id}条消息下载。')
                        except:
                                await event.reply('chat输入错误，请输入频道或群组的链接')
                                return

                else:
                    await event.reply('参数错误，请按照参考格式输入:\n\n ''<i>/start https://t.me/fkdhlg 0 </i>\n\n''Tips:如果不输入offset_id，默认从第一条开始下载。',parse_mode='HTML')
                    return

def check_string(string):
    while True:
        try:
            with TelegramClient(StringSession(string), api_id, api_hash,proxy=proxy,connection_retries=5,auto_reconnect=True,retry_delay=5) as client:
                string = client.session.save()
            return True,string
        except Exception as e:
            return False,""




def get_new_string():
    with TelegramClient(StringSession(), api_id, api_hash,proxy=proxy) as client:
        string = client.session.save()
    return string

def init(path):
    global top_path,filter_file_name,filter_list,api_id,api_hash,proxy,max_num,blacklist
    config_data = read_config(path)
    top_path = config_data.get('Paths', 'top_path')
    api_id = config_data.get('User_info', 'api_id')
    api_hash = config_data.get('User_info', 'api_hash')
    proxy =   tuple(config_data.get('User_info', 'proxy').split(','))
    max_num = int(config_data.get('Download', 'max_num'))
    filter_list = config_data.get('Download', 'filter_list').split(',')
    blacklist = config_data.get('Download', 'blacklist').split(',')
    filter_file_name = config_data.get('Download', 'filter_file_name').split(',')
      

if __name__ == '__main__':

    i=0
    source_path = sys.argv[0]
    path = os.path.dirname(os.path.abspath(__file__))
    init(path)
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    session_path = os.path.join(script_dir, 'session')
    history_json_folder = os.path.join(script_dir, 'history_json')
    get_message_history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'get_message_history.json')
    get_message_history = read_dict_from_json(filename=get_message_history_file)
    history_jsons = {}
    logger = logger.get_logger(os.path.basename(sys.argv[0]), path,func_name='main')
    logger.info(proxy)
    remote_string_status = False
    while True:
        string,local_string_status = read_local_file(session_path)
        if not local_string_status:
            logger.info("no local string,try to login")
        status,new_string = check_string(string=string)
        if new_string == string:
            logger.info(f'right string{string}')
        else:
            logger.info('wrong string')
            string = new_string
            if string:
                save_to_local_file(file_path=session_path,data=string)
            else:
                logger.info('没有登录，关闭程序')
                exit(200)
        try:
            with TelegramClient(StringSession(string), api_id, api_hash,proxy=proxy,connection_retries=5,auto_reconnect=True,retry_delay=5) as client:
                queue = asyncio.Queue()
                client.add_event_handler(my_event_handler)
                loop = asyncio.get_event_loop()
                client.send_message('me', "进入监控\n1.直接转发媒体，将自动下载\n2.根据你的需求从频道按照顺序下载\n请按照参考格式输入:\n '开始频道下载 https://t.me/fkdhlg 0 \n''开始频道下载 https://t.me/fkdhlg 0 关键词\n''Tips:如果不输入0，默认从第一条开始下载。")
                try:
                    for i in range(max_num):
                        history_jsons[f'worker-{i}'] = os.path.join(history_json_folder, f'worker-{i}.json')
                        task2 = loop.create_task(worker(name=f'worker-{i}',json_path=os.path.join(history_json_folder, f'worker-{i}.json')))

                        tasks.append(task2)
                    all_history = read_all_json(history_jsons)
                    client.run_until_disconnected()
                finally:
                    for task in tasks:
                        task.cancel()
                    client.disconnect()
                    logger.info('Stopped!')
        except TimeoutError as e:
            logger.info(f'连接超时，等待10s再启动')
            time.sleep(10)
            continue
        except Exception as e:
                logger.info(f'发生不知名错误f{e}，关闭程序')
                exit(200)




