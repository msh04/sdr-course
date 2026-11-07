function R = make_report()
% Prelab 02, group 6. Analyze real GNU Radio records and make the report plots.
% Run: cd <this folder>; make_report
% Requires base MATLAB (tested with R2021b); no Signal Processing Toolbox.
base=fileparts(mfilename('fullpath')); out=fullfile(base,'out');
figdir=fullfile(out,'matlab'); if ~exist(figdir,'dir'), mkdir(figdir); end
set(groot,'DefaultFigureVisible','off','DefaultAxesFontName','Times New Roman', ...
    'DefaultTextFontName','Times New Roman','DefaultAxesFontSize',10);
T=theory_calculations();
N=readtable(fullfile(out,'noise_repeats.csv'));
gains=(0:10:50)'; A=zeros(numel(gains),6);
for k=1:numel(gains)
    q=N(N.gain_db==gains(k),:); enr=q.enr_db(1);
    off=mean(10.^(q.off_dbfs/10)); on=mean(10.^(q.on_dbfs/10)); y=on/off;
    A(k,:)=[gains(k),enr,10*log10(off),10*log10(on),10*log10(y),enr-10*log10(y-1)];
end
NF=array2table(A,'VariableNames',{'gain_db','enr_db','off_dbfs','on_dbfs','y_db','nf_db'});
P=readtable(fullfile(out,'single_tone_sweeps.csv'));
p1=zeros(size(gains));
for k=1:numel(gains)
    q=P(P.gain_db==gains(k),:);
    q=sortrows(q,'pin_dbm'); ref=q.pout_dbfs(1)-q.pin_dbm(1);
    loss=q.pin_dbm+ref-q.pout_dbfs;
    idx=find(loss>=1,1); assert(~isempty(idx)&&idx>1,'P1dB is not bracketed');
    p1(k)=q.pin_dbm(idx-1)+(1-loss(idx-1))*(q.pin_dbm(idx)-q.pin_dbm(idx-1))/(loss(idx)-loss(idx-1));
end
floor10=-173.98+40+NF.nf_db; dynamic=p1-floor10;
comparison=table(gains,NF.enr_db,NF.y_db,NF.nf_db,p1,floor10,dynamic, ...
 'VariableNames',{'gain_db','enr_db','y_db','nf_db','p1db_input_dbm','noise_floor_10khz_dbm','compression_dynamic_range_db'});
writetable(NF,fullfile(out,'noise_summary.csv'));
writetable(comparison,fullfile(out,'gain_comparison.csv'));
[best,idx]=max(dynamic);
R.group_number=6;R.best_tested_gain_db=gains(idx);R.best_tested_dynamic_range_db=best;
R.noise=table2struct(NF);R.gain_comparison=table2struct(comparison);
R.theory=T;

f=newfigure();
subplot(1,2,1);plot(gains,NF.nf_db,'o-','LineWidth',1.3);
xlabel('Receiver gain (dB)');ylabel('Noise figure (dB)');grid on;
subplot(1,2,2);yyaxis left;
plot(gains,p1,'o-',gains,floor10,'s-','LineWidth',1.3);ylabel('Input P1dB / noise floor (dBm)');
yyaxis right;plot(gains,dynamic,'^-','LineWidth',1.3);ylabel('P1dB - floor (dB)');
xlabel('Receiver gain (dB)');legend('Input P1dB','10 kHz floor','Their difference','Location','southoutside','Orientation','horizontal');grid on;
savefigpng(f,figdir,'gain_tradeoff');

f=newfigure();
for k=1:2
    gain=[0,40]; gain=gain(k);q=P(P.gain_db==gain,:);q=sortrows(q,'pin_dbm');
    ref=q.pout_dbfs(1)-q.pin_dbm(1);subplot(1,2,k);
    plot(q.pin_dbm,q.pout_dbfs,'o-',q.pin_dbm,q.pin_dbm+ref,'--','LineWidth',1.2);
    xlabel('Input power (dBm)');ylabel('Fundamental output (dBFS)');title(sprintf('Gain = %g dB',gain));
    legend('GNU Radio','Small-signal line','Location','northwest');grid on;
end
savefigpng(f,figdir,'single_tone');

