import os
import time
from common.common import config, logger
import sys
from multiprocessing import Process, Queue, freeze_support
from gui.sensor300d import Sensor300dWidght
from gui.tof2011 import Tof2011Widght
import signal
from uwb.uwb import Uwb


def uwb_run(sensor_queue, tof_queue):
    from uwb.uwb import Uwb
    global uwb
    uwb = Uwb(sensor_queue, tof_queue)
    signal.signal(signal.SIGINT, lambda sig, frame: on_app_exit(uwb))
    uwb.join()


def on_app_exit(uwb=None):
    logger.info(f"应用程序退出")
    if uwb:
        uwb.exit()


if __name__ == '__main__':
    # freeze_support()
    global uwb

    if config['gui']:
        # uwb = Uwb(Sensor300dWidght.gui_queue, Tof2011Widght.gui_queue)
        p = Process(target=uwb_run, args=(
            Sensor300dWidght.gui_queue, Tof2011Widght.gui_queue))
        p.start()
        from PySide6.QtWidgets import QApplication
        from gui.mainwinow import MainWindow
        app = QApplication(sys.argv)
        app.lastWindowClosed.connect(lambda: os.kill(p.pid, signal.SIGTERM))
        mainWindow = MainWindow()
        mainWindow.show()
        sys.exit(app.exec())
    else:
        uwb_run(None, None)
