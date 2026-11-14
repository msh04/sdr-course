Lab 2 pre-lab report, Group 6

main.pdf: English report
main.tex and First Page.tex: XeLaTeX sources
fonts: XB Zar fonts
prelab.html: complete HTML report
figures: single-tone and two-tone figures
files: GNU Radio flowgraphs, finite simulation, MATLAB analysis, CSV results

Compile twice with XeLaTeX:
  xelatex main.tex
  xelatex main.tex

To repeat the offline simulation in a radioconda command prompt:
  python sim_measure.py
Then run make_report in MATLAB from the files directory.
MATLAB R2021b was used, without additional toolboxes.

lab02_sim.grc uses the instructor's receiver model, with the flowgraph ID
set to lab02_sim. lab02_sim.py is the generated Python program.
The offline model has an 8-bit ADC and a sample rate of 2.048 MHz.

lab02_combined.grc and lab02_combined.py are prepared for the real Pluto:
2.4 MHz sampling, manual gain, noise band centred at -700 kHz, cable loss
0.5 dB, Pmax 7 dBm. An empty IIO URI selects the locally connected device.
If necessary, set both Pluto blocks to your device URI in GNU Radio Companion.
Start with TX attenuation 89.75 dB and both amplitudes zero.
For tones, set a_tone to 0.9; two-tone mode uses 0.45 for each tone.
For noise, set a_noise to 0.01. The slider minimum is 18 dB; noise mode
also clamps the actual TX attenuation to at least 30 dB. The actual
attenuation is displayed and is used in the power and ENR estimates.
The I/Q recording block and its controls have been removed.
The hardware flowgraph was compiled and checked without transmitting.

The final PDFs, not the older .tex files supplied in the same folder,
define the report requirements. The guide's 15 dB single-tone minimum is
inconsistent with its worst-case parameters; the calculation requires
17.08485 dB. The prepared flowgraph therefore uses 18 dB as the tone minimum.
Only the four pre-lab tasks are included. No lab measurements are invented.
