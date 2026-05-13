#!/usr/bin/env python3
import os

# 获取 HOME 目录
home = os.path.expanduser("~")
bashrc = os.path.join(home, ".bashrc")

# 读取内容
with open(bashrc, "r") as f:
    lines = f.readlines()

# 过滤掉无效的别名行
lines = [line for line in lines if line.strip() != "alias"]

# 确保末尾有换行
if lines and not lines[-1].endswith("\n"):
    lines[-1] += "\n"

# 添加新别名
lines.append("\n")
lines.append("alias flypig='python3 -m flypig'\n")

# 写回文件
with open(bashrc, "w") as f:
    f.writelines(lines)

print("Done!")
