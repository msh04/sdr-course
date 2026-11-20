"""Replot the digitized display traces; not a raw-IQ plot."""
from pathlib import Path
import json, sys
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str((ROOT/'analysis').resolve()))
import digitize_saved_screens as ds
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

# Plot only the user's saved image traces. These are not synthetic IQ spectra.
f,y=ds.trace('wide947_g20.jpg',339,940,76.55,84,82,1640)
y=ds.median(y,3)
d=json.loads((ROOT/'analysis/screen_measurements.json').read_text())
c=canvas.Canvas(str(ROOT/'figures/gsm_display_widths.pdf'),pagesize=(520,470))
c.setTitle('Image-derived widths of three GSM candidates')
c.setFont('Helvetica-Bold',13);c.drawString(48,450,'Three narrow candidates: saved display trace')
for j,row in enumerate(d['gsm']):
    xx,yy,ww,hh=55,325-j*140,440,100
    lo=row['candidate_mhz']-.18;hi=lo+.36;bot=-115;top=-55
    xf=lambda q:xx+(q-lo)/(hi-lo)*ww
    yf=lambda q:yy+(q-bot)/(top-bot)*hh
    c.setStrokeColor(HexColor('#d9dfe6'));c.setLineWidth(.5)
    for tick in (-110,-90,-70):
        c.line(xx,yf(tick),xx+ww,yf(tick));c.setFillColor(HexColor('#344054'));c.setFont('Helvetica',8);c.drawRightString(xx-5,yf(tick)-3,str(tick))
    c.setStrokeColor(HexColor('#1c63a0'));c.setLineWidth(.9)
    ids=(f>=lo)&(f<=hi); p=c.beginPath();first=True
    for a,b in zip(f[ids],y[ids]):
        if first:p.moveTo(xf(a),yf(max(bot,min(top,b))));first=False
        else:p.lineTo(xf(a),yf(max(bot,min(top,b))))
    c.drawPath(p)
    c.setStrokeColor(HexColor('#bc5b20'));c.setDash(3,2)
    level=row['peak_relative_db']-row['x_db'];c.line(xx,yf(level),xx+ww,yf(level))
    for edge in (row['fL_mhz'],row['fU_mhz']):c.line(xf(edge),yy,xf(edge),yy+hh)
    c.setDash();c.setStrokeColor(HexColor('#344054'));c.line(xx,yy,xx+ww,yy)
    c.setFont('Helvetica',8);c.setFillColor(HexColor('#344054'))
    for tick in (lo,lo+.12,lo+.24,hi):c.drawCentredString(xf(tick),yy-13,f'{tick:.2f}')
    c.setFont('Helvetica-Bold',9);c.drawString(xx+4,yy+hh+5,f"{row['candidate_mhz']:.1f} MHz candidate: image B6 ~ {row['Bx_khz']:.0f} kHz")
c.setFont('Helvetica',8);c.drawString(55,12,'Frequency (MHz); vertical scale: relative dB. Pixel spacing 13.1 kHz. Not Max Hold or raw Welch PSD.')
c.save()

