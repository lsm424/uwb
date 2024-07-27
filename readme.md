# UWB上位机客户端

本项目基于python+pyside6实现从多个UWB测量模块汇聚数据，解析得到测量值写csv文件和实时展示。

## 输入说明

1. 数据格式：TLV数据，协议为：

* 0x2121，CIR相位集中上传
* 0x3012，载波相位测距集中上传
* 0x300d，传感器数据输出
* 0x2042，时隙占用表数据上传
* 0x4090，TDOA与PDOA集中上传
* 0x2011，TOF距离集中上传

2、输入方式：

* 串口：相关参数支持在配置文件config.yaml中设置，也支持在界面中配置
* udp：服务端口支持在配置文件config.yaml中设置，也支持在界面中配置

## 安装

pip install -r requirements.txt

## 运行

1、配置：参考config.yaml中有注释

2、源码运行：python main.py

3、udp测试客户端：python simUWBSystem.py

3、测量值csv文件路径：根目录下的out_file文件下，按启动时间细分子文件夹，生成每种协议对应的测量值csv文件

## 打包exe：

* linux：pyinstaller --hidden-import=access --hidden-import=uwb --hidden-import=common --hidden-import=gui -F main.py
* win：python -m nuitka --follow-imports --enable-plugin=pyside6 --plugin-enable=numpy --include-package=matplotlib --include-package=common --include-package=gui --include-package=uwb --include-package=access --standalone --onefile  main.py
