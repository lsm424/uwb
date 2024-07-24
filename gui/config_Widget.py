# encoding=utf-8
import serial.tools.list_ports
from common.common import config, logger, update_yaml
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QLineEdit, QGridLayout, QMessageBox, QPushButton, QRadioButton

from uwb.uwb import Uwb


class ConfigWidget(QWidget):
    def __init__(self, uwb: Uwb):
        super().__init__()
        self.uwb = uwb
        self.vbox = QVBoxLayout()
        self.main_box = QHBoxLayout(self)
        self.main_box.addLayout(self.vbox)

        # 创建两个RadioButton
        self.radio_udp = QRadioButton("udp")
        self.radio_serial = QRadioButton("串口")
        self.vbox.addWidget(self.radio_udp)
        self.vbox.addWidget(self.radio_serial)

        # 创建一个按钮和一个框架，初始时隐藏
        self.button = QPushButton("更新配置")
        self.button.clicked.connect(self.handle_update_config)
        self.vbox.addWidget(self.button)

        self.serial_Widget = SerialConfig()
        self.serial_Widget.setVisible(False)
        self.main_box.addWidget(self.serial_Widget)
        self.udp_Widget = UdpConfig()
        self.udp_Widget.setVisible(False)
        self.main_box.addWidget(self.udp_Widget)

        # 选择第一个RadioButton为默认选中
        if config['access_type'] == 'udp':
            self.radio_udp.setChecked(True)
            self.udp_Widget.setVisible(True)
            self.radio_udp.setText('udp（当前）')
        elif config['access_type'] == 'serial':
            self.radio_serial.setChecked(True)
            self.serial_Widget.setVisible(True)
            self.radio_serial.setText("串口（当前）")

        else:
            QMessageBox.warning(self, 'Warning', f'不支持的通讯方式：{config["access_type"]}，请修改配置后重启')
            return

        # 连接信号槽
        self.radio_udp.toggled.connect(self.handleRadioToggle)
        self.radio_serial.toggled.connect(self.handleRadioToggle)

        # 设置窗口的大小和标题
        self.setGeometry(300, 300, 300, 200)
        self.show()

    def handle_update_config(self):
        if self.radio_serial.isChecked():
            if self.serial_Widget.update_serial(self.uwb.reset_access):
                self.radio_serial.setText("串口（当前）")
                self.radio_udp.setText('udp')
        elif self.radio_udp.isChecked():
            if self.udp_Widget.update_port(self.uwb.reset_access):
                self.radio_serial.setText("串口")
                self.radio_udp.setText('udp（当前）')

    def handleRadioToggle(self):
        # 检查两个RadioButton的状态，并相应地显示或隐藏按钮和框架
        if self.radio_serial.isChecked():
            self.serial_Widget.setVisible(True)
            self.udp_Widget.setVisible(False)
        elif self.radio_udp.isChecked():
            self.udp_Widget.setVisible(True)
            self.serial_Widget.setVisible(False)


class UdpConfig(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout(self)
        self.layout.addWidget(QLabel("端口号："))
        self.port_linedit = QLineEdit(str(config["udp_port"]))
        self.layout.addWidget(self.port_linedit)

    def update_port(self, update_access_func):
        port = self.port_linedit.text()
        try:
            port = int(port)
            if port < 0 or port > 65535:
                raise BaseException("端口号范围：0-65535")
        except BaseException as e:
            QMessageBox.warning(self, 'Warning', f'端口号错误 {e}，请重新修改')
            return False

        config['access_type'] = 'udp'
        config["udp_port"] = port
        update_yaml()
        update_access_func()
        QMessageBox.warning(self, 'Warning', f'udp配置更新成功')
        return True


class PortComboBox(QComboBox):
    """
    重写 QComboBox 
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.update()

    def showPopup(self):
        self.update()
        # 调用原始的 showPopup 方法来显示下拉列表
        super().showPopup()

    def update(self):
        self.clear()
        ports = set(map(lambda x: x.device, serial.tools.list_ports.comports()))
        ports.add(str(config['serial']['port']))
        sorted(ports)
        self.addItems(ports)
        self.setCurrentText(config['serial']['port'])


class SerialConfig(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QGridLayout(self)

        self.layout.addWidget(QLabel("端口号："), 0, 0)
        self.port = PortComboBox()
        self.layout.addWidget(self.port, 0, 1)

        self.layout.addWidget(QLabel("波特率："), 1, 0)
        self.baudrate_lineedit = QLineEdit(str(config['serial']['baudrate']))
        self.layout.addWidget(self.baudrate_lineedit, 1, 1)

        self.layout.addWidget(QLabel('数据位：'), 2, 0)
        bytesize = [serial.EIGHTBITS, serial.SEVENBITS, serial.SIXBITS, serial.FIVEBITS]
        self.bytesize = QComboBox()
        self.bytesize.addItems(list(map(lambda x: str(x), bytesize)))
        if config['serial']['bytesize'] not in bytesize:
            QMessageBox.warning(self, 'Warning', f"数据位配置{config['serial']['bytesize']}错误，请更新配置重启")
            return
        self.bytesize.setCurrentText(str(config['serial']['bytesize']))
        self.layout.addWidget(self.bytesize, 2, 1)

        self.layout.addWidget(QLabel('校验位：'), 3, 0)
        parity = [serial.PARITY_NONE, serial.PARITY_EVEN, serial.PARITY_ODD, serial.PARITY_MARK, serial.PARITY_SPACE]
        self.parity = QComboBox()
        self.parity.addItems(parity)
        if config['serial']['parity'] not in parity:
            QMessageBox.warning(self, 'Warning', f"校验位配置{config['serial']['parity']}错误，请更新配置重启")
            return
        self.bytesize.setCurrentText(str(config['serial']['parity']))
        self.layout.addWidget(self.parity, 3, 1)

        self.layout.addWidget(QLabel('停止位：'), 4, 0)
        stop = [serial.STOPBITS_ONE, serial.STOPBITS_ONE_POINT_FIVE, serial.STOPBITS_TWO]
        self.stop = QComboBox()
        self.stop.addItems(list(map(lambda x: str(x), stop)))
        if config['serial']['stopbits'] not in stop:
            QMessageBox.warning(self, 'Warning', f"停止位配置{config['serial']['stopbits']}错误，请更新配置重启")
            return
        self.bytesize.setCurrentText(str(config['serial']['stopbits']))
        self.layout.addWidget(self.stop, 4, 1)

    def update_serial(self, update_access_func):
        port = self.port.currentText()
        baudrate = self.baudrate_lineedit.text()
        try:
            baudrate = int(baudrate)
            if baudrate <= 0:
                raise BaseException("波特率小于0")
        except BaseException as e:
            QMessageBox.warning(self, 'Warning', f'波特率设置错误 {e}')
            return False

        baudrate = self.baudrate_lineedit.text()
        try:
            baudrate = int(baudrate)
            if baudrate <= 0:
                raise BaseException("波特率小于0")
        except BaseException as e:
            QMessageBox.warning(self, 'Warning', f'波特率设置错误 {e}')
            return False

        config['access_type'] = 'serial'
        config['serial']['port'] = port
        config['serial']['bytesize'] = int(self.bytesize.currentText())
        config['serial']['parity'] = self.parity.currentText()
        config['serial']['stopbits'] = float(self.stop.currentText())
        config['serial']['baudrate'] = baudrate
        update_yaml()
        update_access_func()
        QMessageBox.warning(self, 'Warning', f'串口配置更新成功')
        return True
