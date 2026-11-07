"""Execute the supplied receiver model with genuine GNU Radio 3.10 blocks.

The signal path and FIR coefficients match lab02_sim.py. GUI sinks and the
wall-clock throttle are replaced by finite acquisition and vector sinks.
All exported powers are linear time averages, converted to dB afterwards.
"""
from pathlib import Path
import csv, json, math, platform, time
import numpy as np
from gnuradio import gr, analog, blocks, filter
from gnuradio.filter import firdes

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'out'
FS = 2048000
NF_FE = 6.0
IIP3 = -25.0
PFS = -30.0
N = 1048576
DISCARD = 16384
KT = 10 ** ((-173.98 + 10 * np.log10(FS)) / 10)

def db(p):
    return float(10*np.log10(max(float(p),1e-30)))

def acquire(gain, mode=0, pin=-80, enr=15, seed=101, n=N, raw=False, capture_noise=False):
    tb = gr.top_block('Lab02 finite acquisition')
    t1 = analog.sig_source_c(FS, analog.GR_COS_WAVE, 300000,
                             (mode>=2)*math.sqrt(10**(pin/10)),0,0)
    t2 = analog.sig_source_c(FS, analog.GR_COS_WAVE, 400000,
                             (mode==3)*math.sqrt(10**(pin/10)),0,0)
    noise = analog.noise_source_c(analog.GR_GAUSSIAN,
        math.sqrt(KT*(10**(NF_FE/10)+(mode==1)*10**(enr/10))),seed)
    adder=blocks.add_vcc(1)
    head=blocks.head(gr.sizeof_gr_complex,n+DISCARD)
    env=blocks.complex_to_mag_squared(1)
    c3=blocks.multiply_const_ff(-1/10**(IIP3/10))
    one=blocks.add_const_ff(1)
    zero=analog.sig_source_f(0,analog.GR_CONST_WAVE,0,0,0)
    factor=blocks.float_to_complex(1)
    fe=blocks.multiply_vcc(1)
    rx=blocks.multiply_const_cc(10**((gain-PFS)/20))
    adc_noise=analog.noise_source_c(analog.GR_GAUSSIAN,0.5*math.sqrt(2)/127,seed+1000)
    adc_sum=blocks.add_vcc(1)
    iq=blocks.complex_to_float(1)
    output=blocks.float_to_complex(1)
    tb.connect(t1,(adder,0)); tb.connect(t2,(adder,1)); tb.connect(noise,(adder,2))
    tb.connect(adder,head,env,c3,one,(factor,0));tb.connect(zero,(factor,1))
    tb.connect(head,(fe,0));tb.connect(factor,(fe,1));tb.connect(fe,rx,(adc_sum,0))
    tb.connect(adc_noise,(adc_sum,1));tb.connect(adc_sum,iq)
    keep=[]
    for i in range(2):
        rail=analog.rail_ff(-1,1);scale=blocks.multiply_const_ff(127)
        quant=blocks.float_to_char(1,1);back=blocks.char_to_float(1,127)
        tb.connect((iq,i),rail,scale,quant,back,(output,i))
        keep.extend([rail,scale,quant,back])
    sinks=[]
    # Identical translating filters, including the original decimation.
    for f,bw,decim,transition in [(-500000,400000,4,100000),
        (300000,10000,64,5000),(400000,10000,64,5000),
        (200000,10000,64,5000),(500000,10000,64,5000)]:
        band=filter.freq_xlating_fir_filter_ccf(decim,
              firdes.low_pass(1,FS,bw/2,transition),f,FS)
        sink=blocks.vector_sink_c();tb.connect(output,band,sink)
        sinks.append((sink,decim));keep.append(band)
    if raw:
        rs=blocks.vector_sink_c();tb.connect(output,rs)
    tb.run()
    powers=[]
    for sink,decim in sinks:
        arr=np.asarray(sink.data(),dtype=np.complex64)[DISCARD//decim:]
        powers.append(db(np.mean(np.abs(arr.astype(np.complex128))**2)))
    if capture_noise:
        sink,decim=sinks[0]
        return powers,np.asarray(sink.data(),dtype=np.complex64)[DISCARD//decim:]
    if raw:
        return powers,np.asarray(rs.data(),dtype=np.complex64)[DISCARD:]
    return powers

def save(name, rows):
    with (DATA/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def crossing(rows):
    # Reference small-signal gain from an additional low-distortion point.
    ref=rows[0]['pout_dbfs']-rows[0]['pin_dbm']
    for a,b in zip(rows,rows[1:]):
        ca=a['pin_dbm']+ref-a['pout_dbfs'];cb=b['pin_dbm']+ref-b['pout_dbfs']
        if ca<=1<=cb:
            return a['pin_dbm']+(1-ca)/(cb-ca)*(b['pin_dbm']-a['pin_dbm'])
    return None

