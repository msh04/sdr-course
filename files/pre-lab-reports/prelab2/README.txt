Lab 2 pre-lab report, Group 6

Prelab2.pdf: final English report
fonts: XB Zar font files
figures: the four report figures
prelab.html: HTML report
files: GNU Radio code, MATLAB analysis and recorded data

To analyse the included data, run make_report from the files directory
in MATLAB. MATLAB R2021b was used; no Signal Processing Toolbox is needed.
The analysis uses only the requested gains 0, 10, 20, 30, 40 and 50 dB.

To repeat the acquisitions in radioconda with GNU Radio 3.10:
  python sim_measure.py
  python antenna_measure.py
Then run in MATLAB:
  make_report

The hardware flowgraph is prepared but has not been run on a receiver.
The real receiver model and the assigned group gain have not been announced.