two=readtable(fullfile(out,'two_tone.csv')); low=two(two.gain_db==0,:); high=two(two.gain_db==40,:);
mask=low.pin_per_tone_dbm>=-47 & low.pin_per_tone_dbm<=-43;
c=polyfit(low.pin_per_tone_dbm(mask),low.im_noise_corrected_dbfs(mask),1);
ref=P(P.gain_db==0,:);ref=sortrows(ref,'pin_dbm');smallgain=ref.pout_dbfs(1)-ref.pin_dbm(1);
estimate=low.pin_per_tone_dbm(mask)+(low.pin_per_tone_dbm(mask)+smallgain-low.im_noise_corrected_dbfs(mask))/2;
R.iip3.corrected_slope=c(1);R.iip3.extrapolated_dbm=mean(estimate);

f=newfigure();subplot(1,2,1);
plot(low.pin_per_tone_dbm,low.tone_mean_dbfs,'o-',low.pin_per_tone_dbm,low.im_noise_corrected_dbfs,'s-','LineWidth',1.2);
xlabel('Input power per tone (dBm)');ylabel('Output (dBFS)');title('Gain = 0 dB');
legend('Fundamental','IM3, noise subtracted','Location','northwest');grid on;
subplot(1,2,2);
plot(high.pin_per_tone_dbm,high.tone_mean_dbfs,'o-',high.pin_per_tone_dbm,high.im_mean_dbfs,'s-','LineWidth',1.2);
xline(-76.0206,':');xlabel('Input power per tone (dBm)');ylabel('Output (dBFS)');title('Gain = 40 dB');
legend('Fundamental','IM3 band','Clipping onset','Location','southeast');grid on;
savefigpng(f,figdir,'two_tone');

ant=jsondecode(fileread(fullfile(out,'antenna.json')));
target=max(ant.coarse(:,2))-3;
lo=ant.fine(ant.fine(:,1)<1300,:);hi=ant.fine(ant.fine(:,1)>1300,:);
i=find(lo(:,2)>=target,1);fL=lo(i-1,1)+(target-lo(i-1,2))*(lo(i,1)-lo(i-1,1))/(lo(i,2)-lo(i-1,2));
i=find(hi(:,2)<=target,1);fH=hi(i-1,1)+(target-hi(i-1,2))*(hi(i,1)-hi(i-1,1))/(hi(i,2)-hi(i-1,2));
R.antenna=ant;R.antenna.fL=fL;R.antenna.fH=fH;R.antenna.BW=fH-fL;
f=newfigure();
plot(ant.coarse(:,1),ant.coarse(:,2),'o-',ant.fine(:,1),ant.fine(:,2),'.','LineWidth',1.1);yline(target,'--');
xlim([400,3000]);ylim([-110,5]);xlabel('RF-equivalent frequency (MHz)');ylabel('Power transmission (dB)');
legend('20 MHz sweep','1 MHz edge readings','Peak - 3 dB','Location','northeast');grid on;
savefigpng(f,figdir,'antenna_response');
S.group_number=6;
S.nf=table2struct(NF);S.noise_repeats=table2struct(N);S.sweep1=table2struct(P);
S.two=table2struct(two);S.gain_comparison=table2struct(comparison);
fid=fopen(fullfile(out,'sim_results.json'),'w','n','UTF-8');fwrite(fid,jsonencode(S),'char');fclose(fid);
assert(abs(R.iip3.corrected_slope-3)<.05);
assert(abs(R.iip3.extrapolated_dbm+25)<.1);

