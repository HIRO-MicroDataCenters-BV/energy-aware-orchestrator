# S0 run 1 (2026-11-17 15:22:08-16:27:08 UTC): interrupted by host sleep, not used for KPIs

The macOS host slept during the run (`pmset -g log`, times CET):

- 16:59:54 Idle Sleep (3 s), 17:00:07 Maintenance Sleep until 17:09:49 DarkWake
- 17:12:49 Maintenance Sleep until 17:27:50 DarkWake

The Docker VM, and with it the kind cluster, Kepler and Prometheus, was frozen
during these windows. The harness sampled nothing from t = 2280 s to 2861 s.
o3-optional ran 9 min 47 s instead of about 8 min. Prometheus has gaps.

Data from t = 0 to about 2270 s (normal phase, the whole contingency window,
start of recovery) is unaffected and kept here for reference. KPIs and figures
use the re-run in `../S0_baseline/`, which was started with `caffeinate -i -s`
keeping the host awake.
