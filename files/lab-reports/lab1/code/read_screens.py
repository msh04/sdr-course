"""Estimate graph readings from the original Team 06 PNG screenshots."""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import median_filter


def trace(path, xref, fref, pixels_per_mhz, yref, pixels_per_20db, stop, color):
    pixels = np.asarray(Image.open(path).convert('RGB'), dtype=np.int16)
    x = np.arange(110, stop)
    red, green, blue = np.moveaxis(pixels[42:415, x], 2, 0)
    if color == 'blue':
        mask = (blue-red > 105) & (blue-green > 105)
    else:
        mask = (red-blue > 75) & (green-blue > 75) & (abs(red-green) < 30)
    middle, upper = np.full(len(x), np.nan), np.full(len(x), np.nan)
    for i, column in enumerate(mask.T):
        rows = np.flatnonzero(column)
        if len(rows):
            middle[i], upper[i] = np.median(rows)+42, rows[0]+42
    for y in (middle, upper):
        valid = np.isfinite(y)
        y[:] = -40-(np.interp(x,x[valid],y[valid])-yref)*20/pixels_per_20db
    return fref+(x-xref)/pixels_per_mhz, middle, upper


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('screens', type=Path)
    folder = parser.parse_args().screens
    prefix = 'Team-06_lab01_'
    wide = folder/(prefix+'947000000_2600000_20.0_20261104.png')
    f, middle, upper = trace(wide,339,940,76.55,84,82,1640,'blue')
    top = median_filter(upper,3)
    for expected in (952.8,953.8,954.2):
        sel = abs(f-expected) <= .13
        power = 10**(top[sel]/10)
        weights = power-power.min()
        print(f'GSM candidate {expected:.1f} MHz: {np.average(f[sel],weights=weights):.3f} MHz, peak {top[sel].max():.1f} dB')
    smooth = median_filter(middle,9)
    for low, high in ((941.45,946.65),(946.65,952.25)):
        plateau = np.median(smooth[(f>=low+1.1)&(f<=high-1.1)])
        for drop in (3,12):
            band = f[(f>=low)&(f<=high)&(smooth>=plateau-drop)]
            print(f'Wide block {low:.2f}--{high:.2f} MHz at -{drop} dB: {band[0]:.3f}--{band[-1]:.3f} MHz, width {band[-1]-band[0]:.3f} MHz')
    quiet_view = folder/(prefix+'945000000_2600000_20.0_20261104.png')
    f, middle, _ = trace(quiet_view,109,935,75.4,89,73,1617,'blue')
    for low, high in ((935,936),(939,941)):
        print(f'Median baseline {low}--{high} MHz: {np.median(middle[(f>=low)&(f<high)]):.1f} dB')
    hold = folder/(prefix+'434000000_20000000_250KHz_20261104.png')
    f, y, _ = trace(hold,875,434,588.5,100,82,1640,'yellow')
    candidates = np.flatnonzero((f>=434.01)&(f<=434.07))
    peak = candidates[np.argmax(y[candidates])]
    below = np.flatnonzero(y<y[peak]-20)
    left, right = below[below<peak][-1]+1, below[below>peak][0]-1
    print(f'Burst Max Hold: peak {y[peak]:.1f} dB, B20 {(f[right]-f[left])*1000:.1f} kHz, edges {f[left]:.3f}--{f[right]:.3f} MHz')


if __name__ == '__main__':
    main()
