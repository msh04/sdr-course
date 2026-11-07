#!/usr/bin/env python3
"""GNU Radio 3.10 / PyQt5 simulation; no SDR required.
RF-equivalent mapping: f_sim = (f_RF - 1300 MHz) / 2000.
A +/-250 kHz low-pass represents an 800--1800 MHz RF band-pass.
"""
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PyQt5'
import sys
import time
import signal
import threading
import numpy as np
from PyQt5 import QtCore, QtWidgets
import pyqtgraph as pg
from gnuradio import gr, analog, blocks, filter
from gnuradio.filter import firdes

FS = 2_000_000
RF_CENTER = 1_300_000_000
SCALE = 2000.0
AMPLITUDE = 0.5
SETTLE = 0.25
WINDOW_SECONDS = 0.10


class PowerMeter(gr.sync_block):
    def __init__(self):
        gr.sync_block.__init__(self, name='Power meter',
                               in_sig=[np.complex64], out_sig=None)
        self.guard = threading.Lock()
        self.after = float('inf')
        self.total = 0.0
        self.count = 0

    def reset(self, after):
        with self.guard:
            self.after = after
            self.total = 0.0
            self.count = 0

    def result(self):
        with self.guard:
            return self.total, self.count

    def work(self, input_items, output_items):
        x = input_items[0]
        with self.guard:
            if time.monotonic() >= self.after:
                self.total += float(np.vdot(x, x).real)
                self.count += len(x)
        return len(x)


