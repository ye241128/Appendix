import sys
import time
import math
import threading
from collections import deque

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QLabel, QSpinBox, QDoubleSpinBox, QGridLayout,
    QCheckBox
)
from PyQt5.QtCore import QTimer, Qt
import pyqtgraph as pg
import numpy as np  

class ADCDACMonitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ADC/DAC Monitor")
        self.setGeometry(100, 100, 1200, 1000)
        
        
        from ExpanderPi import DAC, ADC
        self.dac = DAC(gainFactor=2)
        self.adc = ADC()
        
        self.dac_rate = 500   
        self.adc_rate = 500  
        self.running = False
        
        
        self.dac_diff_mode = False  
        
        
        self.setup_ui()

        
        self.maxlen = 1000
        self.global_block_t    = deque(maxlen=self.maxlen)
        self.global_block_1    = deque(maxlen=self.maxlen)  
        self.global_block_2    = deque(maxlen=self.maxlen)
        self.global_block_diff = deque(maxlen=self.maxlen)
        self.data_lock = threading.Lock()
        self.acquisition_thread = None
  
        self.ui_update_counter = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)
        
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        
        control_panel = QHBoxLayout()
        
      
        dac_group = QGroupBox("DAC Waveform Control")
        dac_layout = QGridLayout()
        
       
        dac_layout.addWidget(QLabel("Channel 1:"), 0, 0)
        self.wave_type1 = QComboBox()
        self.wave_type1.addItems(['Sine Wave', 'Square Wave', 'Triangle Wave', 'Sawtooth Wave'])
        dac_layout.addWidget(self.wave_type1, 0, 1)
        
        self.freq1 = QDoubleSpinBox()
        self.freq1.setRange(0.1, 10000)
        self.freq1.setValue(10)
        dac_layout.addWidget(QLabel("Frequency 1 (Hz):"), 1, 0)
        dac_layout.addWidget(self.freq1, 1, 1)
        
        self.amp1 = QDoubleSpinBox()
        self.amp1.setRange(0, 2)
        self.amp1.setValue(1)
        dac_layout.addWidget(QLabel("Amplitude 1 (V, peak):"), 2, 0)
        dac_layout.addWidget(self.amp1, 2, 1)
        
        self.offset1 = QDoubleSpinBox()
        self.offset1.setRange(-1.5, 2.6)
        self.offset1.setValue(0.0)
        dac_layout.addWidget(QLabel("Offset 1 (V):"), 3, 0)
        dac_layout.addWidget(self.offset1, 3, 1)
                
        dac_layout.addWidget(QLabel("Channel 2:"), 4, 0)
        self.wave_type2 = QComboBox()
        self.wave_type2.addItems(['Sine Wave', 'Square Wave', 'Triangle Wave', 'Sawtooth Wave'])
        dac_layout.addWidget(self.wave_type2, 4, 1)
        
        self.freq2 = QDoubleSpinBox()
        self.freq2.setRange(0.1, 10000)
        self.freq2.setValue(200)
        dac_layout.addWidget(QLabel("Frequency 2 (Hz):"), 5, 0)
        dac_layout.addWidget(self.freq2, 5, 1)
        
        self.amp2 = QDoubleSpinBox()
        self.amp2.setRange(0, 2)
        self.amp2.setValue(1)
        dac_layout.addWidget(QLabel("Amplitude 2 (V, peak):"), 6, 0)
        dac_layout.addWidget(self.amp2, 6, 1)
        
        self.offset2 = QDoubleSpinBox()
        self.offset2.setRange(-1.5, 2.6)
        self.offset2.setValue(0.0)
        dac_layout.addWidget(QLabel("Offset 2 (V):"), 7, 0)
        dac_layout.addWidget(self.offset2, 7, 1)
        
        
        self.dac_diff_checkbox = QCheckBox("DAC Differential output")
        self.dac_diff_checkbox.stateChanged.connect(self.on_dac_diff_mode_changed)
        dac_layout.addWidget(self.dac_diff_checkbox, 8, 0, 1, 2)

        dac_group.setLayout(dac_layout)
        control_panel.addWidget(dac_group)
        
        
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

       
        self.freq_label1_fft = QLabel("Freq1 (FFT): 0.00 Hz")
        self.freq_label2_fft = QLabel("Freq2 (FFT): 0.00 Hz")
        self.freq_label_diff_fft = QLabel("Freq Diff (FFT): 0.00 Hz")

        row_start = 6
        adc_layout.addWidget(self.freq_label1_fft,    row_start+0, 0, 1, 2)
        adc_layout.addWidget(self.freq_label2_fft,    row_start+1, 0, 1, 2)
        adc_layout.addWidget(self.freq_label_diff_fft, row_start+2, 0, 1, 2)

        adc_group.setLayout(adc_layout)
        control_panel.addWidget(adc_group)
        
         
        rate_group = QGroupBox("Sampling Rate Control")
        rate_layout = QGridLayout()
        
        rate_layout.addWidget(QLabel("DAC Update Rate (Hz):"), 0, 0)
        self.dac_rate_spin = QSpinBox()
        self.dac_rate_spin.setRange(1, 100000)
        self.dac_rate_spin.setValue(500)
        self.dac_rate_spin.valueChanged.connect(lambda x: setattr(self, 'dac_rate', x))
        rate_layout.addWidget(self.dac_rate_spin, 0, 1)
        
        rate_layout.addWidget(QLabel("ADC Sampling Rate (Hz):"), 1, 0)
        self.adc_rate_spin = QSpinBox()
        self.adc_rate_spin.setRange(1, 100000)
        self.adc_rate_spin.setValue(500)
        self.adc_rate_spin.valueChanged.connect(lambda x: setattr(self, 'adc_rate', x))
        rate_layout.addWidget(self.adc_rate_spin, 1, 1)
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.toggle_running)
        rate_layout.addWidget(self.start_button, 2, 0, 1, 2)
        
        rate_group.setLayout(rate_layout)
        control_panel.addWidget(rate_group)
        
        main_layout.addLayout(control_panel)
        
        
        plot_layout = QVBoxLayout()

        # Plot 1: ADC1
        self.plot_widget1 = pg.PlotWidget()
        self.plot_widget1.setBackground('k')
        self.plot_widget1.setLabel('left', "ADC1 Voltage (V, after -1.5)")
        self.plot_widget1.setLabel('bottom', "Time (s)")
        self.plot_widget1.showGrid(x=True, y=True)
        self.plot_widget1.setYRange(-1.5, 2.6)
        self.curve1 = self.plot_widget1.plot(pen=None, symbol='o', symbolSize=3,
                                             symbolBrush='y', symbolPen='y')
        plot_layout.addWidget(self.plot_widget1)
        
        # Plot 2: ADC2
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


    def on_dac_diff_mode_changed(self, state):
        self.dac_diff_mode = (state == Qt.Checked)
       
        enable_ch2 = not self.dac_diff_mode
        self.wave_type2.setEnabled(enable_ch2)
        self.freq2.setEnabled(enable_ch2)
        self.amp2.setEnabled(enable_ch2)
        self.offset2.setEnabled(enable_ch2)

    def setup_plots_sync(self):
        
        self.plot_widget1.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget1, [self.plot_widget2, self.plot_widget_diff]))
        self.plot_widget2.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget2, [self.plot_widget1, self.plot_widget_diff]))
        self.plot_widget_diff.sigRangeChanged.connect(
            lambda: self.sync_range(self.plot_widget_diff, [self.plot_widget1, self.plot_widget2]))

    def sync_range(self, source, targets):
        x_range = source.viewRange()[0]
        for t in targets:
            t.setXRange(*x_range, padding=0)

    def on_mode_change(self, index):
       
        if index == 0:  # Single-ended
            self.plot_widget_diff.setVisible(False)
            self.adc_value_diff.setVisible(False)
            self.freq_label_diff_fft.setVisible(False)
        else:           # Differential
            self.plot_widget_diff.setVisible(True)
            self.adc_value_diff.setVisible(True)
            self.freq_label_diff_fft.setVisible(True)

    def toggle_running(self):
        
        if not self.running:
            self.running = True
            self.start_button.setText("Stop")
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
        
        sample_index = 0
        while self.running:
            t0 = time.perf_counter()
            t = sample_index / float(self.dac_rate)
            sample_index += 1

          
            real_val1 = self.generate_real_wave(
                self.wave_type1.currentText(),
                self.freq1.value(),
                self.amp1.value(),
                self.offset1.value(),
                t
            )
            code_val1 = max(0, min(4.096, real_val1))
            self.dac.set_dac_voltage(1, code_val1)

            
            if self.dac_diff_mode:
                
                offset1 = self.offset1.value()
                mirror_val2 = 2 * offset1 - real_val1
                code_val2 = max(0, min(4.096, mirror_val2))
            else:
                real_val2 = self.generate_real_wave(
                    self.wave_type2.currentText(),
                    self.freq2.value(),
                    self.amp2.value(),
                    self.offset2.value(),
                    t
                )
                code_val2 = max(0, min(4.096, real_val2))
            self.dac.set_dac_voltage(2, code_val2)
             
            ch1 = self.adc_channel1.value()
            ch2 = self.adc_channel2.value()
            code_v1 = self.adc.read_adc_voltage(ch1, 0)
            code_v2 = self.adc.read_adc_voltage(ch2, 0)
            real_v1 = code_v1 - 1.5
            real_v2 = code_v2 - 1.5
            diff_v = real_v1 - real_v2 if self.adc_mode.currentIndex() == 1 else 0.0

           
            with self.data_lock:
                self.global_block_t.append(t)
                self.global_block_1.append(real_v1)
                self.global_block_2.append(real_v2)
                self.global_block_diff.append(diff_v)
            
            
            elapsed = time.perf_counter() - t0
            period = 1.0 / self.dac_rate
            to_sleep = period - elapsed
            if to_sleep > 0:
                time.sleep(to_sleep)

    def generate_real_wave(self, wave_type, freq, amplitude, offset, t):
        
        if wave_type == 'Sine Wave':
            w = amplitude * math.sin(2 * math.pi * freq * t)
        elif wave_type == 'Square Wave':
            w = amplitude * (1 if math.sin(2 * math.pi * freq * t) >= 0 else -1)
        elif wave_type == 'Triangle Wave':
            f_mod = (t * freq) % 1.0
            w = (4 * f_mod - 1) if f_mod < 0.5 else (3 - 4 * f_mod)
            w *= amplitude
        else:  # Sawtooth Wave
            f_mod = (t * freq) % 1.0
            w = (2 * f_mod - 1) * amplitude
        return w + offset

    def measure_frequency_fft(self, data_t, data_y):
        
        n = len(data_y)
        if n < 4:
            return 0.0
        duration = data_t[-1] - data_t[0]
        if duration <= 0:
            return 0.0
        fs_est = (n - 1) / duration
        y_centered = data_y - np.mean(data_y)
        window = np.hanning(n)
        Y = np.fft.rfft(y_centered * window)
        freqs = np.fft.rfftfreq(n, d=1.0/fs_est)
        mag = np.abs(Y)
        return freqs[np.argmax(mag)]

    def update_plot(self):
        
        self.ui_update_counter += 1
        with self.data_lock:
            
            local_t = self.global_block_t
            local_1 = self.global_block_1
            local_2 = self.global_block_2
            local_diff = self.global_block_diff
            self.global_block_t = deque(maxlen=self.maxlen)
            self.global_block_1 = deque(maxlen=self.maxlen)
            self.global_block_2 = deque(maxlen=self.maxlen)
            self.global_block_diff = deque(maxlen=self.maxlen)

        if not local_t:
            return

        data_t    = np.array(local_t, dtype=float)
        data1     = np.array(local_1, dtype=float)
        data2     = np.array(local_2, dtype=float)
        data_diff = np.array(local_diff, dtype=float)

        
        self.curve1.setData(x=data_t, y=data1)
        self.curve2.setData(x=data_t, y=data2)
        self.curve_diff.setData(x=data_t, y=data_diff)

        
        if len(data1) > 0:
            self.adc_value1.setText(f"ADC1: {data1[-1]:.3f} V")
            self.adc_value2.setText(f"ADC2: {data2[-1]:.3f} V")
            self.adc_value_diff.setText(f"Differential: {data_diff[-1]:.3f} V")

       
        if self.ui_update_counter % 2 == 0:
            freq1_fft = self.measure_frequency_fft(data_t, data1)
            freq2_fft = self.measure_frequency_fft(data_t, data2)
            freq_diff_fft = self.measure_frequency_fft(data_t, data_diff) if self.adc_mode.currentIndex() == 1 else 0.0

            self.freq_label1_fft.setText(f"Freq1 (FFT): {freq1_fft:.2f} Hz")
            self.freq_label2_fft.setText(f"Freq2 (FFT): {freq2_fft:.2f} Hz")
            self.freq_label_diff_fft.setText(f"Freq Diff (FFT): {freq_diff_fft:.2f} Hz")
        
       
        self.plot_widget1.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
        self.plot_widget2.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)
        self.plot_widget_diff.enableAutoRange(axis=pg.ViewBox.XAxis, enable=True)

    def closeEvent(self, event):
    
        self.running = False
        time.sleep(0.5)
        event.accept()

def main():
    app = QApplication(sys.argv)
    pg.setConfigOptions(antialias=True)
    window = ADCDACMonitor()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
