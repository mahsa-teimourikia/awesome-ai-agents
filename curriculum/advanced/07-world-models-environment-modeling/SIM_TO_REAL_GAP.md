# Deep Dive: Sim-to-Real Gap, Calibration, and Drift

A model can predict success while the real system fails because its state, structure, parameters, or disturbances differ from production. This is the sim-to-real gap.

## Validate before simulation

The lab does not compress applicability into a confidence score. `assess_model_validity()` checks:

- model, snapshot, and sensor age;
- input-state digest and tenant binding;
- required variables and units;
- sensor quality (`GOOD`, `DELAYED`, `MISSING`, `NOISY`, `UNTRUSTED`); and
- each variable's validated range.

It returns `VALID`, `DEGRADED`, `STALE`, `OUT_OF_DISTRIBUTION`, or `UNVALIDATED` with explicit reasons. Black Friday traffic outside the calibrated range is `MODEL_OUT_OF_DOMAIN`, not “lower confidence and continue.”

## Measure material error

Percentage error alone is misleading. A 1 ms prediction followed by 2 ms is 100% relative error but may be operationally irrelevant. A 10 ms prediction followed by 4,200 ms has large absolute error and can cross an SLO.

Track absolute error, relative error, SLO impact, interval coverage, decision sensitivity, and whether the recommended ranking would change. For event predictions, track Brier score or another proper scoring rule.

## Calibrate without silent self-modification

After independently authorized execution, trusted observations produce `ObservedOutcome`. The application stores prediction error and calibration records. Candidate models run in shadow mode and backtest against historical scenarios.

```text
prediction -> observed outcome -> error -> update proposal
-> backtest -> validation report -> staged promotion or rejection
```

The agent does not silently rewrite the active model, and an untrusted or broken sensor cannot become calibration truth. Versions remain immutable so decisions can be reproduced and rolled back.
