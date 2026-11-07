#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: SDR Lab 08 - receiver model: noise figure, P1dB and IIP3 (no hardware)
# Author: SDR Lab
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
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
import math
import sip
import threading



class lab08_sim(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "SDR Lab 08 - receiver model: noise figure, P1dB and IIP3 (no hardware)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("SDR Lab 08 - receiver model: noise figure, P1dB and IIP3 (no hardware)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab08_sim")

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
        self.p_in = p_in = -80
        self.p_fs0 = p_fs0 = -30.0
        self.nf_fe = nf_fe = 6.0
        self.mode = mode = 0
        self.kt0_fs = kt0_fs = 10**((-173.98 + 10*math.log10(samp_rate))/10)
        self.iip3_fe = iip3_fe = -25.0
        self.gain = gain = 40
        self.f_noise = f_noise = -500e3
        self.f2 = f2 = 400e3
        self.f1 = f1 = 300e3
        self.enr_db = enr_db = 15
        self.bw_tone = bw_tone = 10e3
        self.bw_noise = bw_noise = 400e3

        ##################################################
        # Blocks
        ##################################################

        self._p_in_range = qtgui.Range(-110, -10, 0.5, -80, 200)
        self._p_in_win = qtgui.RangeWidget(self._p_in_range, self.set_p_in, "Tone power at the input, per tone (dBm)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._p_in_win)
        # Create the options list
        self._mode_options = [0, 1, 2, 3]
        # Create the labels list
        self._mode_labels = ['Off (50 ohm at 290 K)', 'Noise source on', 'One tone', 'Two tones']
        # Create the combo box
        self._mode_tool_bar = Qt.QToolBar(self)
        self._mode_tool_bar.addWidget(Qt.QLabel("Source" + ": "))
        self._mode_combo_box = Qt.QComboBox()
        self._mode_tool_bar.addWidget(self._mode_combo_box)
        for _label in self._mode_labels: self._mode_combo_box.addItem(_label)
        self._mode_callback = lambda i: Qt.QMetaObject.invokeMethod(self._mode_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._mode_options.index(i)))
        self._mode_callback(self.mode)
        self._mode_combo_box.currentIndexChanged.connect(
            lambda i: self.set_mode(self._mode_options[i]))
        # Create the radio buttons
        self.top_layout.addWidget(self._mode_tool_bar)
        self._gain_range = qtgui.Range(0, 50, 1, 40, 200)
        self._gain_win = qtgui.RangeWidget(self._gain_range, self.set_gain, "Receiver gain (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._gain_win)
        self._enr_db_range = qtgui.Range(0, 60, 1, 15, 200)
        self._enr_db_win = qtgui.RangeWidget(self._enr_db_range, self.set_enr_db, "ENR of the noise source (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._enr_db_win)
        self.zero = analog.sig_source_f(0, analog.GR_CONST_WAVE, 0, 0, 0)
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
        self.tone2 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, f2, ((mode == 3)*math.sqrt(10**(p_in/10))), 0, 0)
        self.tone1 = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, f1, ((mode >= 2)*math.sqrt(10**(p_in/10))), 0, 0)
        self.to_iq = blocks.complex_to_float(1)
        self.throttle = blocks.throttle( gr.sizeof_gr_complex*1, samp_rate, True, 0 if "auto" == "auto" else max( int(float(0.1) * samp_rate) if "auto" == "time" else int(0.1), 1) )
        self.thermal_noise = analog.noise_source_c(analog.GR_GAUSSIAN, (math.sqrt(kt0_fs*(1 + (mode == 1)*10**(enr_db/10)) + kt0_fs*(10**(nf_fe/10) - 1))), 0)
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
        self.scale_q = blocks.multiply_const_ff(127)
        self.scale_i = blocks.multiply_const_ff(127)
        self.rx_gain = blocks.multiply_const_cc(10**((gain - p_fs0)/20))
        self.round_q = blocks.float_to_char(1, 1)
        self.round_i = blocks.float_to_char(1, 1)
        self.one_minus = blocks.add_const_ff(1.0)
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
        self.input_sum = blocks.add_vcc(1)
        self.im_lo_rms = blocks.rms_cf((1e-3))
        self.im_lo_db = blocks.nlog10_ff(20, 1, 0)
        self.im_lo_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f1 - f2), samp_rate)
        self.im_hi_rms = blocks.rms_cf((1e-3))
        self.im_hi_db = blocks.nlog10_ff(20, 1, 0)
        self.im_hi_band = filter.freq_xlating_fir_filter_ccf(64, firdes.low_pass(1, samp_rate, bw_tone/2, bw_tone/2), (2*f2 - f1), samp_rate)
        self.gain_factor = blocks.float_to_complex(1)
        self.front_end = blocks.multiply_vcc(1)
        self.env_power = blocks.complex_to_mag_squared(1)
        self.cubic_coeff = blocks.multiply_const_ff((-1/10**(iip3_fe/10)))
        self.clip_q = analog.rail_ff((-1.0), 1.0)
        self.clip_i = analog.rail_ff((-1.0), 1.0)
        self.back_q = blocks.char_to_float(1, 127)
        self.back_i = blocks.char_to_float(1, 127)
        self.adc_out = blocks.float_to_complex(1)
        self.adc_noise = analog.noise_source_c(analog.GR_GAUSSIAN, (0.5*math.sqrt(2)/127), 1)
        self.adc_input = blocks.add_vcc(1)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.adc_input, 0), (self.to_iq, 0))
        self.connect((self.adc_noise, 0), (self.adc_input, 1))
        self.connect((self.adc_out, 0), (self.im_hi_band, 0))
        self.connect((self.adc_out, 0), (self.im_lo_band, 0))
        self.connect((self.adc_out, 0), (self.noise_band, 0))
        self.connect((self.adc_out, 0), (self.spec, 0))
        self.connect((self.adc_out, 0), (self.t1_band, 0))
        self.connect((self.adc_out, 0), (self.t2_band, 0))
        self.connect((self.adc_out, 0), (self.total_rms, 0))
        self.connect((self.back_i, 0), (self.adc_out, 0))
        self.connect((self.back_q, 0), (self.adc_out, 1))
        self.connect((self.clip_i, 0), (self.scale_i, 0))
        self.connect((self.clip_q, 0), (self.scale_q, 0))
        self.connect((self.cubic_coeff, 0), (self.one_minus, 0))
        self.connect((self.env_power, 0), (self.cubic_coeff, 0))
        self.connect((self.front_end, 0), (self.rx_gain, 0))
        self.connect((self.gain_factor, 0), (self.front_end, 1))
        self.connect((self.im_hi_band, 0), (self.im_hi_rms, 0))
        self.connect((self.im_hi_db, 0), (self.tone_num, 3))
        self.connect((self.im_hi_rms, 0), (self.im_hi_db, 0))
        self.connect((self.im_lo_band, 0), (self.im_lo_rms, 0))
        self.connect((self.im_lo_db, 0), (self.tone_num, 2))
        self.connect((self.im_lo_rms, 0), (self.im_lo_db, 0))
        self.connect((self.input_sum, 0), (self.throttle, 0))
        self.connect((self.noise_band, 0), (self.noise_rms, 0))
        self.connect((self.noise_db, 0), (self.noise_num, 0))
        self.connect((self.noise_rms, 0), (self.noise_db, 0))
        self.connect((self.one_minus, 0), (self.gain_factor, 0))
        self.connect((self.round_i, 0), (self.back_i, 0))
        self.connect((self.round_q, 0), (self.back_q, 0))
        self.connect((self.rx_gain, 0), (self.adc_input, 0))
        self.connect((self.scale_i, 0), (self.round_i, 0))
        self.connect((self.scale_q, 0), (self.round_q, 0))
        self.connect((self.t1_band, 0), (self.t1_rms, 0))
        self.connect((self.t1_db, 0), (self.tone_num, 0))
        self.connect((self.t1_rms, 0), (self.t1_db, 0))
        self.connect((self.t2_band, 0), (self.t2_rms, 0))
        self.connect((self.t2_db, 0), (self.tone_num, 1))
        self.connect((self.t2_rms, 0), (self.t2_db, 0))
        self.connect((self.thermal_noise, 0), (self.input_sum, 2))
        self.connect((self.throttle, 0), (self.env_power, 0))
        self.connect((self.throttle, 0), (self.front_end, 0))
        self.connect((self.to_iq, 0), (self.clip_i, 0))
        self.connect((self.to_iq, 1), (self.clip_q, 0))
        self.connect((self.tone1, 0), (self.input_sum, 0))
        self.connect((self.tone2, 0), (self.input_sum, 1))
        self.connect((self.total_log, 0), (self.total_num, 0))
        self.connect((self.total_rms, 0), (self.total_log, 0))
        self.connect((self.zero, 0), (self.gain_factor, 1))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab08_sim")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_kt0_fs(10**((-173.98 + 10*math.log10(self.samp_rate))/10))
        self.im_hi_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.im_lo_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.noise_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_noise/2, self.bw_noise/4))
        self.spec.set_frequency_range(0, self.samp_rate)
        self.t1_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.t2_band.set_taps(firdes.low_pass(1, self.samp_rate, self.bw_tone/2, self.bw_tone/2))
        self.throttle.set_sample_rate(self.samp_rate)
        self.tone1.set_sampling_freq(self.samp_rate)
        self.tone2.set_sampling_freq(self.samp_rate)

    def get_p_in(self):
        return self.p_in

    def set_p_in(self, p_in):
        self.p_in = p_in
        self.tone1.set_amplitude(((self.mode >= 2)*math.sqrt(10**(self.p_in/10))))
        self.tone2.set_amplitude(((self.mode == 3)*math.sqrt(10**(self.p_in/10))))

    def get_p_fs0(self):
        return self.p_fs0

    def set_p_fs0(self, p_fs0):
        self.p_fs0 = p_fs0
        self.rx_gain.set_k(10**((self.gain - self.p_fs0)/20))

    def get_nf_fe(self):
        return self.nf_fe

    def set_nf_fe(self, nf_fe):
        self.nf_fe = nf_fe
        self.thermal_noise.set_amplitude((math.sqrt(self.kt0_fs*(1 + (self.mode == 1)*10**(self.enr_db/10)) + self.kt0_fs*(10**(self.nf_fe/10) - 1))))

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        self.mode = mode
        self._mode_callback(self.mode)
        self.thermal_noise.set_amplitude((math.sqrt(self.kt0_fs*(1 + (self.mode == 1)*10**(self.enr_db/10)) + self.kt0_fs*(10**(self.nf_fe/10) - 1))))
        self.tone1.set_amplitude(((self.mode >= 2)*math.sqrt(10**(self.p_in/10))))
        self.tone2.set_amplitude(((self.mode == 3)*math.sqrt(10**(self.p_in/10))))

    def get_kt0_fs(self):
        return self.kt0_fs

    def set_kt0_fs(self, kt0_fs):
        self.kt0_fs = kt0_fs
        self.thermal_noise.set_amplitude((math.sqrt(self.kt0_fs*(1 + (self.mode == 1)*10**(self.enr_db/10)) + self.kt0_fs*(10**(self.nf_fe/10) - 1))))

    def get_iip3_fe(self):
        return self.iip3_fe

    def set_iip3_fe(self, iip3_fe):
        self.iip3_fe = iip3_fe
        self.cubic_coeff.set_k((-1/10**(self.iip3_fe/10)))

    def get_gain(self):
        return self.gain

    def set_gain(self, gain):
        self.gain = gain
        self.rx_gain.set_k(10**((self.gain - self.p_fs0)/20))

    def get_f_noise(self):
        return self.f_noise

    def set_f_noise(self, f_noise):
        self.f_noise = f_noise
        self.noise_band.set_center_freq(self.f_noise)

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

    def get_enr_db(self):
        return self.enr_db

    def set_enr_db(self, enr_db):
        self.enr_db = enr_db
        self.thermal_noise.set_amplitude((math.sqrt(self.kt0_fs*(1 + (self.mode == 1)*10**(self.enr_db/10)) + self.kt0_fs*(10**(self.nf_fe/10) - 1))))

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




def main(top_block_cls=lab08_sim, options=None):

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
