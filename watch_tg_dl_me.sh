#!/bin/bash

# 定义Python脚本的名称和路径
python_script="tg_bot_dl_me.py"
python_script_path="/ql/data/scripts/tg_dl_me"

# 检查Python脚本是否在运行
if ! pgrep -f "$python_script"; then
    # 如果脚本未运行，则启动它
    echo "启动 $python_script"
    cd /ql/data/scripts/tg_dl_me && nohup python3 tg_bot_dl_me.py &
else
    echo "$python_script 已经在运行"
fi
