# Differences from the published figure - guo2019_melanoma_roc

Guo W, et al. (2019). eLife 8:e44310. https://doi.org/10.7554/eLife.44310

Classification: **publication-grade recreation of the ROC-curve KIND; same kind, not pixel-identical.**

- The AUC matches exactly (published 0.822; app 0.8223 -> 0.822).
- The paper annotates P < 0.001 and the 95%CI (0.76-0.88) as text; the app shows the AUC in the legend and does not draw the CI/P (it never fabricates a statistic it did not compute).
- The paper draws a smooth ROC; the app draws the empirical step ROC (where='post'). Same curve, different interpolation.
- Colours, fonts and limits are Make My Figure Publication defaults.
