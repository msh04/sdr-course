"""Task 4: finite acquisitions using genuine GNU Radio blocks. Run in radioconda."""
from gnuradio_measurements import *

def main():
    DATA.mkdir(parents=True,exist_ok=True)
    meta={'group_number':6,'gnu_radio':gr.version(),'python':platform.python_version(),
          'fs_hz':FS,'samples_per_record':N,'discard_samples':DISCARD,
          'nf_fe_db':NF_FE,'iip3_fe_dbm':IIP3,'pfs0_dbm':PFS,
          'method':'Genuine GNU Radio blocks; finite run; mean squared FIR output',
          'records':{},'antenna':json.loads((DATA/'metadata.json').read_text())['antenna'] if (DATA/'metadata.json').exists() else {}}
    noise_rows=[];nf_summary=[]
    for gain in range(0,51,10):
        enr=45 if gain==0 else 35 if gain<=20 else 15
        off=[];on=[]
        for rep in range(5):
            a=acquire(gain,0,enr=enr,seed=100+rep)[0]
            b=acquire(gain,1,enr=enr,seed=200+rep)[0]
            off.append(10**(a/10));on.append(10**(b/10))
            noise_rows.append(dict(gain_db=gain,enr_db=enr,repeat=rep+1,
                                   off_dbfs=a,on_dbfs=b))
        po=np.mean(off);ph=np.mean(on);yd=db(ph/po)
        nf=enr-db(ph/po-1)
        nf_reps=[enr-db(b/a-1) for a,b in zip(off,on)]
        r=dict(gain_db=gain,enr_db=enr,off_dbfs=db(po),on_dbfs=db(ph),
               y_db=yd,nf_db=nf,nf_repeat_sd_db=float(np.std(nf_reps,ddof=1)))
        nf_summary.append(r);print('NOISE',r,flush=True)
    save('noise_repeats.csv',noise_rows);save('noise_summary.csv',nf_summary)
    sweeps=[];p1=[]
    for gain in range(0,51,10):
        guess=min(-34.64,-29.1-gain)
        pins=sorted(set([min(-60,-45-gain),round(guess-16,1),round(guess-10,1),round(guess-6,1)] +
                       list(np.arange(math.floor(guess)-3,math.ceil(guess)+4,1))))
        rows=[]
        for pin in pins:
            vals=acquire(gain,2,pin=float(pin),seed=301,n=524288)
            row=dict(gain_db=gain,pin_dbm=float(pin),pout_dbfs=vals[1],
                     pout_calibrated_dbm=vals[1]+PFS)
            rows.append(row);sweeps.append(row)
        val=crossing(rows);p1.append(dict(gain_db=gain,p1db_input_dbm=val))
        print('P1DB',gain,val,flush=True)
    save('single_tone_sweeps.csv',sweeps);save('p1db_summary.csv',p1)
    two=[]
    for gain,pins in [(0,[-49,-47,-45,-43,-41,-39,-37,-35]),
                      (40,[-82,-80,-78,-76,-75,-74,-73,-72,-71,-70,-69,-68,-67,-66])]:
        for pin in pins:
            vals=acquire(gain,3,pin=pin,seed=401)
            # Average the two symmetric power meters in the power domain.
            fundamental=db((10**(vals[1]/10)+10**(vals[2]/10))/2)
            im=db((10**(vals[3]/10)+10**(vals[4]/10))/2)
            row=dict(gain_db=gain,pin_per_tone_dbm=pin,f1_dbfs=vals[1],
                 f2_dbfs=vals[2],im_lo_dbfs=vals[3],im_hi_dbfs=vals[4],
                 tone_mean_dbfs=fundamental,im_mean_dbfs=im,
                 iip3_apparent_dbm=pin+(fundamental-im)/2)
            two.append(row);print('TWO',gain,pin,round(im,3),flush=True)
    save('two_tone.csv',two)
    combined=[]
    for nr,pr in zip(nf_summary,p1):
        floor=-173.98+40+nr['nf_db'];v=pr['p1db_input_dbm']
        combined.append(dict(gain_db=nr['gain_db'],nf_db=nr['nf_db'],
           noise_floor_10khz_dbm=floor,p1db_input_dbm=v,
           compression_dynamic_range_db=v-floor))
    save('gain_comparison.csv',combined)
    baseline=acquire(0,0,seed=701,n=4194304)
    bn=(10**(baseline[3]/10)+10**(baseline[4]/10))/2
    for r in two:
        if r['gain_db']==0:
            ip=10**(r['im_mean_dbfs']/10)
            r['im_noise_corrected_dbfs']=db(max(ip-bn,1e-30))
            r['iip3_corrected_dbm']=r['pin_per_tone_dbm']+(r['tone_mean_dbfs']-r['im_noise_corrected_dbfs'])/2
        else:
            r['im_noise_corrected_dbfs']='';r['iip3_corrected_dbm']=''
    save('two_tone.csv',two)
    sel=[r for r in two if r['gain_db']==0 and -47<=r['pin_per_tone_dbm']<=-43]
    meta['iip3_fit']={'im3_slope':float(np.polyfit([r['pin_per_tone_dbm'] for r in sel],[r['im_mean_dbfs'] for r in sel],1)[0]),
       'fundamental_slope':float(np.polyfit([r['pin_per_tone_dbm'] for r in sel],[r['tone_mean_dbfs'] for r in sel],1)[0]),
       'apparent_iip3_mean_dbm':float(np.mean([r['iip3_apparent_dbm'] for r in sel])),
       'corrected_im3_slope':float(np.polyfit([r['pin_per_tone_dbm'] for r in sel],[r['im_noise_corrected_dbfs'] for r in sel],1)[0]),
       'corrected_iip3_mean_dbm':float(np.mean([r['iip3_corrected_dbm'] for r in sel])),
       'baseline_im3_noise_dbfs':db(bn)}
    reference=next(r for r in sweeps if r['gain_db']==0)
    small_gain=reference['pout_dbfs']-reference['pin_dbm']
    meta['iip3_fit']['extrapolated_fundamental_iip3_dbm']=float(np.mean([
        r['pin_per_tone_dbm']+(r['pin_per_tone_dbm']+small_gain-r['im_noise_corrected_dbfs'])/2 for r in sel]))
    (DATA/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print('COMPLETE',json.dumps(meta,indent=2),flush=True)

if __name__=='__main__':main()
