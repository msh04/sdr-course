#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Lab02 - receive-only RF measurements
# Author: SDR Lab
# Description: RTLSDR preparation; set center_freq and supported gain for actual hardware; AGC off
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import soapy
import math
import sip
import threading



class lab02_meas(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Lab02 - receive-only RF measurements", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Lab02 - receive-only RF measurements")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_meas")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)
        self.flowgraph_started = threading.Event()

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 2.048e6
        self.gain = gain = 0
        self.freq_error_hz = freq_error_hz = 0
        self.f_noise = f_noise = -500e3
        self.f2 = f2 = 400e3
        self.f1 = f1 = 300e3
        self.center_freq = center_freq = 100e6
        self.bw_tone = bw_tone = 10e3
        self.bw_noise = bw_noise = 400e3

        ##################################################
        # Blocks
        ##################################################

        self._gain_range = qtgui.Range(0, 50, 1, 0, 200)
        self._gain_win = qtgui.RangeWidget(self._gain_range, self.set_gain, "Manual RF gain (dB); AGC off", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_win)
        self.total_rms = blocks.rms_cf((1e-4))
        self.total_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.total_num.set_update_time(0.10)
        self.total_num.set_title("Total level (dBFS)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['dB', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.total_num.set_min(i, -100)
            self.total_num.set_max(i, 0)
            self.total_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.total_num.set_label(i, "Data {0}".format(i))
            else:
                self.total_num.set_label(i, labels[i])
            self.total_num.set_unit(i, units[i])
            self.total_num.set_factor(i, factor[i])

        self.total_num.enable_autoscale(False)
        self._total_num_win = sip.wrapinstance(self.total_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._total_num_win)
        self.total_log = blocks.nlog10_ff(20, 1, 0)
        self.tone_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_NONE,
            4,
            None # parent
        )
        self.tone_num.set_update_time(0.10)
        self.tone_num.set_title("Tone meters (10 kHz each)")

        labels = ["f1 (dBFS)", "f2 (dBFS)", "2 f1 - f2 (dBFS)", "2 f2 - f1 (dBFS)", '',
            '', '', '', '', '']
        units = ['', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(4):
            self.tone_num.set_min(i, -140)
            self.tone_num.set_max(i, 0)
            self.tone_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.tone_num.set_label(i, "Data {0}".format(i))
            else:
                self.tone_num.set_label(i, labels[i])
            self.tone_num.set_unit(i, units[i])
            self.tone_num.set_factor(i, factor[i])

        self.tone_num.enable_autoscale(False)
        self._tone_num_win = sip.wrapinstance(self.tone_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._tone_num_win)
        self.t2_rms = blocks.rms_cf((1e-3))
        self.t2_db = blocks.nlog10_ff(20, 1, 0)
        self.t2_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), f2, samp_rate)
        self.t1_rms = blocks.rms_cf((1e-3))
        self.t1_db = blocks.nlog10_ff(20, 1, 0)
        self.t1_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), f1, samp_rate)
        self.spec = qtgui.freq_sink_c(
            4096, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Spectrum at the receiver output", #name
            1,
            None # parent
        )
        self.spec.set_update_time(0.10)
        self.spec.set_y_axis((-140), 0)
        self.spec.set_y_label('Relative Gain', 'dB')
        self.spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.spec.enable_autoscale(False)
        self.spec.enable_grid(True)
        self.spec.set_fft_average(0.05)
        self.spec.enable_axis_labels(True)
        self.spec.enable_control_panel(True)
        self.spec.set_fft_window_normalized(False)



        labels = ['', '', '', '', '',
            '', '', '', '', '']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ["blue", "red", "green", "black", "cyan",
            "magenta", "yellow", "dark red", "dark green", "dark blue"]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.spec.set_line_label(i, labels[i])
            self.spec.set_line_width(i, widths[i])
            self.spec.set_line_color(i, colors[i])
            self.spec.set_line_alpha(i, alphas[i])

        self._spec_win = sip.wrapinstance(self.spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._spec_win)
        self.rtl_source = None
        dev = 'driver=rtlsdr'
        stream_args = 'bufflen=16384'
        tune_args = ['']
        settings = ['']

        def _set_rtl_source_gain_mode(channel, agc):
            self.rtl_source.set_gain_mode(channel, agc)
            if not agc:
                  self.rtl_source.set_gain(channel, self._rtl_source_gain_value)
        self.set_rtl_source_gain_mode = _set_rtl_source_gain_mode

        def _set_rtl_source_gain(channel, name, gain):
            self._rtl_source_gain_value = gain
            if not self.rtl_source.get_gain_mode(channel):
                self.rtl_source.set_gain(channel, gain)
        self.set_rtl_source_gain = _set_rtl_source_gain

        def _set_rtl_source_bias(bias):
            if 'biastee' in self._rtl_source_setting_keys:
                self.rtl_source.write_setting('biastee', bias)
        self.set_rtl_source_bias = _set_rtl_source_bias

        self.rtl_source = soapy.source(dev, "fc32", 1, '',
                                  stream_args, tune_args, settings)

        self._rtl_source_setting_keys = [a.key for a in self.rtl_source.get_setting_info()]

        self.rtl_source.set_sample_rate(0, samp_rate)
        self.rtl_source.set_frequency(0, center_freq)
        self.rtl_source.set_frequency_correction(0, 0)
        self.set_rtl_source_bias(bool(False))
        self._rtl_source_gain_value = gain
        self.set_rtl_source_gain_mode(0, bool(False))
        self.set_rtl_source_gain(0, 'TUNER', gain)
        self.noise_rms = blocks.rms_cf((2e-5))
        self.noise_num = qtgui.number_sink(
            gr.sizeof_float,
            0,
            qtgui.NUM_GRAPH_HORIZ,
            1,
            None # parent
        )
        self.noise_num.set_update_time(0.10)
        self.noise_num.set_title("Noise power in the 400 kHz band (dBFS)")

        labels = ['', '', '', '', '',
            '', '', '', '', '']
        units = ['dBFS', '', '', '', '',
            '', '', '', '', '']
        colors = [("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"),
            ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black"), ("black", "black")]
        factor = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]

        for i in range(1):
            self.noise_num.set_min(i, -120)
            self.noise_num.set_max(i, 0)
            self.noise_num.set_color(i, colors[i][0], colors[i][1])
            if len(labels[i]) == 0:
                self.noise_num.set_label(i, "Data {0}".format(i))
            else:
                self.noise_num.set_label(i, labels[i])
            self.noise_num.set_unit(i, units[i])
            self.noise_num.set_factor(i, factor[i])

        self.noise_num.enable_autoscale(False)
        self._noise_num_win = sip.wrapinstance(self.noise_num.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._noise_num_win)
        self.noise_db = blocks.nlog10_ff(20, 1, 0)
        self.noise_band = filter.freq_xlating_fir_filter_ccf(4, firdes.low_pass(1, samp_rate, bw_noise/2, bw_noise/4), f_noise, samp_rate)
        self.im_lo_rms = blocks.rms_cf((1e-3))
        self.im_lo_db = blocks.nlog10_ff(20, 1, 0)
        self.im_lo_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f1 - f2), samp_rate)
        self.im_hi_rms = blocks.rms_cf((1e-3))
        self.im_hi_db = blocks.nlog10_ff(20, 1, 0)
        self.im_hi_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f2 - f1), samp_rate)
        self.fine_rotator = blocks.rotator_cc((-2*math.pi*freq_error_hz/samp_rate), False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.fine_rotator, 0), (self.im_hi_band, 0))
        self.connect((self.fine_rotator, 0), (self.im_lo_band, 0))
        self.connect((self.fine_rotator, 0), (self.noise_band, 0))
        self.connect((self.fine_rotator, 0), (self.spec, 0))
        self.connect((self.fine_rotator, 0), (self.t1_band, 0))
        self.connect((self.fine_rotator, 0), (self.t2_band, 0))
        self.connect((self.fine_rotator, 0), (self.total_rms, 0))
        self.connect((self.im_hi_band, 0), (self.im_hi_rms, 0))
        self.connect((self.im_hi_db, 0), (self.tone_num, 3))
        self.connect((self.im_hi_rms, 0), (self.im_hi_db, 0))
        self.connect((self.im_lo_band, 0), (self.im_lo_rms, 0))
        self.connect((self.im_lo_db, 0), (self.tone_num, 2))
        self.connect((self.im_lo_rms, 0), (self.im_lo_db, 0))
        self.connect((self.noise_band, 0), (self.noise_rms, 0))
        self.connect((self.noise_db, 0), (self.noise_num, 0))
        self.connect((self.noise_rms, 0), (self.noise_db, 0))
        self.connect((self.rtl_source, 0), (self.fine_rotator, 0))
        self.connect((self.t1_band, 0), (self.t1_rms, 0))
        self.connect((self.t1_db, 0), (self.tone_num, 0))
        self.connect((self.t1_rms, 0), (self.t1_db, 0))
        self.connect((self.t2_band, 0), (self.t2_rms, 0))
        self.connect((self.t2_db, 0), (self.tone_num, 1))
        self.connect((self.t2_rms, 0), (self.t2_db, 0))
        self.connect((self.total_log, 0), (self.total_num, 0))
        self.connect((self.total_rms, 0), (self.total_log, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_meas")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.noise_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_noise/2, self.bw_noise/4))
        self.t1_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t2_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_lo_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_hi_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.spec.set_frequency_range(0, self.samp_rate)
        self.rtl_source.set_sample_rate(0, self.samp_rate)
        self.fine_rotator.set_phase_inc((-2*math.pi*self.freq_error_hz/self.samp_rate))

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.set_rtl_source_gain(0, 'TUNER', self.gain)

    def get_freq_error_hz(self):
        return self.freq_error_hz

    def set_freq_error_hz(self, freq_error_hz):
        self.freq_error_hz = freq_error_hz
        self.fine_rotator.set_phase_inc((-2*math.pi*self.freq_error_hz/self.samp_rate))

    def get_f_noise(self):
        return self.f_noise

    def set_f_noise(self, f_noise):
        self.f_noise = f_noise
        self.noise_band.set_center_freq(self.f_noise)

    def get_f2(self):
        return self.f2

    def set_f2(self, f2):
        self.f2 = f2
        self.t2_band.set_center_freq(self.f2)
        self.im_lo_band.set_center_freq((2*self.f1 - self.f2))
        self.im_hi_band.set_center_freq((2*self.f2 - self.f1))

    def get_f1(self):
        return self.f1

    def set_f1(self, f1):
        self.f1 = f1
        self.t1_band.set_center_freq(self.f1)
        self.im_lo_band.set_center_freq((2*self.f1 - self.f2))
        self.im_hi_band.set_center_freq((2*self.f2 - self.f1))

    def get_center_freq(self):
        return self.center_freq

    def set_center_freq(self, center_freq):
        self.center_freq = center_freq
        self.rtl_source.set_frequency(0, self.center_freq)

    def get_bw_tone(self):
        return self.bw_tone

    def set_bw_tone(self, bw_tone):
        self.bw_tone = bw_tone
        self.t1_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t2_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_lo_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_hi_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))

    def get_bw_noise(self):
        return self.bw_noise

    def set_bw_noise(self, bw_noise):
        self.bw_noise = bw_noise
        self.noise_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_noise/2, self.bw_noise/4))




def main(top_block_cls=lab02_meas, options=None):

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls()

    tb.start()
    tb.flowgraph_started.set()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
