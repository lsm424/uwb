'''
Author: wadesmli
Date: 2024-05-18 14:43:49
LastEditTime: 2024-09-05 20:52:05
Description: 
'''
import os
from common.common import config, logger
import sys
import signal
from uwb.uwb import Uwb


def uwb_run(sensor_queue, tof_queue):
    from uwb.uwb import Uwb
    global uwb
    uwb = Uwb(sensor_queue, tof_queue)
    uwb.join()


def on_app_exit(uwb=None):
    logger.info(f"应用程序退出")
    if uwb:
        uwb.exit()


def signal_handler(Signal, Frame):
    # 在这里处理Ctrl+C被按下后的逻辑
    print(Signal, Frame)
    print(f"Ctrl+C被按下 {os.getpid()}")
    pid = int(open('uwb.dat', 'r').read())
    # os.kill(os.getpid(), signal.SIGTERM)
    os.kill(pid, signal.SIGTERM)
    os.kill(os.getpid(), signal.SIGTERM)

    # if uwb:
    #     print("uwb退出")
    #     uwb.exit()


# 设置信号处理程序
signal.signal(signal.SIGINT, signal_handler)

if __name__ == '__main__':
    global uwb
    # freeze_support()
    uwb = Uwb()
    # signal.signal(signal.SIGINT, lambda sig, frame: on_app_exit(uwb))
    # signal.signal(signal.SIGINT, lambda sig, frame: on_app_exit(uwb))

    if config['gui']:
        from PySide6.QtWidgets import QApplication
        from gui.mainwinow import MainWindow
        app = QApplication(sys.argv)
        app.lastWindowClosed.connect(lambda: on_app_exit(uwb))
        mainWindow = MainWindow(uwb)
        mainWindow.show()
        sys.exit(app.exec())
    else:
        uwb.join()
