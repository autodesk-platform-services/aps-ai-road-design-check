# Comparison Rubric

## Status assignment

| Status | When to use |
|---|---|
| `pass` | Design value satisfies the retrieved threshold without ambiguity. |
| `fail` | Design value violates the retrieved threshold without ambiguity. |
| `needs_review` | The clause uses conditional language ("unless otherwise approved", "typically", "may"), requires engineering judgment, or the comparison is valid but a human should confirm. |
| `not_applicable` | No retrieved clause covers this parameter, or the clause explicitly excludes this design class. |

## Confidence assignment

| Confidence | When to use |
|---|---|
| `high` | The clause unambiguously states a numeric threshold; comparison was direct arithmetic. No unit conversion was required, or conversion factor is universally agreed (e.g. ft → m). |
| `medium` | The clause uses conditional language, OR a unit conversion was required beyond trivial SI/imperial, OR the design value required rounding or interpolation to match the standard speed class. |
| `low` | The clause is vague, partially applicable, or required semantic inference. The retrieved text does not state a threshold directly. |

## Remediation rules

- Only provide `remediation` when `status` is `fail`.
- Every remediation must cite the specific clause (`clause_id`, `section`) that defines the corrective target.
- State the required corrective action concretely: e.g. "Increase radius from 185 ft to at least 350 ft per Section 4.2.1-A."
- Do not recommend values that are not stated or clearly derivable from a retrieved clause.
