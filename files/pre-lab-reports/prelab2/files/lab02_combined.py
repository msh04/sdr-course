#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Lab 2: Pluto TX and RX
# Author: Group 6
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
from gnuradio import blocks
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import iio
import math
import sip
import threading



class lab02_combined(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Lab 2: Pluto TX and RX", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Lab 2: Pluto TX and RX")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_combined")

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
        self.tx_atten = tx_atten = 89.75
        self.mode = mode = 0
        self.tx_atten_safe = tx_atten_safe = max(tx_atten, 30.0 if mode == 1 else 18.0)
        self.samp_rate = samp_rate = 2400000
        self.p_max = p_max = 7.0
        self.a_tone = a_tone = 0
        self.a_pad = a_pad = 0.5
        self.a_noise = a_noise = 0
        self.rf_gain = rf_gain = 40
        self.p_tone_est = p_tone_est = ((p_max + 20*math.log10(a_tone/(2 if mode == 3 else 1)) - tx_atten_safe - a_pad) if (a_tone > 0 and mode >= 2) else float('-inf'))
        self.f_noise = f_noise = -700e3
        self.f_c = f_c = 434.0e6
        self.f2 = f2 = 400e3
        self.f1 = f1 = 300e3
        self.enr_est = enr_est = ((p_max + 20*math.log10(a_noise) - 10*math.log10(samp_rate) - a_pad + 174 - tx_atten_safe) if (a_noise > 0 and mode == 1) else float('-inf'))
        self.display_tx_atten = display_tx_atten = tx_atten_safe
        self.bw_tone = bw_tone = 10e3
        self.bw_noise = bw_noise = 400e3

        ##################################################
        # Blocks
        ##################################################

        self._rf_gain_range = qtgui.Range(0, 50, 1, 40, 200)
        self._rf_gain_win = qtgui.RangeWidget(self._rf_gain_range, self.set_rf_gain, "RF gain of the device under test (dB)", "counter_slider", int, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._rf_gain_win)
        # Create the options list
        self._mode_options = [0, 1, 2, 3]
        # Create the labels list
        self._mode_labels = ['Off (zeros)', 'Gaussian noise', 'One tone', 'Two tones']
        # Create the combo box
        self._mode_tool_bar = Qt.QToolBar(self)
        self._mode_tool_bar.addWidget(Qt.QLabel("Output" + ": "))
        self._mode_combo_box = Qt.QComboBox()
        self._mode_tool_bar.addWidget(self._mode_combo_box)
        for _label in self._mode_labels: self._mode_combo_box.addItem(_label)
        self._mode_callback = lambda i: Qt.QMetaObject.invokeMethod(self._mode_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._mode_options.index(i)))
        self._mode_callback(self.mode)
        self._mode_combo_box.currentIndexChanged.connect(
            lambda i: self.set_mode(self._mode_options[i]))
        # Create the radio buttons
        self.top_layout.addWidget(self._mode_tool_bar)
        self._f_c_range = qtgui.Range(24e6, 1700e6, 1e6, 434.0e6, 200)
        self._f_c_win = qtgui.RangeWidget(self._f_c_range, self.set_f_c, "Centre frequency (Hz)", "counter", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._f_c_win)
        self._a_tone_range = qtgui.Range(0, 0.9, 0.05, 0, 200)
        self._a_tone_win = qtgui.RangeWidget(self._a_tone_range, self.set_a_tone, "Tone amplitude (single / twice per-tone in two-tone mode)", "counter", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._a_tone_win)
        self.tx_spec = qtgui.freq_sink_c(
            2048, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            samp_rate, #bw
            "Baseband spectrum sent to the Pluto", #name
            1,
            None # parent
        )
        self.tx_spec.set_update_time(0.10)
        self.tx_spec.set_y_axis((-200), 0)
        self.tx_spec.set_y_label('Relative Gain', 'dB')
        self.tx_spec.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.tx_spec.enable_autoscale(False)
        self.tx_spec.enable_grid(True)
        self.tx_spec.set_fft_average(0.1)
        self.tx_spec.enable_axis_labels(True)
        self.tx_spec.enable_control_panel(True)
        self.tx_spec.set_fft_window_normalized(False)



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
                self.tx_spec.set_line_label(i, "Data {0}".format(i))
            else:
                self.tx_spec.set_line_label(i, labels[i])
            self.tx_spec.set_line_width(i, widths[i])
            self.tx_spec.set_line_color(i, colors[i])
            self.tx_spec.set_line_alpha(i, alphas[i])

        self._tx_spec_win = sip.wrapinstance(self.tx_spec.qwidget(), Qt.QWidget)
        self.top_layout.addWidget(self._tx_spec_win)
        self._tx_atten_range = qtgui.Range(18, 89.75, 0.25, 89.75, 200)
        self._tx_atten_win = qtgui.RangeWidget(self._tx_atten_range, self.set_tx_atten, "Requested TX attenuation (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._tx_atten_win)
        self.total_rms = blocks.rms_cf((2e-6))
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
        self.tone2 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, f2, ((mode == 3)*(a_tone/2)), 0, 0)
        self.tone1 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, f1, ((mode == 2)*a_tone + (mode == 3)*(a_tone/2)), 0, 0)
        self.t2_rms = blocks.rms_cf((2e-6))
        self.t2_db = blocks.nlog10_ff(20, 1, 0)
        self.t2_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), f2, samp_rate)
        self.t1_rms = blocks.rms_cf((2e-6))
        self.t1_db = blocks.nlog10_ff(20, 1, 0)
        self.t1_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), f1, samp_rate)
        self.src_sum = blocks.add_vcc(1)
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
        self.spec.set_y_axis((-200), 0)
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
        self.pluto_tx = iio.fmcomms2_sink_fc32('' if '' else iio.get_pluto_uri(), [True, True], 32768, False)
        self.pluto_tx.set_len_tag_key('')
        self.pluto_tx.set_bandwidth(int(samp_rate))
        self.pluto_tx.set_frequency(int(f_c))
        self.pluto_tx.set_samplerate(int(samp_rate))
        self.pluto_tx.set_attenuation(0, tx_atten_safe)
        self.pluto_tx.set_filter_params('Off', '', 0, 0)
        self._p_tone_est_tool_bar = Qt.QToolBar(self)

        if lambda x: "%.2f" % x:
            self._p_tone_est_formatter = lambda x: "%.2f" % x
        else:
            self._p_tone_est_formatter = lambda x: eng_notation.num_to_str(x)

        self._p_tone_est_tool_bar.addWidget(Qt.QLabel("Estimated input power per tone (dBm): "))
        self._p_tone_est_label = Qt.QLabel(str(self._p_tone_est_formatter(self.p_tone_est)))
        self._p_tone_est_tool_bar.addWidget(self._p_tone_est_label)
        self.top_layout.addWidget(self._p_tone_est_tool_bar)
        self.noise_rms = blocks.rms_cf((2e-6))
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
        self.noise = analog.noise_source_c(analog.GR_GAUSSIAN, ((mode == 1)*a_noise), 0)
        self.im_lo_rms = blocks.rms_cf((2e-6))
        self.im_lo_db = blocks.nlog10_ff(20, 1, 0)
        self.im_lo_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f1 - f2), samp_rate)
        self.im_hi_rms = blocks.rms_cf((2e-6))
        self.im_hi_db = blocks.nlog10_ff(20, 1, 0)
        self.im_hi_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f2 - f1), samp_rate)
        self.iio_pluto_source_0 = iio.fmcomms2_source_fc32('' if '' else iio.get_pluto_uri(), [True, True], 32768)
        self.iio_pluto_source_0.set_len_tag_key('packet_len')
        self.iio_pluto_source_0.set_frequency(int(f_c))
        self.iio_pluto_source_0.set_samplerate(int(samp_rate))
        self.iio_pluto_source_0.set_gain_mode(0, 'manual')
        self.iio_pluto_source_0.set_gain(0, int(rf_gain))
        self.iio_pluto_source_0.set_quadrature(True)
        self.iio_pluto_source_0.set_rfdc(True)
        self.iio_pluto_source_0.set_bbdc(True)
        self.iio_pluto_source_0.set_filter_params('Off', '', 0, 0)
        self._enr_est_tool_bar = Qt.QToolBar(self)

        if lambda x: "%.2f" % x:
            self._enr_est_formatter = lambda x: "%.2f" % x
        else:
            self._enr_est_formatter = lambda x: eng_notation.num_to_str(x)

        self._enr_est_tool_bar.addWidget(Qt.QLabel("Estimated ENR (dB): "))
        self._enr_est_label = Qt.QLabel(str(self._enr_est_formatter(self.enr_est)))
        self._enr_est_tool_bar.addWidget(self._enr_est_label)
        self.top_layout.addWidget(self._enr_est_tool_bar)
        self._display_tx_atten_tool_bar = Qt.QToolBar(self)

        if lambda x: "%.2f" % x:
            self._display_tx_atten_formatter = lambda x: "%.2f" % x
        else:
            self._display_tx_atten_formatter = lambda x: eng_notation.num_to_str(x)

        self._display_tx_atten_tool_bar.addWidget(Qt.QLabel("Applied TX attenuation (dB): "))
        self._display_tx_atten_label = Qt.QLabel(str(self._display_tx_atten_formatter(self.display_tx_atten)))
        self._display_tx_atten_tool_bar.addWidget(self._display_tx_atten_label)
        self.top_layout.addWidget(self._display_tx_atten_tool_bar)
        self._a_noise_range = qtgui.Range(0, 0.01, 0.001, 0, 200)
        self._a_noise_win = qtgui.RangeWidget(self._a_noise_range, self.set_a_noise, "Noise RMS amplitude", "counter", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._a_noise_win)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.iio_pluto_source_0, 0), (self.im_hi_band, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.im_lo_band, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.noise_band, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.spec, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.t1_band, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.t2_band, 0))
        self.connect((self.iio_pluto_source_0, 0), (self.total_rms, 0))
        self.connect((self.im_hi_band, 0), (self.im_hi_rms, 0))
        self.connect((self.im_hi_db, 0), (self.tone_num, 3))
        self.connect((self.im_hi_rms, 0), (self.im_hi_db, 0))
        self.connect((self.im_lo_band, 0), (self.im_lo_rms, 0))
        self.connect((self.im_lo_db, 0), (self.tone_num, 2))
        self.connect((self.im_lo_rms, 0), (self.im_lo_db, 0))
        self.connect((self.noise, 0), (self.src_sum, 2))
        self.connect((self.noise_band, 0), (self.noise_rms, 0))
        self.connect((self.noise_db, 0), (self.noise_num, 0))
        self.connect((self.noise_rms, 0), (self.noise_db, 0))
        self.connect((self.src_sum, 0), (self.pluto_tx, 0))
        self.connect((self.src_sum, 0), (self.tx_spec, 0))
        self.connect((self.t1_band, 0), (self.t1_rms, 0))
        self.connect((self.t1_db, 0), (self.tone_num, 0))
        self.connect((self.t1_rms, 0), (self.t1_db, 0))
        self.connect((self.t2_band, 0), (self.t2_rms, 0))
        self.connect((self.t2_db, 0), (self.tone_num, 1))
        self.connect((self.t2_rms, 0), (self.t2_db, 0))
        self.connect((self.tone1, 0), (self.src_sum, 0))
        self.connect((self.tone2, 0), (self.src_sum, 1))
        self.connect((self.total_log, 0), (self.total_num, 0))
        self.connect((self.total_rms, 0), (self.total_log, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab02_combined")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_tx_atten(self):
        return self.tx_atten

    def set_tx_atten(self, tx_atten):
        self.tx_atten = tx_atten
        self.set_tx_atten_safe(max(self.tx_atten, 30.0 if self.mode == 1 else 18.0))

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        self.mode = mode
        self._mode_callback(self.mode)
        self.noise.set_amplitude(((self.mode == 1)*self.a_noise))
        self.tone1.set_amplitude(((self.mode == 2)*self.a_tone + (self.mode == 3)*(self.a_tone/2)))
        self.tone2.set_amplitude(((self.mode == 3)*(self.a_tone/2)))
        self.set_tx_atten_safe(max(self.tx_atten, 30.0 if self.mode == 1 else 18.0))
        self.set_p_tone_est(((self.p_max + 20*math.log10(self.a_tone/(2 if self.mode == 3 else 1)) - self.tx_atten_safe - self.a_pad) if (self.a_tone > 0 and self.mode >= 2) else float('-inf')))
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_tx_atten_safe(self):
        return self.tx_atten_safe

    def set_tx_atten_safe(self, tx_atten_safe):
        self.tx_atten_safe = tx_atten_safe
        self.pluto_tx.set_attenuation(0,self.tx_atten_safe)
        self.set_display_tx_atten(self.tx_atten_safe)
        self.set_p_tone_est(((self.p_max + 20*math.log10(self.a_tone/(2 if self.mode == 3 else 1)) - self.tx_atten_safe - self.a_pad) if (self.a_tone > 0 and self.mode >= 2) else float('-inf')))
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.iio_pluto_source_0.set_samplerate(int(self.samp_rate))
        self.im_hi_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_lo_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.noise_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_noise/2, self.bw_noise/4))
        self.pluto_tx.set_bandwidth(int(self.samp_rate))
        self.pluto_tx.set_samplerate(int(self.samp_rate))
        self.spec.set_frequency_range(0, self.samp_rate)
        self.t1_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t2_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.tone1.set_sampling_freq(self.samp_rate)
        self.tone2.set_sampling_freq(self.samp_rate)
        self.tx_spec.set_frequency_range(0, self.samp_rate)
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_p_max(self):
        return self.p_max

    def set_p_max(self, p_max):
        self.p_max = p_max
        self.set_p_tone_est(((self.p_max + 20*math.log10(self.a_tone/(2 if self.mode == 3 else 1)) - self.tx_atten_safe - self.a_pad) if (self.a_tone > 0 and self.mode >= 2) else float('-inf')))
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_a_tone(self):
        return self.a_tone

    def set_a_tone(self, a_tone):
        self.a_tone = a_tone
        self.tone1.set_amplitude(((self.mode == 2)*self.a_tone + (self.mode == 3)*(self.a_tone/2)))
        self.tone2.set_amplitude(((self.mode == 3)*(self.a_tone/2)))
        self.set_p_tone_est(((self.p_max + 20*math.log10(self.a_tone/(2 if self.mode == 3 else 1)) - self.tx_atten_safe - self.a_pad) if (self.a_tone > 0 and self.mode >= 2) else float('-inf')))

    def get_a_pad(self):
        return self.a_pad

    def set_a_pad(self, a_pad):
        self.a_pad = a_pad
        self.set_p_tone_est(((self.p_max + 20*math.log10(self.a_tone/(2 if self.mode == 3 else 1)) - self.tx_atten_safe - self.a_pad) if (self.a_tone > 0 and self.mode >= 2) else float('-inf')))
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_a_noise(self):
        return self.a_noise

    def set_a_noise(self, a_noise):
        self.a_noise = a_noise
        self.noise.set_amplitude(((self.mode == 1)*self.a_noise))
        self.set_enr_est(((self.p_max + 20*math.log10(self.a_noise) - 10*math.log10(self.samp_rate) - self.a_pad + 174 - self.tx_atten_safe) if (self.a_noise > 0 and self.mode == 1) else float('-inf')))

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.iio_pluto_source_0.set_gain(0, int(self.rf_gain))

    def get_p_tone_est(self):
        return self.p_tone_est

    def set_p_tone_est(self, p_tone_est):
        self.p_tone_est = p_tone_est
        Qt.QMetaObject.invokeMethod(self._p_tone_est_label, "setText", Qt.Q_ARG("QString", str(self._p_tone_est_formatter(self.p_tone_est))))

    def get_f_noise(self):
        return self.f_noise

    def set_f_noise(self, f_noise):
        self.f_noise = f_noise
        self.noise_band.set_center_freq(self.f_noise)

    def get_f_c(self):
        return self.f_c

    def set_f_c(self, f_c):
        self.f_c = f_c
        self.iio_pluto_source_0.set_frequency(int(self.f_c))
        self.pluto_tx.set_frequency(int(self.f_c))

    def get_f2(self):
        return self.f2

    def set_f2(self, f2):
        self.f2 = f2
        self.im_hi_band.set_center_freq((2*self.f2 - self.f1))
        self.im_lo_band.set_center_freq((2*self.f1 - self.f2))
        self.t2_band.set_center_freq(self.f2)
        self.tone2.set_frequency(self.f2)

    def get_f1(self):
        return self.f1

    def set_f1(self, f1):
        self.f1 = f1
        self.im_hi_band.set_center_freq((2*self.f2 - self.f1))
        self.im_lo_band.set_center_freq((2*self.f1 - self.f2))
        self.t1_band.set_center_freq(self.f1)
        self.tone1.set_frequency(self.f1)

    def get_enr_est(self):
        return self.enr_est

    def set_enr_est(self, enr_est):
        self.enr_est = enr_est
        Qt.QMetaObject.invokeMethod(self._enr_est_label, "setText", Qt.Q_ARG("QString", str(self._enr_est_formatter(self.enr_est))))

    def get_display_tx_atten(self):
        return self.display_tx_atten

    def set_display_tx_atten(self, display_tx_atten):
        self.display_tx_atten = display_tx_atten
        Qt.QMetaObject.invokeMethod(self._display_tx_atten_label, "setText", Qt.Q_ARG("QString", str(self._display_tx_atten_formatter(self.display_tx_atten))))

    def get_bw_tone(self):
        return self.bw_tone

    def set_bw_tone(self, bw_tone):
        self.bw_tone = bw_tone
        self.im_hi_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_lo_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t1_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t2_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))

    def get_bw_noise(self):
        return self.bw_noise

    def set_bw_noise(self, bw_noise):
        self.bw_noise = bw_noise
        self.noise_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_noise/2, self.bw_noise/4))




def main(top_block_cls=lab02_combined, options=None):

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
