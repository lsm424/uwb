import csv
import os
import loguru
import yaml


loguru.logger.add("./ubw.log", colorize=True, level="INFO", encoding="utf-8", retention="5 days", rotation="1 day", enqueue=True)
logger = loguru.logger


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

if not os.path.exists('./out_file'):
    os.mkdir('./out_file')
pickle_file = open('out_file/pickle_file.dat', 'ab')


def save(writer, queue, csv_file):
    while True:
        pkg = queue.get()
        writer.writerows(pkg)
        csv_file.flush()
