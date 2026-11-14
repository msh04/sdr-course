function R = make_report()
% Lab 2 pre-lab, group 6. Run after sim_measure.py in radioconda.
% Base MATLAB is sufficient. Only the single-tone and two-tone plots are made.
base=fileparts(mfilename('fullpath')); out=fullfile(base,'out');
figdir=fullfile(base,'..','figures'); if ~exist(figdir,'dir'), mkdir(figdir); end
set(groot,'DefaultFigureVisible','off','DefaultAxesFontName','Times New Roman', ...
    'DefaultTextFontName','Times New Roman','DefaultAxesFontSize',10);
N=readtable(fullfile(out,'noise_repeats.csv')); gains=(0:10:50)'; A=zeros(6,6);
for k=1:numel(gains)
    q=N(N.gain_db==gains(k),:); enr=q.enr_db(1);
    off=mean(10.^(q.off_dbfs/10)); on=mean(10.^(q.on_dbfs/10)); y=on/off;
    A(k,:)=[gains(k),enr,10*log10(off),10*log10(on),10*log10(y),enr-10*log10(y-1)];
end
NF=array2table(A,'VariableNames',{'gain_db','enr_db','off_dbfs','on_dbfs','y_db','nf_db'});
P=readtable(fullfile(out,'single_tone_sweeps.csv')); p1=zeros(6,1);
for k=1:numel(gains)
    q=sortrows(P(P.gain_db==gains(k),:),'pin_dbm');
    ref=q.pout_dbfs(1)-q.pin_dbm(1); loss=q.pin_dbm+ref-q.pout_dbfs;
    idx=find(loss>=1,1); assert(~isempty(idx)&&idx>1,'P1dB is not bracketed');
    p1(k)=q.pin_dbm(idx-1)+(1-loss(idx-1))*(q.pin_dbm(idx)-q.pin_dbm(idx-1))/(loss(idx)-loss(idx-1));
end
floor10=-173.98+40+NF.nf_db; dynamic=p1-floor10;
comparison=table(gains,NF.enr_db,NF.y_db,NF.nf_db,p1,floor10,dynamic, ...
    'VariableNames',{'gain_db','enr_db','y_db','nf_db','p1db_input_dbm','noise_floor_10khz_dbm','compression_dynamic_range_db'});
writetable(NF,fullfile(out,'noise_summary.csv'));
writetable(comparison,fullfile(out,'gain_comparison.csv'));
[best,idx]=max(dynamic); R.group_number=6;
R.best_tested_gain_db=gains(idx); R.best_tested_dynamic_range_db=best;
R.noise=table2struct(NF); R.gain_comparison=table2struct(comparison);

f=newfigure();
for k=1:2
    gg=[0,40]; gg=gg(k); q=sortrows(P(P.gain_db==gg,:),'pin_dbm');
    ref=q.pout_dbfs(1)-q.pin_dbm(1); subplot(1,2,k);
    plot(q.pin_dbm,q.pout_dbfs,'o-',q.pin_dbm,q.pin_dbm+ref,'--','LineWidth',1.2);
    xlabel('Input power (dBm)'); ylabel('Fundamental output (dBFS)'); title(sprintf('Gain = %g dB',gg));
    legend('GNU Radio','Small-signal line','Location','northwest'); grid on;
end
saveplot(f,figdir,'single_tone');

two=readtable(fullfile(out,'two_tone.csv')); low=two(two.gain_db==0,:); high=two(two.gain_db==40,:);
mask=low.pin_per_tone_dbm>=-47 & low.pin_per_tone_dbm<=-43;
c=polyfit(low.pin_per_tone_dbm(mask),low.im_noise_corrected_dbfs(mask),1);
ref=sortrows(P(P.gain_db==0,:),'pin_dbm'); smallgain=ref.pout_dbfs(1)-ref.pin_dbm(1);
est=low.pin_per_tone_dbm(mask)+(low.pin_per_tone_dbm(mask)+smallgain-low.im_noise_corrected_dbfs(mask))/2;
R.iip3.corrected_slope=c(1); R.iip3.extrapolated_dbm=mean(est);
R.im3_onset_gain40_dbm=-30-40-20*log10(2);
f=newfigure(); subplot(1,2,1);
plot(low.pin_per_tone_dbm,low.tone_mean_dbfs,'o-',low.pin_per_tone_dbm,low.im_noise_corrected_dbfs,'s-','LineWidth',1.2);
xlabel('Input power per tone (dBm)'); ylabel('Output (dBFS)'); title('Gain = 0 dB');
legend('Fundamental','IM3, noise subtracted','Location','northwest'); grid on;
subplot(1,2,2);
plot(high.pin_per_tone_dbm,high.tone_mean_dbfs,'o-',high.pin_per_tone_dbm,high.im_mean_dbfs,'s-','LineWidth',1.2);
xline(R.im3_onset_gain40_dbm,':'); xlabel('Input power per tone (dBm)'); ylabel('Output (dBFS)'); title('Gain = 40 dB');
legend('Fundamental','IM3 band','Clipping onset','Location','southeast'); grid on;
saveplot(f,figdir,'two_tone');

