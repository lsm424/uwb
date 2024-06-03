import time
from common.common import config, logger
import sys
from multiprocessing import Process, Queue
from gui.sensor300d import Sensor300dWidght
from gui.tof2011 import Tof2011Widght

def uwb_run(sensor_queue, tof_queue):
    from uwb.uwb import Uwb
    uwb = Uwb(sensor_queue, tof_queue)
    uwb.join()


if __name__ == '__main__':
    if config['gui']:
        p = Process(target=uwb_run, args=(Sensor300dWidght.gui_queue, Tof2011Widght.gui_queue))
        p.start()
        from PySide6.QtWidgets import QApplication
        from gui.mainwinow import MainWindow
        app = QApplication(sys.argv)
        mainWindow = MainWindow()
        mainWindow.show()
        sys.exit(app.exec())
    else:
        uwb_run(Sensor300dWidght.gui_queue, Tof2011Widght.gui_queue)