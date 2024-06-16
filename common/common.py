import csv
import os
import time
import datetime
import loguru
import yaml


loguru.logger.add("./ubw.log", level="INFO", encoding="utf-8",
                  retention="10 days", rotation="1 day", enqueue=True)
logger = loguru.logger

if not os.path.exists('config.yaml'):
    logger.error(f'请把config.yaml配置文件放到同文件夹下，然后重启程序')
    while True:
        time.sleep(100)

with open(file="config.yaml", mode="r", encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 提取csv文件头


def get_header(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, 'r', newline='') as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
        except BaseException as e:
            return None
        return header


# out_file_dir = os.path.join(
#     'out_file', datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S'))
# if not os.path.exists(out_file_dir):
#     os.makedirs(out_file_dir)
# logger.info(f'文件输出路径：{out_file_dir}')


def save(writer, queue, csv_file):
    while True:
        pkgs = queue.get()
        while not queue.empty() and len(pkgs) < 2000:
            pkgs += queue.get(block=False)
        if len(pkgs) == 0:
          continue
        writer.writerows(pkgs)
        if '传感器' in str(csv_file) or 'TOF' in str(csv_file):
          continue
        logger.warning(f'{csv_file} 写文件{len(pkgs)}')
        # csv_file.flush()
