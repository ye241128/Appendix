import sys
import time
import threading
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSpinBox, QGridLayout
)
from PyQt5.QtCore import QTimer
import pyqtgraph as pg
import numpy as np

class OscilloscopeMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADC Monitor (UI显示=电压 -1.5V)")
        self.setGeometry(100, 100, 1200, 1000)
        
        from ExpanderPi import ADC
        self.adc = ADC()
        
        self.adc_rate = 500
        self.running = False
        self.first_timestamp = None  
        
        self.sample_count = 0
        self.last_sample_time = None
        self.actual_rate = 0.0

        self.setup_ui()
        self.maxlen = 300
        self.global_block_t = deque(maxlen=self.maxlen)   
        self.global_block_1 = deque(maxlen=self.maxlen)  
        self.global_block_2 = deque(maxlen=self.maxlen)  
        self.global_block_diff = deque(maxlen=self.maxlen)

        self.data_lock = threading.Lock()
        self.acquisition_thread = None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(1000)

    def setup_ui(self):
        """构建界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        control_panel = QHBoxLayout()
        
        adc_group = QGroupBox("ADC Settings")
        adc_layout = QGridLayout()
    
        adc_layout.addWidget(QLabel("ADC Channel 1:"), 0, 0)
        self.adc_channel1 = QSpinBox()
        self.adc_channel1.setRange(1, 8)
        self.adc_channel1.setValue(7)
        adc_layout.addWidget(self.adc_channel1, 0, 1)
        
        adc_layout.addWidget(QLabel("ADC Channel 2:"), 1, 0)
        self.adc_channel2 = QSpinBox()
        self.adc_channel2.setRange(1, 8)
        self.adc_channel2.setValue(8)
        adc_layout.addWidget(self.adc_channel2, 1, 1)
        
        adc_layout.addWidget(QLabel("Measurement Mode:"), 2, 0)
        self.adc_mode = QComboBox()
        self.adc_mode.addItems(['Single-ended', 'Differential'])
        self.adc_mode.currentIndexChanged.connect(self.on_mode_change)
        adc_layout.addWidget(self.adc_mode, 2, 1)
        
        self.adc_value1 = QLabel("ADC1: 0.000 V")
        self.adc_value2 = QLabel("ADC2: 0.000 V")
        self.adc_value_diff = QLabel("Differential: 0.000 V")
        adc_layout.addWidget(self.adc_value1, 3, 0, 1, 2)
        adc_layout.addWidget(self.adc_value2, 4, 0, 1, 2)
        adc_layout.addWidget(self.adc_value_diff, 5, 0, 1, 2)

        self.freq_label1_fft = QLabel("Freq1 (FFT): 0.0 Hz")
        self.freq_label2_fft = QLabel("Freq2 (FFT): 0.0 Hz")
        self.freq_label_diff_fft = QLabel("Freq Diff (FFT): 0.0 Hz")

        row = 6
        adc_layout.addWidget(self.freq_label1_fft, row + 0, 0, 1, 2)
        adc_layout.addWidget(self.freq_label2_fft, row + 1, 0, 1, 2)
        adc_layout.addWidget(self.freq_label_diff_fft, row + 2, 0, 1, 2)

        adc_group.setLayout(adc_layout)
        control_panel.addWidget(adc_group)

        rate_group = QGroupBox("Sampling Rate Control")
        rate_layout = QGridLayout()
        
        rate_layout.addWidget(QLabel("Target ADC Sampling Rate (Hz):"), 0, 0)
        self.adc_rate_spin = QSpinBox()
        self.adc_rate_spin.setRange(1, 100000)
        self.adc_rate_spin.setValue(500)
        self.adc_rate_spin.valueChanged.connect(
            lambda x: setattr(self, 'adc_rate', x)
        )
        rate_layout.addWidget(self.adc_rate_spin, 0, 1)
        
        rate_layout.addWidget(QLabel("Actual Sampling Rate:"), 1, 0)
        self.actual_rate_label = QLabel("0.0 Hz")
        rate_layout.addWidget(self.actual_rate_label, 1, 1)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_running)
        rate_layout.addWidget(self.start_button, 2, 0, 1, 2)
        
        rate_group.setLayout(rate_layout)
        control_panel.addWidget(rate_group)
        
        main_layout.addLayout(control_panel)
        plot_layout = QVBoxLayout()

        self.plot_widget1 = pg.PlotWidget()
        self.plot_widget1.setBackground('k')
        self.plot_widget1.setLabel('left', "ADC1 Voltage (V, after -1.5)")
        self.plot_widget1.setLabel('bottom', "Time (s)")
        self.plot_widget1.showGrid(x=True, y=True)
        self.plot_widget1.setYRange(-1.5, 2.6)
        self.curve1 = self.plot_widget1.plot(pen=None, symbol='o', symbolSize=3,
                                             symbolBrush='y', symbolPen='y')
        plot_layout.addWidget(self.plot_widget1)
        
        self.plot_widget2 = pg.PlotWidget()
        self.plot_widget2.setBackground('k')
        self.plot_widget2.setLabel('left', "ADC2 Voltage (V, after -1.5)")
        self.plot_widget2.setLabel('bottom', "Time (s)")
        self.plot_widget2.showGrid(x=True, y=True)
        self.plot_widget2.setYRange(-1.5, 2.6)
        self.curve2 = self.plot_widget2.plot(pen=None, symbol='o', symbolSize=3,
                                             symbolBrush='g', symbolPen='g')
        plot_layout.addWidget(self.plot_widget2)
        
        self.plot_widget_diff = pg.PlotWidget()
        self.plot_widget_diff.setBackground('k')
        self.plot_widget_diff.setLabel('left', "Differential (V)")
        self.plot_widget_diff.setLabel('bottom', "Time (s)")
        self.plot_widget_diff.showGrid(x=True, y=True)
        self.plot_widget_diff.setYRange(-4.0, 4.0)
        self.curve_diff = self.plot_widget_diff.plot(pen=None, symbol='o', 
                                                     symbolSize=3,
                                                     symbolBrush='r', 
                                                     symbolPen='r')
        plot_layout.addWidget(self.plot_widget_diff)
        
        main_layout.addLayout(plot_layout)
        
        self.setup_plots_sync()

        if self.adc_mode.currentIndex() == 0:  
            self.plot_widget_diff.setVisible(False)
            self.adc_value_diff.setVisible(False)
            self.freq_label_diff_fft.setVisible(False)

    def setup_plots_sync(self):
        """同步三个图的 X 轴缩放/平移"""
        self.plot_widget1.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget1, [self.plot_widget2, self.plot_widget_diff])
        )
        self.plot_widget2.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget2, [self.plot_widget1, self.plot_widget_diff])
        )
        self.plot_widget_diff.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget_diff, [self.plot_widget1, self.plot_widget2])
        )

    def sync_range(self, source, targets):
        x_range = source.viewRange()[0]
        for t in targets:
            t.setXRange(*x_range, padding=0)

    def on_mode_change(self, index):
        """单端 / 差分模式下，决定是否隐藏第三图"""
        if index == 0:  
            self.plot_widget_diff.setVisible(False)
            self.adc_value_diff.setVisible(False)
            self.freq_label_diff_fft.setVisible(False)
        else:           # Differential
            self.plot_widget_diff.setVisible(True)
            self.adc_value_diff.setVisible(True)
            self.freq_label_diff_fft.setVisible(True)

    def toggle_running(self):
        """启动/停止采集线程"""
        if not self.running:
            self.running = True
            self.start_button.setText("Stop")
            self.first_timestamp = None  
            
            self.sample_count = 0
            self.last_sample_time = None
            self.actual_rate = 0.0
            
            with self.data_lock:
                self.global_block_t.clear()
                self.global_block_1.clear()
                self.global_block_2.clear()
                self.global_block_diff.clear()

            self.acquisition_thread = threading.Thread(
                target=self.acquisition_loop, daemon=True
            )
            self.acquisition_thread.start()
        else:
            self.running = False
            self.start_button.setText("Start")

    def acquisition_loop(self):
        
        next_sample_time = time.perf_counter()
        
        while self.running:
            now = time.perf_counter()
         
            if now < next_sample_time:
                time.sleep(next_sample_time - now)

          
            real_t = time.perf_counter()

        
            if self.first_timestamp is None:
                self.first_timestamp = real_t
                self.last_sample_time = real_t
            else:
                self.last_sample_time = real_t
            
          
            normalized_t = real_t - self.first_timestamp
            
          
            self.sample_count += 1
            
            if normalized_t > 0:
                self.actual_rate = self.sample_count / normalized_t

            ch1 = self.adc_channel1.value()
            ch2 = self.adc_channel2.value()

            code_v1 = self.adc.read_adc_voltage(ch1, 0)  # 0~4.096
            code_v2 = self.adc.read_adc_voltage(ch2, 0)

            real_v1 = code_v1 - 1.5
            real_v2 = code_v2 - 1.5

            if self.adc_mode.currentIndex() == 1:  
                diff_v = real_v1 - real_v2
            else:
                diff_v = 0.0

            with self.data_lock:
                self.global_block_t.append(normalized_t)
                self.global_block_1.append(real_v1)
                self.global_block_2.append(real_v2)
                self.global_block_diff.append(diff_v)

            next_sample_time += 1.0 / self.adc_rate

    def update_plot(self):
        with self.data_lock:
            if not self.global_block_t:
                return
            data_t    = np.array(self.global_block_t) 
            data1     = np.array(self.global_block_1)
            data2     = np.array(self.global_block_2)
            data_diff = np.array(self.global_block_diff)

        self.curve1.setData(x=data_t, y=data1)
        self.curve2.setData(x=data_t, y=data2)
        self.curve_diff.setData(x=data_t, y=data_diff)

        if len(data1) > 0:
            self.adc_value1.setText(f"ADC1: {data1[-1]:.3f} V")
            self.adc_value2.setText(f"ADC2: {data2[-1]:.3f} V")
            self.adc_value_diff.setText(f"Differential: {data_diff[-1]:.3f} V")

        freq1_fft = self.measure_frequency_fft(data_t, data1)
        freq2_fft = self.measure_frequency_fft(data_t, data2)
        freq_d_fft = 0.0

        if self.adc_mode.currentIndex() == 1:
            freq_d_fft = self.measure_frequency_fft(data_t, data_diff)

        # 更新频率显示 (FFT)
        self.freq_label1_fft.setText(f"Freq1 (FFT): {freq1_fft:.2f} Hz")
        self.freq_label2_fft.setText(f"Freq2 (FFT): {freq2_fft:.2f} Hz")
        self.freq_label_diff_fft.setText(f"Freq Diff (FFT): {freq_d_fft:.2f} Hz")
        
        # =============== 更新实际采样率 ===============
        self.actual_rate_label.setText(f"{self.actual_rate:.2f} Hz")

        # 自动范围 X 轴
        self.plot_widget1.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
        self.plot_widget2.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
        self.plot_widget_diff.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)

    def measure_frequency_fft(self, data_t, data_y):
       
        n = len(data_y)
        if n < 4:
            return 0.0

        t_min = data_t[0]  
        t_max = data_t[-1]
        duration = t_max - t_min
        if duration <= 0:
            return 0.0

        fs_est = (n - 1) / duration
        
        y_centered = data_y - np.mean(data_y)
        window = np.hanning(n)
        y_win = y_centered * window
        
        Y = np.fft.rfft(y_win)
        freqs = np.fft.rfftfreq(n, d=1.0/fs_est)
        mag = np.abs(Y)
        
        idx_max = np.argmax(mag)
        peak_freq = freqs[idx_max]
        return peak_freq

    def closeEvent(self, event):
        self.running = False
        time.sleep(0.5)  
        event.accept()

def main():
    app = QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    window = OscilloscopeMonitor()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
