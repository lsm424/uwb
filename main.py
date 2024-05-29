import time
from common.common import config
from uwb.uwb import Uwb
import sys

if __name__ == '__main__':
    uwb = Uwb()
    if config['gui']:
        from PySide6.QtWidgets import QApplication
        from gui.mainwinow import MainWindow
        app = QApplication(sys.argv)
        mainWindow = MainWindow()
        mainWindow.show()
        sys.exit(app.exec())
    else:
        while True:
            time.sleep(10)