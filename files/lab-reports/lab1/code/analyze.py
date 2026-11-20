"""Analyze Team 06 complex64 recordings without connecting to the SDR."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import correlate, find_peaks, welch, windows


def db(power):
    return 10*np.log10(np.maximum(power, 1e-30))


def psd(samples, fs, n):
    f, p = welch(samples, fs, window='blackmanharris', nperseg=n,
                 noverlap=n//2, detrend=False, return_onesided=False)
    return np.fft.fftshift(f), np.fft.fftshift(p)


def edges(f, p, mask, floor):
    f, p = f[mask], np.maximum(p[mask]-floor, 0)
    cumulative = np.cumsum(p)
    limits = np.interp(cumulative[-1]*np.array([.005,.995]),
                       np.r_[0,cumulative], np.r_[f[0]-(f[1]-f[0])/2, f+(f[1]-f[0])/2])
    return list(limits)


def tone_peaks(samples, fs, fc):
    n = 2**20
    w = windows.hann(n, sym=False)
    z = np.fft.fftshift(np.fft.fft(samples[fs:fs+n]*w, 2*n))
    freq = np.fft.fftshift(np.fft.fftfreq(2*n, 1/fs))
    level = db(abs(z/w.sum())**2)
    pks, _ = find_peaks(level, distance=int(2000*2*n/fs))
    pks = pks[np.abs(freq[pks]) <= .4*fs]
    strongest = pks[np.argsort(level[pks])[-6:][::-1]]
    result = []
    for k in strongest:
        a,b,c=level[k-1:k+2]
        offset=.5*(a-c)/(a-2*b+c)*fs/(2*n)
        result.append({'baseband_hz':float(freq[k]+offset),
                       'rf_hz':float(fc+freq[k]+offset),'dbfs':float(b)})
    return result


def frame_spectrum(samples, fs, n):
    f = np.fft.fftshift(np.fft.fftfreq(n, 1/fs))
    w = windows.blackmanharris(n, sym=False)
    frames = samples[:len(samples)//n*n].reshape(-1,n)
    p = np.empty(frames.shape,dtype=np.float32)
    for i in range(0,len(frames),256):
        ft=np.fft.fftshift(np.fft.fft(frames[i:i+256]*w,axis=1),axes=1)
        p[i:i+256]=np.abs(ft)**2/(fs*np.dot(w,w))
    t = (np.arange(len(frames))+.5)*n/fs
    return t, f, p


def runs(state):
    changes=np.diff(np.r_[False,state,False].astype(int))
    return np.column_stack((np.flatnonzero(changes==1),np.flatnonzero(changes==-1)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('recordings',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent.parent/'figures')
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    result={}
    for path in sorted(args.recordings.glob('Team-06_lab01_*.cf32')):
        _,_,fc,fs,gain,stamp=path.stem.split('_')
        fc,fs=int(fc),int(fs)
        samples=np.memmap(path,mode='r',dtype='<c8')
        row={'file':path.name,'fc':fc,'fs':fs,'gain':float(gain),'bytes':path.stat().st_size,
             'samples':len(samples),'duration':len(samples)/fs}
        result[stamp]=row
        if fc==434100000:
            row['peaks']=tone_peaks(samples,fs,fc)
            f,p=psd(samples,fs,16384)
            plt.figure(figsize=(7,2.65));plt.plot((fc+f)/1e6,db(p),lw=.75)
            plt.xlim(433.0,435.2);plt.ylabel('PSD (dBFS/Hz)');plt.xlabel('Frequency (MHz)')
            plt.grid(alpha=.22);plt.tight_layout();plt.savefig(args.output/f'loop_{stamp[-6:]}.png',dpi=190);plt.close()
        elif fc==945000000:
            f,p=psd(samples,fs,16384)
            row['max_iq']=[float(np.max(np.abs(samples.real))),float(np.max(np.abs(samples.imag)))]
            row['slice_dbfs']=float(db(p.sum()*fs/len(p)))
            row['trusted_slice_dbfs']=float(db(p[np.abs(f)<=.4*fs].sum()*fs/len(p)))
            row['psd_regions']=[float(db(np.median(p[(f>=a)&(f<b)]))) for a,b in [(-1300000,-1170000),(-800000,-200000),(200000,800000),(1170000,1300000)]]
            fig,ax=plt.subplots(figsize=(7,2.8));ax.plot((fc+f)/1e6,db(p),lw=.75)
            ax.axvspan(943.7,943.96,color='grey',alpha=.15);ax.axvspan(946.04,946.3,color='grey',alpha=.15)
            ax.set(xlim=(943.7,946.3),xlabel='Frequency (MHz)',ylabel='PSD (dBFS/Hz)')
            ax.grid(alpha=.22);fig.tight_layout();fig.savefig(args.output/'downlink_iq.png',dpi=190);plt.close(fig)
        elif fc==434000000:
            t,f,p=frame_spectrum(samples,fs,1024)
            df=fs/len(f)
            channel=(f>=10000)&(f<=80000)
            power=db(p[:,channel].sum(axis=1)*df)
            threshold=float(np.percentile(power,20)+12)
            intervals=runs(power>threshold)
            intervals=intervals[(intervals[:,1]-intervals[:,0])>=4]
            row['threshold_dbfs']=threshold
            row['burst_start_ms']=(intervals[:,0]*1024/fs*1000).tolist()
            row['burst_width_ms']=((intervals[:,1]-intervals[:,0])*1024/fs*1000).tolist()
            row['active_channel_dbfs']=float(db(np.mean(10**(power[power>threshold]/10))))
            mask=np.zeros(len(t),bool)
            for a,b in intervals: mask[a:b]=True
            active_time=mask[intervals[0,0]:intervals[-1,1]].astype(float)
            active_time-=active_time.mean()
            autocorr=correlate(active_time,active_time)[len(active_time)-1:]
            lags=np.arange(len(autocorr))*1024/fs
            candidates=np.flatnonzero((lags>=.03)&(lags<=.07))
            peak=candidates[np.argmax(autocorr[candidates])]
            row['repeat_ms']=float(lags[peak]*1000)
            row['repeat_correlation']=float(autocorr[peak]/autocorr[0])
            active=p[mask].mean(axis=0)
            quiet=np.median(p[power<threshold-6],axis=0)
            row['burst_bands']=[]
            for low,high in [(-150000,-100000),(20000,65000),(170000,240000)]:
                local=(f>=low)&(f<=high)
                floor=float(np.median(quiet[local]))
                lo,hi=edges(f,active,local,floor)
                row['burst_bands'].append({'bounds_hz':[low,high],'b99_hz':hi-lo,
                    'centroid_label_hz':fc+(lo+hi)/2,'edges_hz':[fc+lo,fc+hi],
                    'peak_label_hz':fc+float(f[np.flatnonzero(local)[np.argmax(active[local])]]),
                    'active_dbfs':float(db(np.maximum(active[local]-floor,0).sum()*df))})
            fig,(ax,ap)=plt.subplots(2,1,figsize=(7.5,4.6),height_ratios=[2,1],layout='constrained')
            bins=(f>=-210000)&(f<=260000)
            h=ax.imshow(db(p[:,bins]).T,origin='lower',aspect='auto',
                        extent=(0,len(t)*1024/fs,(fc+f[bins][0]-df/2)/1e6,(fc+f[bins][-1]+df/2)/1e6),
                        vmin=-123,vmax=-78,cmap='viridis',interpolation='nearest')
            ax.set(xlabel='Time from start (s)',ylabel='Frequency (MHz)');fig.colorbar(h,ax=ax,label='PSD (dBFS/Hz)',pad=.02)
            ap.plot(t,power,color='#164c77',lw=.85);ap.axhline(threshold,color='#924324',ls='--',lw=.9)
            ap.set(xlabel='Time from start (s), detail',ylabel='Channel power (dBFS)',xlim=(1.31,1.47));ap.grid(alpha=.18)
            fig.savefig(args.output/'band_b_waterfall.png',dpi=190);plt.close(fig)
            # Use longer Welch windows inside each accepted active run so that
            # the occupied-width estimate resolves the main 434.04 MHz signal.
            spectra=[]; weights=[]
            for a,b in intervals:
                if (b-a)*1024>=4096:
                    fine_f,fine_p=psd(samples[a*1024:b*1024],fs,4096)
                    spectra.append(fine_p);weights.append((b-a)*1024)
            if spectra:
                fine=np.average(spectra,axis=0,weights=weights)
                fine_grid,whole=psd(samples,fs,4096)
                low,high=20000,65000
                band=(fine_f>=low)&(fine_f<=high)
                floor=float(np.median(fine[(fine_f>=65000)&(fine_f<=80000)]))
                lo,hi=edges(fine_f,fine,band,floor)
                row['burst_fine']={'edges_hz':[fc+lo,fc+hi],'b99_hz':hi-lo,'mid_hz':fc+(lo+hi)/2,
                    'df_hz':fs/4096,'peak_dbfs_per_hz':float(db(max(fine[band]))),
                    'power_dbfs':float(db(np.maximum(fine[band]-floor,0).sum()*fs/4096))}
                fig,ax=plt.subplots(figsize=(7,2.7));ax.plot((fc+fine_f)/1e6,db(fine),label='Burst intervals',lw=.9)
                ax.plot((fc+fine_grid)/1e6,db(whole),label='Entire recording',lw=.8,alpha=.75)
                ax.axvspan((fc+lo)/1e6,(fc+hi)/1e6,alpha=.13,color='#2372a3',label='99% band')
                ax.set(xlim=(433.82,434.24),xlabel='Frequency (MHz)',ylabel='PSD (dBFS/Hz)');ax.grid(alpha=.22);ax.legend(fontsize=8)
                fig.tight_layout();fig.savefig(args.output/'band_b_psd.png',dpi=190);plt.close(fig)
    (Path(__file__).resolve().parent/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
