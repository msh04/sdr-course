# SDR Course Materials

An English static website with exactly three tabs:

- Lab Instructions
- Pre-Lab Reports
- Lab Reports

Files are added to the repository and linked from their corresponding section. Visitors can download them directly. No accounts, backend, database, external SDK, or cloud storage service is required.

## Add course files

Use the following folders:

- files/lab-instructions/
- files/pre-lab-reports/
- files/lab-reports/

When a document is supplied, copy it into the relevant folder, add a descriptive title and a relative download link inside that section's .files container in index.html, and update the file count. Remove the empty-state block once that section contains documents. Escape any HTML characters in titles and percent-encode the filename in the link when necessary. Preserve the original file content.

On GitHub Pages, published documents are available to visitors without signing in. Only publish course files intended to be shared.

## Preview

Open index.html directly, or serve this folder:

```sh
python -m http.server 8080 --bind 127.0.0.1
```

Open http://localhost:8080/. The tabs support mouse, touch, Left/Right arrow keys, Home, and End. Without JavaScript, all three sections remain visible and document links still work.

## GitHub Pages

Upload this folder's contents to the root of main in the public sdr-course repository. In Settings > Pages, choose Deploy from a branch, main, and /(root). No build is required.

Repository: https://github.com/msh04/sdr-course


## Prelab 2 — Group 06

[Prelab2.pdf](files/pre-lab-reports/prelab2/Prelab2.pdf), 10 Python/MATLAB/GNU Radio code and flowgraph files, and 15 CSV/JSON simulation data files are available in the Pre-Lab Reports tab. The download bundle includes these 26 files. Images, fonts, HTML and LaTeX source are excluded.
