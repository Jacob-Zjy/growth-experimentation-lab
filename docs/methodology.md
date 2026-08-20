# Methodology notes

## 1. SRM

Sample Ratio Mismatch compares observed arm counts with the planned allocation using a
chi-square statistic. It is an instrumentation and assignment diagnostic, not a test of
campaign effectiveness.

## 2. Standardized mean difference

For a pre-treatment covariate X:

```text
SMD = (mean_treatment - mean_control) / sqrt((var_treatment + var_control) / 2)
```

Absolute values below 0.10 are a common diagnostic rule, not a theorem.

## 3. Intent-to-treat effect

The project compares users by assigned arm, regardless of whether an email was opened.
Conditioning on exposure/opening would introduce post-treatment selection.

## 4. Binary and continuous outcomes

- Visits/conversion: two-proportion Z test and rate-difference confidence interval.
- Revenue: Welch test because variances may differ and the distribution is zero-inflated.

P-values are not effect sizes. Every decision table includes arm means, absolute lift,
relative lift, confidence interval, and multiplicity-adjusted p-value.

## 5. Benjamini-Hochberg

Nine planned hypotheses create multiple-testing risk. BH controls the expected false
discovery proportion among rejected hypotheses and is less conservative than Bonferroni.

## 6. Power and MDE

The project solves backward from realized n to the smallest rate increase detectable at
80% power and alpha 0.05. MDE connects statistical uncertainty to business relevance.

## 7. CUPED

CUPED subtracts the outcome component predictable from pre-treatment covariates:

```text
Y_adjusted = Y - (prediction(X_pre) - mean(prediction(X_pre)))
```

Randomization keeps the expected treatment effect unchanged, while variance falls only
when X_pre predicts Y. Weak variance reduction is therefore an informative result.

## 8. S-, T-, and X-learners

- S-learner: one outcome model with treatment as a feature.
- T-learner: separate treated and control outcome models.
- X-learner: imputes treatment effects within each arm and learns those effects with two
  second-stage regressors, then combines them using the treatment propensity.

The project models visit uplift because visit has enough positive labels for stable
ranking. It does not pretend that visit and profit are the same outcome.

## 9. Qini and AUUC

Users are sorted by predicted uplift. A useful model accumulates incremental outcomes
faster than random targeting. Ordinary ROC-AUC cannot evaluate this objective because it
ranks outcome probability, not the counterfactual difference between treatment states.

## 10. Offline policy value

Policy curves use inverse-propensity weighting. Both the uplift model and target share are
selected using validation data; test outcomes only evaluate that fixed policy. Contact
cost includes delivery and the opportunity cost of a limited customer-contact slot;
both it and value per incremental visit are explicit scenario inputs. The default
scenario uses $5.00 per incremental visit and $0.50 per contacted user. The output is an
offline estimate, not a deployment claim.