assert(isequal(gains,(0:10:50)'));
assert(R.best_tested_gain_db==10);
fid=fopen(fullfile(out,'analysis_results.json'),'w','n','UTF-8');fwrite(fid,jsonencode(R),'char');fclose(fid);
write_html(R,fullfile(base,'..','prelab.html'));
fprintf('Group %d: best tested gain %.0f dB; range %.4f dB\n',R.group_number,R.best_tested_gain_db,R.best_tested_dynamic_range_db);
fprintf('IIP3 %.4f dBm; corrected slope %.5f\n',R.iip3.extrapolated_dbm,R.iip3.corrected_slope);
fprintf('Measured antenna %.4f .. %.4f MHz; bandwidth %.4f MHz\n',fL,fH,fH-fL);
end

function f=newfigure()
f=figure('Color','w','Position',[50,50,1050,380]);
end
function savefigpng(f,folder,name)
exportgraphics(f,fullfile(folder,[name '.png']),'Resolution',200);close(f);
end
function write_html(R,path)
fid=fopen(path,'w','n','UTF-8');c=onCleanup(@()fclose(fid));
fprintf(fid,'<!doctype html><html lang="en"><meta charset="utf-8"><title>Lab 2 pre-lab report, Group 6</title>');
fprintf(fid,'<style>body{font:16px/1.6 Georgia,serif;max-width:900px;margin:40px auto;padding:20px}table{border-collapse:collapse;width:100%%}td,th{border:1px solid #444;padding:6px}img{width:100%%}</style>');
fprintf(fid,'<h1>Lab 2 pre-lab report</h1><p>Group 6</p><p><a href="main.pdf">Full report (PDF)</a> | <a href="main.tex">LaTeX source</a></p>');
fprintf(fid,'<h2>1. Summary of concepts</h2><p>Noise figure measures the loss of signal-to-noise ratio. In the Y-factor method, gain and bandwidth cancel in the on/off power ratio. IIP3 predicts the third-order products from the extended small-signal lines.</p>');
fprintf(fid,'<h2>2. Theory questions</h2><p>Noise temperatures for NF of 1, 3, 6 and 10 dB are 75.088, 288.626, 864.511 and 2610 K. The chain noise figure is %.6f dB with the amplifier first and %.6f dB with the filter first. Derivations of the Y-factor relation, error sensitivity, third-order relations and SFDR are in the PDF.</p>',R.theory.friis.nf_lna_first_db,R.theory.friis.nf_filter_first_db);
fprintf(fid,'<h2>3. Measurement design</h2><p>For NF near 7 and 30 dB, ENR is 15 and 35 dB. We average for at least 0.1 s. Tones at 300 and 400 kHz give products at 200 and 500 kHz. The chosen power at zero gain is -43 dBm per tone. The hardware limit is -10 dBm total power.</p>');
fprintf(fid,'<h2>4. Receiver model simulation</h2><table><tr><th>Gain (dB)</th><th>NF (dB)</th><th>P1dB (dBm)</th><th>10 kHz floor (dBm)</th><th>Gap (dB)</th></tr>');
for row=R.gain_comparison',fprintf(fid,'<tr><td>%.0f</td><td>%.3f</td><td>%.3f</td><td>%.3f</td><td>%.3f</td></tr>',row.gain_db,row.nf_db,row.p1db_input_dbm,row.noise_floor_10khz_dbm,row.compression_dynamic_range_db);end
fprintf(fid,'</table><p>The largest gap among the requested gains is %.3f dB at gain %.0f dB. IIP3 is %.2f dBm and the product slope is %.4f. At gain 40 dB, ADC clipping causes the sudden product increase.</p>',R.best_tested_dynamic_range_db,R.best_tested_gain_db,R.iip3.extrapolated_dbm,R.iip3.corrected_slope);
for name={'single_tone','two_tone','gain_tradeoff'},fprintf(fid,'<img src="figures/%s.png" alt="%s">',name{1},strrep(name{1},'_',' '));end
fprintf(fid,'<h2>5. Antenna response</h2><p>The original program gives fL = %.2f MHz, fH = %.2f MHz and BW = %.2f MHz. The seller lists 2400 to 2500 MHz. Other band limits are not stated.</p>',R.antenna.fL,R.antenna.fH,R.antenna.BW);
fprintf(fid,'<img src="figures/antenna_response.png" alt="Antenna model response">');
fprintf(fid,'<h2>6. Predictions</h2><p>For NF = 7 dB and ENR = 15 dB, Y = 8.639 dB. A matched 10 dB attenuator at the reference temperature adds 10 dB to the chain noise figure. A 2 dB rise per tone gives a 6 dB product rise in the third-order region. The real receiver is ADALM-PLUTO with a 12-bit ADC. At an assumed 800 MHz and room temperature, we predict about 3 dB NF at maximum gain, using the AD9363 typical value of 2.5 dB as a reference and allowing for board input loss. A 20 dB gain reduction generally raises NF, but the change depends on the gain stages. Input P1dB rises by about 10 dB for a 10 dB gain reduction only if ADC clipping is the limit. The 9.6 dB IIP3-to-P1dB gap is not guaranteed. The assigned group gain has not been announced. The offline simulation remains the supplied 8-bit model.</p>');
fprintf(fid,'<h2>7. Likely mistakes</h2><p>Excess input power: calculate the total level and use enough attenuation. Invalid Y readings: turn AGC off, fix the gain and avoid compression. False IIP3: check the product slope and the two-tone source.</p></html>');
end
