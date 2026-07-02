# Statistics example: survival_km

Survival data for two arms (Standard/Experimental), 40 patients each, with administrative censoring.

Design: right-censored survival. Default: log-rank test comparing the two curves. A Cox model (hazard ratio) is available; its proportional-hazards assumption is not auto-checked.

Required columns: `time_months` (numeric), `event` (1=event, 0=censored), `group` (categorical).

All data are SYNTHETIC (fixed seed) and not real measurements.
