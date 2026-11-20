"""Read Team 06's saved display images; these are NOT raw-IQ PSD estimates.

Usage: python analysis/digitize_saved_screens.py
Requires numpy and Pillow. Output: analysis/screen_measurements.json.
The colour trace is reduced to one median vertical coordinate per image column.
Keep image-pixel uncertainty separate from FFT-bin spacing.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent


def trace(name, x0, f0, px_mhz, y40, px20, stop, colour='blue'):
    a = np.asarray(Image.open(ROOT/'figures'/name).convert('RGB'), dtype=np.int16)
    x = np.arange(110, stop)
    r, g, b = np.moveaxis(a[42:415, x], 2, 0)
    mask = ((b-r > 105) & (b-g > 105)) if colour == 'blue' else ((r-b > 75) & (g-b > 75) & (abs(r-g) < 30))
    y = np.array([np.median(np.flatnonzero(c))+42 if c.any() else np.nan for c in mask.T])
    ok = np.isfinite(y)
    y = np.interp(x, x[ok], y[ok])
    return f0+(x-x0)/px_mhz, -40-(y-y40)*20/px20


def median(a, n):
    return np.median(np.lib.stride_tricks.sliding_window_view(np.pad(a,n//2,mode='edge'),n),axis=1)


def width(f, y, centre, roi=.15):
    sel = abs(f-centre) <= roi
    ff, yy = f[sel], median(y,3)[sel]
    k = np.argmax(yy)
    floor = np.median(yy[(abs(ff-centre) >= .10)])
    x = 20 if yy[k]-floor >= 26 else 6
    level = yy[k]-x
    left = k
    while left > 0 and yy[left-1] >= level: left -= 1
    right = k
    while right+1 < len(yy) and yy[right+1] >= level: right += 1
    # Interpolate threshold crossings; no claimed precision beyond image pixels.
    fl = np.interp(level, yy[left-1:left+1], ff[left-1:left+1]) if left else ff[0]
    fu = np.interp(level, yy[right:right+2][::-1], ff[right:right+2][::-1]) if right+1 < len(yy) else ff[-1]
    return dict(candidate_mhz=centre, peak_relative_db=float(yy[k]), local_floor_relative_db=float(floor), x_db=x,
                fL_mhz=float(fl), fU_mhz=float(fu), Bx_khz=float((fu-fl)*1000),
                midpoint_mhz=float((fl+fu)/2), pixel_khz=float(np.median(np.diff(f))*1000),
                trace='instantaneous median pixel trace; NOT Max Hold', raw_B99=None)


def main():
    f,y = trace('wide947_g20.jpg',339,940,76.55,84,82,1640)
    out = {'method':'Display-image readings only; no raw-IQ reconstruction or Welch recomputation.',
           'gsm':[width(f,y,c) for c in (952.8,953.8,954.2)]}
    f,y = trace('band_b_scan.jpg',109,425,75.4,80,82,1617)
    sm = median(y,61)
    mid = np.median(sm[(f>=432)&(f<=438)])
    ok = abs(sm-mid) <= 3
    k = np.argmin(abs(f-435))
    left=right=k
    while left > 0 and ok[left-1]: left-=1
    while right+1<len(f) and ok[right+1]: right+=1
    out['baseline']={'reference_db':float(mid),'tolerance_db':3,'smoothing_pixels':61,
                     'fL_mhz':float(f[left]),'fU_mhz':float(f[right]),
                     'fraction_of_fs':float((f[right]-f[left])/20),
                     'interpretation':'Baseline flatness of this saved RF view, not calibrated filter bandwidth.'}
    (ROOT/'analysis'/'screen_measurements.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2))


if __name__ == '__main__': main()