% Task 4: use the real Pluto level assumptions given in the final guide.
pmax=7; apad=.5; fs=2.4e6; a1=.9; a2=.45; an=.01;
c1=pmax+20*log10(a1)-apad; c2=pmax+20*log10(a2)-apad;
cn=pmax+20*log10(an)-10*log10(fs)-apad+174;
c1worst=8+20*log10(a1); c2worst=8+20*log10(a2);
up=@(x)ceil((x-1e-10)*4)/4;
minone=c1worst+10; mintwo=c2worst+10*log10(2)+10;
names={'Single-tone minimum attenuation';'Two-tone minimum attenuation';'Two-tone envelope peak'; ...
    'Calibration tone';'ENR 15 dB';'ENR 25 dB';'Single tone gain 40 start'; ...
    'Single tone gain 40 end';'Single tone gain 50 start';'Single tone gain 50 end'; ...
    'Two tones gain 40 start, per tone';'Two tones gain 40 end, per tone'};
exact=[minone;mintwo;NaN;60;cn-15;cn-25;c1+50;c1+15;c1+60;c1+25;c2+38;c2+22];
setting=up(exact); setting(3)=setting(2);
value=[c1worst-setting(1);c2worst-setting(2)+10*log10(2); ...
    c2worst-setting(3)+20*log10(2);c1-setting(4);cn-setting(5);cn-setting(6); ...
    c1-setting(7);c1-setting(8);c1-setting(9);c1-setting(10);c2-setting(11);c2-setting(12)];
kind={'Total power, worst case';'Total mean power, worst case';'Envelope peak, worst case'; ...
    'Tone input power';'ENR';'ENR';'Tone input power';'Tone input power'; ...
    'Tone input power';'Tone input power';'Input power per tone';'Input power per tone'};
levels=table(names,exact,setting,value,kind,'VariableNames', ...
    {'quantity','attenuation_exact_db','attenuation_setting_db','level_db','level_kind'});
writetable(levels,fullfile(out,'design_levels.csv'));
R.design=struct('pmax_dbm',pmax,'cable_loss_db',apad,'fs_hz',fs,'single_constant_dbm',c1, ...
    'two_constant_dbm',c2,'noise_constant_db',cn,'minimum_single_attenuation_db',minone, ...
    'minimum_two_attenuation_db',mintwo,'minimum_rx_gain_db',32,'levels',table2struct(levels));
prednames={'NF at gain 50';'NF at gain 40';'NF at gain 30';'Input P1dB at gain 40'; ...
    'Input P1dB at gain 50';'IM3 onset at gain 40, per tone'};
pred=[NF.nf_db(6);NF.nf_db(5);NF.nf_db(4);p1(5);p1(6);R.im3_onset_gain40_dbm];
unit={'dB';'dB';'dB';'dBm';'dBm';'dBm'}; measured=repmat({''},6,1);
predictions=table(prednames,pred,unit,measured,'VariableNames',{'quantity','prediction','unit','measured'});
writetable(predictions,fullfile(out,'predictions.csv')); R.predictions=table2struct(predictions);
% A 2 dB overestimate of Pmax produces these signed estimation errors.
R.calibration_error_db=struct('enr',2,'nf_y_factor',2,'g_fs',-2,'nf_direct',2,'iip3',2);
fid=fopen(fullfile(out,'analysis_results.json'),'w','n','UTF-8');
fwrite(fid,jsonencode(R),'char'); fclose(fid);
fprintf('Group 6: best tested gain %.0f dB, gap %.4f dB\n',R.best_tested_gain_db,best);
fprintf('IIP3 %.4f dBm; IM3 slope %.5f\n',R.iip3.extrapolated_dbm,c(1));
fprintf('Minimum calculated TX attenuation: single %.5f dB, two %.5f dB\n',minone,mintwo);
end
function f=newfigure()
f=figure('Color','w','Position',[50,50,1050,380]);
end
function saveplot(f,folder,name)
exportgraphics(f,fullfile(folder,[name '.png']),'Resolution',200); close(f);
end
