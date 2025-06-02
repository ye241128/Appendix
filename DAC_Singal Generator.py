import sys
import time
import math
import numpy as np
import threading
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QGroupBox, QGridLayout, QLabel, QDoubleSpinBox,
    QSpinBox, QPushButton, QComboBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from ExpanderPi import DAC


class WaveformGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
        self.params = {
            'running': False,
            'sample_rate': 10000,    
            'diff_mode': False       
        }
        
        self.sample_count = 0
        self.sample_start_time = time.time()
        self.actual_sample_rate = 0
        
        self.dac = DAC(gainFactor=2)
        self.wave_thread = threading.Thread(target=self.update_wave)
        self.wave_thread.daemon = True  
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_actual_rate_display)
        self.update_timer.start(1000) 
        
    def initUI(self):
        self.setWindowTitle('Signal Generator')
        self.setGeometry(100, 100, 400, 400)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
    
        group1 = QGroupBox('Channel 1')
        group1_layout = QGridLayout()
        
        self.wave_type1 = QComboBox()
        self.wave_type1.addItems([
            'Sine', 
            'Square',
            'Triangle'
        ])
        
        self.freq1 = QDoubleSpinBox()
        self.freq1.setRange(0.1, 8000)
        self.freq1.setValue(100)
        
        self.amp1 = QDoubleSpinBox()
        self.amp1.setRange(0, 2)
        self.amp1.setValue(1)
        
        self.offset1 = QDoubleSpinBox()
        self.offset1.setRange(0, 4.096)
        self.offset1.setValue(2)
        
        group1_layout.addWidget(QLabel('Waveform:'), 0, 0)
        group1_layout.addWidget(self.wave_type1,          0, 1)
        group1_layout.addWidget(QLabel('FREQUENCY(Hz):'),    1, 0)
        group1_layout.addWidget(self.freq1,               1, 1)
        group1_layout.addWidget(QLabel('AMPLITUDE (V):'),     2, 0)
        group1_layout.addWidget(self.amp1,                2, 1)
        group1_layout.addWidget(QLabel('OFFSET (V):'),     3, 0)
        group1_layout.addWidget(self.offset1,             3, 1)
        
        group1.setLayout(group1_layout)
        layout.addWidget(group1)
        
        
        group2 = QGroupBox('Channel 2')
        group2_layout = QGridLayout()
        
        self.wave_type2 = QComboBox()
        self.wave_type2.addItems([
            'Sine', 
            'Square',
            'Triangle'
        ])
        
        self.wave_type2.setCurrentText('Square')
        
        self.freq2 = QDoubleSpinBox()
        self.freq2.setRange(0.1, 8000)
        self.freq2.setValue(100)
        
        self.amp2 = QDoubleSpinBox()
        self.amp2.setRange(0, 2)
        self.amp2.setValue(1)
        
        self.offset2 = QDoubleSpinBox()
        self.offset2.setRange(0, 4.096)
        self.offset2.setValue(2)
        
        group2_layout.addWidget(QLabel('Waveform:'), 0, 0)
        group2_layout.addWidget(self.wave_type2,          0, 1)
        group2_layout.addWidget(QLabel('FREQUENCY (Hz):'),    1, 0)
        group2_layout.addWidget(self.freq2,               1, 1)
        group2_layout.addWidget(QLabel('AMPLITUDE (V):'),     2, 0)
        group2_layout.addWidget(self.amp2,                2, 1)
        group2_layout.addWidget(QLabel('OFFSET (V):'),     3, 0)
        group2_layout.addWidget(self.offset2,             3, 1)
        
        group2.setLayout(group2_layout)
        layout.addWidget(group2)
        
        
        self.diff_checkbox = QCheckBox("Differential Mode")
        self.diff_checkbox.stateChanged.connect(self.on_diff_mode_changed)
        layout.addWidget(self.diff_checkbox)
        
        
        sample_group = QGroupBox('Sampling Rate')
        sample_layout = QGridLayout()
        
        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(1000, 200000)
        self.sample_rate.setValue(10000)
        self.sample_rate.setSingleStep(1000)
        self.sample_rate.valueChanged.connect(self.update_sample_rate)
        
        
        self.actual_rate_label = QLabel('Actual rate: 0 Hz')
        
        sample_layout.addWidget(QLabel('Target rate (Hz):'), 0, 0)
        sample_layout.addWidget(self.sample_rate,        0, 1)
        sample_layout.addWidget(self.actual_rate_label,  1, 0, 1, 2)
        
        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)
        
        
        self.start_button = QPushButton('Start')
        self.start_button.clicked.connect(self.toggle_output)
        layout.addWidget(self.start_button)
        
    def on_diff_mode_changed(self, state):
       
        self.params['diff_mode'] = (state == Qt.Checked)
        
        
        enabled = not self.params['diff_mode']
        self.wave_type2.setEnabled(enabled)
        self.freq2.setEnabled(enabled)
        self.amp2.setEnabled(enabled)
        self.offset2.setEnabled(enabled)
        
    def update_sample_rate(self):
        self.params['sample_rate'] = self.sample_rate.value()
        
    def update_actual_rate_display(self):
        
        if self.params['running'] and self.sample_count > 0:
            current_time = time.time()
            elapsed = current_time - self.sample_start_time
            if elapsed > 0:
                self.actual_sample_rate = self.sample_count / elapsed
                self.actual_rate_label.setText(f'Actual rate: {self.actual_sample_rate:.1f} Hz')
                
               
                self.sample_count = 0
                self.sample_start_time = current_time
        
    def generate_value(self, wave_type_str, freq, amplitude, offset, t):
        
        wave_type = wave_type_str.split(' ')[0]  
        
        if wave_type == 'Sine':
            val = amplitude * math.sin(2 * math.pi * freq * t) + offset
        elif wave_type == 'Square':
           
            val = amplitude * np.sign(math.sin(2 * math.pi * freq * t)) + offset
        elif wave_type == 'Triangle':
            
            t_norm = (t * freq) % 1.0
            if t_norm < 0.5:
                val = offset + amplitude * (4 * t_norm - 1)
            else:
                val = offset + amplitude * (3 - 4 * t_norm)
        else:  
            val = amplitude * math.sin(2 * math.pi * freq * t) + offset
        
        return val
    
    def update_wave(self):
        
        while True:
            if not self.params['running']:
                time.sleep(0.1)
                continue
            
            sample_period = 1.0 / self.params['sample_rate']
            next_sample_time = time.time() + sample_period
            
         
            t = time.time()
            
            value1 = self.generate_value(
                self.wave_type1.currentText(),
                self.freq1.value(),
                self.amp1.value(),
                self.offset1.value(),
                t
            )
           
            value1 = max(0, min(4.096, value1))
            
           
            if self.params['diff_mode']:
                
                offset1 = self.offset1.value()
                
                mirrored_value2 = 2 * offset1 - value1
                value2 = max(0, min(4.096, mirrored_value2))
            else:
               
                value2 = self.generate_value(
                    self.wave_type2.currentText(),
                    self.freq2.value(),
                    self.amp2.value(),
                    self.offset2.value(),
                    t
                )
                value2 = max(0, min(4.096, value2))
            
           
            self.dac.set_dac_voltage(1, value1)
            self.dac.set_dac_voltage(2, value2)
            

            self.sample_count += 1
            
            sleep_time = next_sample_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def toggle_output(self):

        if not self.params['running']:
           
            self.params['running'] = True
            
            self.sample_count = 0
            self.sample_start_time = time.time()
            
            if not self.wave_thread.is_alive():
                self.wave_thread.start()
            self.start_button.setText('Stop')
        else:
            
            self.params['running'] = False
            self.start_button.setText('Start')
            
    def closeEvent(self, event):

        self.params['running'] = False
        time.sleep(0.2)  
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = WaveformGenerator()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
