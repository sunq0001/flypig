#!/bin/bash
export PATH=$HOME/.local/bin:$PATH
pip install vulture -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --break-system-packages
echo "EXIT: $?"
