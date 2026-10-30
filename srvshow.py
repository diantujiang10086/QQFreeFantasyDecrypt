"""按行号打印已拷贝到 out/srv 的服务端模块（ASCII 安全）。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def show(name, a, b):
    p = os.path.join(HERE, 'out', 'srv', name)
    lines = open(p, encoding='utf-8').read().splitlines()
    for i in range(a - 1, min(b, len(lines))):
        text = lines[i].encode('ascii', 'replace').decode('ascii')
        print('%4d| %s' % (i + 1, text))


if __name__ == '__main__':
    show(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