class FilterSimulation(gr.top_block, QtWidgets.QWidget):
    def __init__(self):
        gr.top_block.__init__(self, 'Simulated RF filter', catch_exceptions=True)
        QtWidgets.QWidget.__init__(self)
        self.setWindowTitle('800–1800 MHz filter — software simulation')
        self.resize(1100, 720)
        self.points = {}
        self.running_sweep = False
        self.started = False
        self.closed = False
        self.rf_hz = 400e6

        layout = QtWidgets.QVBoxLayout(self)
        description = QtWidgets.QLabel(
            'No SDR required. A frequency-shifted/scaled low-pass models an '
            '800–1800 MHz band-pass. Passband-edge transition regions are finite. '
            'Displayed frequencies are RF-equivalent, not actual sample frequencies.')
        description.setWordWrap(True)
        layout.addWidget(description)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)
        self.frequency = QtWidgets.QDoubleSpinBox()
        self.frequency.setRange(400, 3000)
        self.frequency.setDecimals(1)
        self.frequency.setSingleStep(10)
        self.frequency.setValue(400)
        self.frequency.setSuffix(' MHz')
        form.addRow('Manual RF-equivalent frequency:', self.frequency)
        self.step = QtWidgets.QDoubleSpinBox()
        self.step.setRange(1, 500)
        self.step.setValue(20)
        self.step.setSuffix(' MHz')
        form.addRow('Sweep step:', self.step)
        self.maxhold = QtWidgets.QCheckBox('Max Hold at each frequency')
        form.addRow(self.maxhold)
        row = QtWidgets.QHBoxLayout()
        layout.addLayout(row)
        self.start_button = QtWidgets.QPushButton('Start sweep: 400–3000 MHz')
        self.stop_button = QtWidgets.QPushButton('Stop')
        self.clear_button = QtWidgets.QPushButton('Clear')
        self.save_button = QtWidgets.QPushButton('Save CSV')
        for b in (self.start_button, self.stop_button, self.clear_button, self.save_button):
            row.addWidget(b)
        self.plot = pg.PlotWidget(title='Simulated filter transmission response')
        self.plot.setLabel('bottom', 'RF-equivalent frequency', units='MHz')
        self.plot.setLabel('left', 'Output / input power', units='dB')
        self.plot.showGrid(x=True, y=True)
        self.plot.setXRange(400, 3000, padding=0)
        self.plot.setYRange(-120, 5)
        for edge in (800, 1800):
            self.plot.addItem(pg.InfiniteLine(pos=edge, angle=90,
                              pen=pg.mkPen('#66aaaa', style=QtCore.Qt.DashLine)))
        self.curve = self.plot.plot(pen=pg.mkPen('y', width=2),
                                   symbol='o', symbolSize=4)
        layout.addWidget(self.plot)
        self.status = QtWidgets.QLabel('Starting simulation…')
        layout.addWidget(self.status)

        self.source = analog.sig_source_c(FS, analog.GR_SIN_WAVE,
                                          self.to_sim(self.rf_hz), AMPLITUDE, 0, 0)
        self.throttle = blocks.throttle(gr.sizeof_gr_complex, FS, True)
        # Hamming FIR: cutoff at +/-250 kHz; transition width 25 kHz.
        # RF-equivalent cutoff edges: 800 and 1800 MHz.
        # RF-equivalent transition width: approximately 50 MHz.
        taps = firdes.low_pass(1.0, FS, 250_000, 25_000)
        self.digital_filter = filter.fir_filter_ccf(1, taps)
        self.meter = PowerMeter()
        self.connect(self.source, self.throttle, self.digital_filter, self.meter)
        # Small buffers reduce old-frequency data remaining after retuning.
        self.source.set_max_output_buffer(8192)
        self.throttle.set_max_output_buffer(8192)
        self.digital_filter.set_max_output_buffer(8192)

        self.frequency.valueChanged.connect(self.tune)
        self.start_button.clicked.connect(self.start_sweep)
        self.stop_button.clicked.connect(self.stop_sweep)
        self.clear_button.clicked.connect(self.clear)
        self.save_button.clicked.connect(self.save_csv)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_measurement)
        self.timer.start(50)

    @staticmethod
    def to_sim(rf_hz):
        return (rf_hz - RF_CENTER) / SCALE

    def arm(self):
        self.ready_after = time.monotonic() + SETTLE
        self.meter.reset(self.ready_after)
        self.status.setText(f'Settling at {self.rf_hz / 1e6:.1f} MHz RF-equivalent…')

    def begin(self):
        self.start()
        self.started = True
        self.arm()

    def tune(self, mhz):
        self.meter.reset(float('inf'))
        self.rf_hz = round(mhz * 1e6)
        self.source.set_frequency(self.to_sim(self.rf_hz))
        self.arm()

    def record_response(self, rf_hz, db):
        if self.maxhold.isChecked():
            db = max(self.points.get(rf_hz, -np.inf), db)
        self.points[rf_hz] = db
        frequencies = sorted(self.points)
        self.curve.setData(np.array(frequencies) / 1e6,
                           [self.points[f] for f in frequencies])

    def update_measurement(self):
        if not self.started or time.monotonic() < self.ready_after:
            return
        total, count = self.meter.result()
        if count < int(FS * WINDOW_SECONDS):
            return
        ratio = (total / count) / (AMPLITUDE ** 2)
        db = 10.0 * np.log10(max(ratio, 1e-30))
        self.record_response(self.rf_hz, db)
        self.status.setText(
            f'RF-equivalent: {self.rf_hz / 1e6:.1f} MHz | '
            f'Simulated tone: {self.to_sim(self.rf_hz) / 1e3:.1f} kHz | '
            f'Response: {db:.2f} dB | Points: {len(self.points)}')
        if self.running_sweep:
            if self.rf_hz >= 3e9:
                self.stop_sweep()
                self.status.setText('Sweep complete. Save CSV to export the response.')
            else:
                next_hz = min(3e9, self.rf_hz + round(self.step.value() * 1e6))
                self.frequency.setValue(next_hz / 1e6)
        else:
            self.ready_after = time.monotonic()
            self.meter.reset(self.ready_after)

    def start_sweep(self):
        self.running_sweep = True
        for w in (self.frequency, self.step, self.start_button):
            w.setEnabled(False)
        self.clear()
        self.frequency.setValue(400)
        self.arm()

    def stop_sweep(self):
        self.running_sweep = False
        for w in (self.frequency, self.step, self.start_button):
            w.setEnabled(True)

    def clear(self):
        self.points.clear()
        self.curve.setData([], [])
        self.arm()

    def save_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save simulated response', 'filter_simulation.csv', 'CSV (*.csv)')
        if path:
            data = np.array(sorted(self.points.items()), dtype=float).reshape(-1, 2)
            np.savetxt(path, data, delimiter=',',
                       header='rf_equivalent_frequency_hz,response_db', comments='')
            self.status.setText(f'Saved: {path}')

    def closeEvent(self, event):
        if not self.closed:
            self.closed = True
            self.timer.stop()
            if self.started:
                self.stop()
                self.wait()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = FilterSimulation()
    window.show()
    window.begin()
    signal.signal(signal.SIGINT, lambda *_: window.close())
    signal.signal(signal.SIGTERM, lambda *_: window.close())
    heartbeat = QtCore.QTimer()
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(500)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
