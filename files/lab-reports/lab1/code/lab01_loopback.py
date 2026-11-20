#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: Lab 01 - Loopback (TX1 -> RX1 cable)
# Author: Team-06
# GNU Radio version: 3.10.12.0

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, pyqtSlot
from gnuradio import analog
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import iio
import lab01_loopback_iq_recorder as iq_recorder  # embedded python block
import sip
import threading



class lab01_loopback(gr.top_block, Qt.QWidget):

    def __init__(self):
        gr.top_block.__init__(self, "Lab 01 - Loopback (TX1 -> RX1 cable)", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("Lab 01 - Loopback (TX1 -> RX1 cable)")
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

        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab01_loopback")

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
        self.samp_rate = samp_rate = 2600000
        self.lo_shift = lo_shift = 0
        self.fc = fc = 434e6
        self.uri = uri = "ip:192.168.2.1"
        self.tx_att = tx_att = 60
        self.team = team = "Team-06"
        self.rf_gain = rf_gain = 10
        self.rec_sec = rec_sec = min(4.0, 80e6/(8*samp_rate))
        self.rec = rec = False
        self.f_tx = f_tx = 250e3
        self.f_tune = f_tune = int(fc + lo_shift)

        ##################################################
        # Blocks
        ##################################################

        self._tx_att_range = qtgui.Range(40, 89, 1, 60, 200)
        self._tx_att_win = qtgui.RangeWidget(self._tx_att_range, self.set_tx_att, "TX1 attenuation (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._tx_att_win, 1, 1, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        # Create the options list
        self._samp_rate_options = [2600000, 5000000, 10000000, 20000000]
        # Create the labels list
        self._samp_rate_labels = ['2.6 MS/s', '5 MS/s', '10 MS/s', '20 MS/s']
        # Create the combo box
        self._samp_rate_tool_bar = Qt.QToolBar(self)
        self._samp_rate_tool_bar.addWidget(Qt.QLabel("Sample rate" + ": "))
        self._samp_rate_combo_box = Qt.QComboBox()
        self._samp_rate_tool_bar.addWidget(self._samp_rate_combo_box)
        for _label in self._samp_rate_labels: self._samp_rate_combo_box.addItem(_label)
        self._samp_rate_callback = lambda i: Qt.QMetaObject.invokeMethod(self._samp_rate_combo_box, "setCurrentIndex", Qt.Q_ARG("int", self._samp_rate_options.index(i)))
        self._samp_rate_callback(self.samp_rate)
        self._samp_rate_combo_box.currentIndexChanged.connect(
            lambda i: self.set_samp_rate(self._samp_rate_options[i]))
        # Create the radio buttons
        self.top_grid_layout.addWidget(self._samp_rate_tool_bar, 0, 0, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._rf_gain_range = qtgui.Range(0, 10, 1, 10, 200)
        self._rf_gain_win = qtgui.RangeWidget(self._rf_gain_range, self.set_rf_gain, "RX gain (dB)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._rf_gain_win, 0, 3, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(3, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        _rec_check_box = Qt.QCheckBox("Record I/Q")
        self._rec_choices = {True: True, False: False}
        self._rec_choices_inv = dict((v,k) for k,v in self._rec_choices.items())
        self._rec_callback = lambda i: Qt.QMetaObject.invokeMethod(_rec_check_box, "setChecked", Qt.Q_ARG("bool", self._rec_choices_inv[i]))
        self._rec_callback(self.rec)
        _rec_check_box.stateChanged.connect(lambda i: self.set_rec(self._rec_choices[bool(i)]))
        self.top_grid_layout.addWidget(_rec_check_box, 1, 0, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 1):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._fc_range = qtgui.Range(325e6, 3.8e9, 16e6, 434e6, 200)
        self._fc_win = qtgui.RangeWidget(self._fc_range, self.set_fc, "fc (Hz)", "counter", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._fc_win, 0, 1, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(1, 2):
            self.top_grid_layout.setColumnStretch(c, 1)
        self._f_tx_range = qtgui.Range(-1e6, 1e6, 50e3, 250e3, 200)
        self._f_tx_win = qtgui.RangeWidget(self._f_tx_range, self.set_f_tx, "f_tx (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._f_tx_win, 1, 2, 1, 1)
        for r in range(1, 2):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.waterfall_sink = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            f_tune, #fc
            samp_rate, #bw
            "Waterfall", #name
            1, #number of inputs
            None # parent
        )
        self.waterfall_sink.set_update_time(0.10)
        self.waterfall_sink.enable_grid(False)
        self.waterfall_sink.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.waterfall_sink.set_line_label(i, "Data {0}".format(i))
            else:
                self.waterfall_sink.set_line_label(i, labels[i])
            self.waterfall_sink.set_color_map(i, colors[i])
            self.waterfall_sink.set_line_alpha(i, alphas[i])

        self.waterfall_sink.set_intensity_range(-110, -20)

        self._waterfall_sink_win = sip.wrapinstance(self.waterfall_sink.qwidget(), Qt.QWidget)

        self.top_grid_layout.addWidget(self._waterfall_sink_win, 3, 0, 1, 4)
        for r in range(3, 4):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.tone = analog.sig_source_c(samp_rate, analog.GR_COS_WAVE, f_tx, 0.5, 0, 0)
        self.time_sink = qtgui.time_sink_c(
            1024, #size
            samp_rate, #samp_rate
            "Time (I/Q)", #name
            1, #number of inputs
            None # parent
        )
        self.time_sink.set_update_time(0.10)
        self.time_sink.set_y_axis(-1, 1)

        self.time_sink.set_y_label('Amplitude', "")

        self.time_sink.enable_tags(True)
        self.time_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, qtgui.TRIG_SLOPE_POS, 0.0, 0, 0, "")
        self.time_sink.enable_autoscale(False)
        self.time_sink.enable_grid(True)
        self.time_sink.enable_axis_labels(True)
        self.time_sink.enable_control_panel(False)
        self.time_sink.enable_stem_plot(False)


        labels = ['Signal 1', 'Signal 2', 'Signal 3', 'Signal 4', 'Signal 5',
            'Signal 6', 'Signal 7', 'Signal 8', 'Signal 9', 'Signal 10']
        widths = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        colors = ['blue', 'red', 'green', 'black', 'cyan',
            'magenta', 'yellow', 'dark red', 'dark green', 'dark blue']
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
            1.0, 1.0, 1.0, 1.0, 1.0]
        styles = [1, 1, 1, 1, 1,
            1, 1, 1, 1, 1]
        markers = [-1, -1, -1, -1, -1,
            -1, -1, -1, -1, -1]


        for i in range(2):
            if len(labels[i]) == 0:
                if (i % 2 == 0):
                    self.time_sink.set_line_label(i, "Re{{Data {0}}}".format(i/2))
                else:
                    self.time_sink.set_line_label(i, "Im{{Data {0}}}".format(i/2))
            else:
                self.time_sink.set_line_label(i, labels[i])
            self.time_sink.set_line_width(i, widths[i])
            self.time_sink.set_line_color(i, colors[i])
            self.time_sink.set_line_style(i, styles[i])
            self.time_sink.set_line_marker(i, markers[i])
            self.time_sink.set_line_alpha(i, alphas[i])

        self._time_sink_win = sip.wrapinstance(self.time_sink.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._time_sink_win, 4, 0, 1, 4)
        for r in range(4, 5):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.pluto_source = iio.fmcomms2_source_fc32(uri if uri else iio.get_pluto_uri(), [True, True], 32768)
        self.pluto_source.set_len_tag_key('packet_len')
        self.pluto_source.set_frequency(f_tune)
        self.pluto_source.set_samplerate(samp_rate)
        self.pluto_source.set_gain_mode(0, 'manual')
        self.pluto_source.set_gain(0, rf_gain)
        self.pluto_source.set_quadrature(True)
        self.pluto_source.set_rfdc(True)
        self.pluto_source.set_bbdc(True)
        self.pluto_source.set_filter_params('Off', '', 0, 0)
        self.pluto_sink = iio.fmcomms2_sink_fc32(uri if uri else iio.get_pluto_uri(), [True, True], 32768, False)
        self.pluto_sink.set_len_tag_key('')
        self.pluto_sink.set_bandwidth(20000000)
        self.pluto_sink.set_frequency(int(fc))
        self.pluto_sink.set_samplerate(samp_rate)
        self.pluto_sink.set_attenuation(0, tx_att)
        self.pluto_sink.set_filter_params('Off', '', 0, 0)
        self._lo_shift_range = qtgui.Range(-500e3, 500e3, 10e3, 0, 200)
        self._lo_shift_win = qtgui.RangeWidget(self._lo_shift_range, self.set_lo_shift, "lo_shift (Hz)", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_grid_layout.addWidget(self._lo_shift_win, 0, 2, 1, 1)
        for r in range(0, 1):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(2, 3):
            self.top_grid_layout.setColumnStretch(c, 1)
        self.iq_recorder = iq_recorder.blk(team=team, lab=1, fc=f_tune, fs=samp_rate, gain=rf_gain, record=rec, max_seconds=rec_sec, folder="recordings")
        self.freq_sink = qtgui.freq_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            f_tune, #fc
            samp_rate, #bw
            "Spectrum", #name
            1,
            None # parent
        )
        self.freq_sink.set_update_time(0.10)
        self.freq_sink.set_y_axis((-120), 0)
        self.freq_sink.set_y_label('Relative Gain', 'dB')
        self.freq_sink.set_trigger_mode(qtgui.TRIG_MODE_FREE, 0.0, 0, "")
        self.freq_sink.enable_autoscale(False)
        self.freq_sink.enable_grid(True)
        self.freq_sink.set_fft_average(1.0)
        self.freq_sink.enable_axis_labels(True)
        self.freq_sink.enable_control_panel(True)
        self.freq_sink.set_fft_window_normalized(False)



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
                self.freq_sink.set_line_label(i, "Data {0}".format(i))
            else:
                self.freq_sink.set_line_label(i, labels[i])
            self.freq_sink.set_line_width(i, widths[i])
            self.freq_sink.set_line_color(i, colors[i])
            self.freq_sink.set_line_alpha(i, alphas[i])

        self._freq_sink_win = sip.wrapinstance(self.freq_sink.qwidget(), Qt.QWidget)
        self.top_grid_layout.addWidget(self._freq_sink_win, 2, 0, 1, 4)
        for r in range(2, 3):
            self.top_grid_layout.setRowStretch(r, 1)
        for c in range(0, 4):
            self.top_grid_layout.setColumnStretch(c, 1)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.pluto_source, 0), (self.freq_sink, 0))
        self.connect((self.pluto_source, 0), (self.iq_recorder, 0))
        self.connect((self.pluto_source, 0), (self.time_sink, 0))
        self.connect((self.pluto_source, 0), (self.waterfall_sink, 0))
        self.connect((self.tone, 0), (self.pluto_sink, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("gnuradio/flowgraphs", "lab01_loopback")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_rec_sec(min(4.0, 80e6/(8*self.samp_rate)))
        self._samp_rate_callback(self.samp_rate)
        self.freq_sink.set_frequency_range(self.f_tune, self.samp_rate)
        self.iq_recorder.fs = self.samp_rate
        self.pluto_sink.set_samplerate(self.samp_rate)
        self.pluto_source.set_samplerate(self.samp_rate)
        self.time_sink.set_samp_rate(self.samp_rate)
        self.tone.set_sampling_freq(self.samp_rate)
        self.waterfall_sink.set_frequency_range(self.f_tune, self.samp_rate)

    def get_lo_shift(self):
        return self.lo_shift

    def set_lo_shift(self, lo_shift):
        self.lo_shift = lo_shift
        self.set_f_tune(int(self.fc + self.lo_shift))

    def get_fc(self):
        return self.fc

    def set_fc(self, fc):
        self.fc = fc
        self.set_f_tune(int(self.fc + self.lo_shift))
        self.pluto_sink.set_frequency(int(self.fc))

    def get_uri(self):
        return self.uri

    def set_uri(self, uri):
        self.uri = uri

    def get_tx_att(self):
        return self.tx_att

    def set_tx_att(self, tx_att):
        self.tx_att = tx_att
        self.pluto_sink.set_attenuation(0,self.tx_att)

    def get_team(self):
        return self.team

    def set_team(self, team):
        self.team = team
        self.iq_recorder.team = self.team

    def get_rf_gain(self):
        return self.rf_gain

    def set_rf_gain(self, rf_gain):
        self.rf_gain = rf_gain
        self.iq_recorder.gain = self.rf_gain
        self.pluto_source.set_gain(0, self.rf_gain)

    def get_rec_sec(self):
        return self.rec_sec

    def set_rec_sec(self, rec_sec):
        self.rec_sec = rec_sec
        self.iq_recorder.max_seconds = self.rec_sec

    def get_rec(self):
        return self.rec

    def set_rec(self, rec):
        self.rec = rec
        self._rec_callback(self.rec)
        self.iq_recorder.record = self.rec

    def get_f_tx(self):
        return self.f_tx

    def set_f_tx(self, f_tx):
        self.f_tx = f_tx
        self.tone.set_frequency(self.f_tx)

    def get_f_tune(self):
        return self.f_tune

    def set_f_tune(self, f_tune):
        self.f_tune = f_tune
        self.freq_sink.set_frequency_range(self.f_tune, self.samp_rate)
        self.iq_recorder.fc = self.f_tune
        self.pluto_source.set_frequency(self.f_tune)
        self.waterfall_sink.set_frequency_range(self.f_tune, self.samp_rate)




def main(top_block_cls=lab01_loopback, options=None):

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
