"""Task 5: run the mandatory original Python/Qt antenna program.

The original source is unchanged. Its own spinbox, scheduler and power meter
take a 20 MHz sweep and 1 MHz edge measurements. No RF hardware is used.
"""
from pathlib import Path
import os,sys,time,json,csv
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'out';OUT.mkdir(exist_ok=True)
cache=OUT/'runtime_cache';cache.mkdir(exist_ok=True)
os.environ['QT_QPA_PLATFORM']='offscreen'
os.environ['XDG_CACHE_HOME']=str(cache)
os.environ['XDG_CONFIG_HOME']=str(cache/'config')
import numpy as np
from PyQt5 import QtWidgets,QtGui
import lab02_antenna_response_simulation as original

def main():
    app=QtWidgets.QApplication(sys.argv)
    font=Path(sys.prefix)/'fonts'/'DejaVuSans.ttf'
    if font.exists():QtGui.QFontDatabase.addApplicationFont(str(font))
    app.setFont(QtGui.QFont('DejaVu Sans',10))
    window=original.FilterSimulation();window.show();window.begin()
    def pump(condition,timeout):
        deadline=time.monotonic()+timeout
        while not condition():
            if time.monotonic()>deadline:raise TimeoutError('Original antenna program timed out')
            app.processEvents();time.sleep(.005)
    try:
        window.start_sweep();pump(lambda:not window.running_sweep,180)
        coarse=sorted((float(f/1e6),float(v)) for f,v in window.points.items())
        print('COARSE',len(coarse),flush=True)
        fine=[]
        for rf in list(range(795,826))+list(range(1775,1806)):
            key=int(rf*1e6);window.points.pop(key,None)
            window.frequency.setValue(rf);window.arm()
            pump(lambda:key in window.points,10)
            fine.append([float(rf),float(window.points[key])])
        peak=max(v for _,v in coarse);level=peak-3
        def edges(points):
            points=sorted(points);found=[]
            for (a,ya),(b,yb) in zip(points,points[1:]):
                if b-a>25:continue
                if (ya-level)*(yb-level)<0:found.append(a+(level-ya)*(b-a)/(yb-ya))
            if len(found)!=2:raise ValueError('Both -3 dB crossings must be bracketed')
            return found
        cl,ch=edges(coarse);fl,fh=edges(fine)
        result=dict(group_number=6,peak_db=peak,coarse=coarse,fine=fine,
            coarse_fL=cl,coarse_fH=ch,fL=fl,fH=fh,BW=fh-fl,step_coarse=20,step_fine=1,
            method='original Python program, original power meter, original settle and acquisition times')
        (OUT/'antenna.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        for name,rows in [('antenna.csv',coarse),('antenna_fine.csv',fine)]:
            with (OUT/name).open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['rf_equivalent_frequency_mhz','response_db']);w.writerows(rows)
        print('COMPLETE',fl,fh,fh-fl,flush=True)
    finally:window.close();app.processEvents()

if __name__=='__main__':main()
