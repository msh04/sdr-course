function T = theory_calculations()
% Prelab 02, group 6: analytical calculations, using base MATLAB only.
% Units: power gains and noise factors are linear; NF/ENR are in dB.
out = fullfile(fileparts(mfilename('fullpath')), 'out');
if ~exist(out,'dir'), mkdir(out); end
T.group_number = 6;
T.reference_temperature_K = 290;
nf = [1;3;6;10]; factor = 10.^(nf/10);
T.noise_temperature = table(nf,factor,290*(factor-1), ...
    'VariableNames',{'nf_db','noise_factor','temperature_K'});
L = 10^(3/10); G = 10^(20/10); F1 = 10^(1/10); F3 = 10^(15/10);
T.friis.F_lna_first = F1+(L-1)/G+(F3-1)/(G/L);
T.friis.F_filter_first = L+(F1-1)*L+(F3-1)/(G/L);
T.friis.nf_lna_first_db = 10*log10(T.friis.F_lna_first);
T.friis.nf_filter_first_db = 10*log10(T.friis.F_filter_first);
NF = [6;25]; ENR = 15*ones(size(NF)); Y=1+10.^((ENR-NF)/10);
y = 10*log10(Y);
errPlus = ENR-10*log10(10.^((y+.1)/10)-1)-NF;
errMinus = ENR-10*log10(10.^((y-.1)/10)-1)-NF;
T.sensitivity = table(NF,ENR,Y,y,-Y./(Y-1),errPlus,errMinus, ...
    'VariableNames',{'nf_db','enr_db','y_linear','y_db','derivative','nf_error_plus_db','nf_error_minus_db'});
B=[200000;10000]; floor=-174+8+10*log10(B); sfdr=2/3*(-10-floor);
T.sfdr=table(B,floor,sfdr,'VariableNames',{'bandwidth_hz','noise_floor_dbm','sfdr_db'});
T.iip3_minus_p1db_db=-10*log10(1-10^(-1/20));
T.averaging.minimum_tau_400khz_s=(10/log(10)/.05)^2/400000;
T.prediction.y_nf7_enr15_db=10*log10(1+10^((15-7)/10));
T.prediction.attenuator10_nf_increase_db=10;
T.prediction.im3_increase_for_2db_input_db=6;
T.design.two_tone_max_per_tone_dbm=-10-10*log10(2);
T.design.enr_nf7_db=15; T.design.enr_nf30_db=35;
writetable(T.noise_temperature,fullfile(out,'theory_noise_temperature.csv'));
writetable(T.sensitivity,fullfile(out,'theory_sensitivity.csv'));
writetable(T.sfdr,fullfile(out,'theory_sfdr.csv'));
fid=fopen(fullfile(out,'theory_results.json'),'w','n','UTF-8');
cleanup=onCleanup(@() fclose(fid));
fwrite(fid,jsonencode(T),'char');
assert(abs(T.friis.nf_lna_first_db-2.7413076421534)<1e-10);
assert(abs(T.sfdr.sfdr_db(2)-77.3333333333333)<1e-10);
end
