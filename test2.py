import sys
import random
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class RealTimePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)

        # 创建一个 Figure 对象
        self.figure = Figure()

        # 在 Figure 上添加两个子图，2行1列
        self.ax1 = self.figure.add_subplot(211)
        self.ax2 = self.figure.add_subplot(212)
        # 创建两个 FigureCanvas 用于显示 Figure 中的两个子图
        self.canvas = FigureCanvas(self.figure)
        self.layout.addWidget(self.canvas)

        # 初始化数据
        self.x_data = []
        self.y1_data = []
        self.y2_data = []

        # 绘制两条初始曲线
        self.line1 = list(map(lambda x: self.ax1.plot([], [])[0], range(4)))  # self.ax1.plot(self.x_data, self.y1_data, label='Line 1')
        self.line2 = list(map(lambda x: self.ax2.plot([], [])[0], range(4)))  # self.ax2.plot(self.x_data, self.y2_data, label='Line 2')

        # 设置图例
        # self.ax1.legend()
        # self.ax2.legend()

        # 定时器，每隔一段时间更新图表
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)  # 每1000毫秒（1秒）更新一次

    def update_plot(self):
        # 模拟数据更新
        self.x_data.append(len(self.x_data) + 1)
        self.y1_data.append([random.randint(0, 10), random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)])
        self.y2_data.append([random.randint(0, 10), random.randint(0, 10), random.randint(0, 10), random.randint(0, 10)])

        # self.x_data.append(len(self.x_data) + 1)
        # self.y1_data.append(random.randint(0, 10))
        # self.y2_data.append(random.randint(0, 10))

        y_data = list(zip(*self.y1_data))
        # 更新每条曲线的数据
        for i, y in enumerate(y_data):
            self.lines[i].set_xdata(self.x_data)
            self.lines[i].set_ydata(y)
            self.lines2[i].set_xdata(self.x_data)
            self.lines2[i].set_ydata(y)

        # 更新曲线数据
        # self.line1.set_xdata(self.x_data)
        # self.line1.set_ydata(self.y1_data)
        # self.line2.set_xdata(self.x_data)
        # self.line2.set_ydata(self.y2_data)

        # 自动调整坐标轴范围
        self.ax1.relim()
        self.ax1.autoscale_view()
        self.ax2.relim()
        self.ax2.autoscale_view()

        # 刷新画布
        self.canvas.draw()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Real-Time Plot with PyQt and Matplotlib')
        self.setGeometry(100, 100, 800, 600)

        # 创建一个 RealTimePlot 实例
        self.realtime_plot = RealTimePlot(self)
        self.setCentralWidget(self.realtime_plot)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())
