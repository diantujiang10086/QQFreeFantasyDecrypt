# -*- coding: utf-8 -*-
"""所有脚本共用的资源根解析（便携：不写死任何盘符）。

解析顺序：环境变量 FFO_DATA > 本地配置 data/ffo_data.txt（一行路径）> 空。
约定：DATA 指向「存放 objects*.pkg 的目录」；official 资源在其下的 data/official。
服务器（私服源码/表）不是运行期依赖：只有 FFO_SERVER 指向的目录才可用。
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def _conf():
    p = os.path.join(HERE, 'data', 'ffo_data.txt')
    try:
        with io.open(p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    return line
    except OSError:
        pass
    return ''


DATA = os.environ.get('FFO_DATA', '') or _conf()
OFFICIAL = os.path.join(DATA, 'data', 'official') if DATA else ''
WORK = HERE                                      # 工作区（本地 json / 缓存都放这里）
SERVER = os.environ.get('FFO_SERVER', '')        # 可选，私服源码目录


def sub(*parts):
    """official 下的子目录，例如 sub('avatar', 'head')。"""
    return os.path.join(OFFICIAL, *parts) if OFFICIAL else os.path.join(*parts)


def exists():
    return bool(DATA) and os.path.isdir(DATA)
