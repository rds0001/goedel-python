# Contributing

A change to syntax, coding, proof rules or status semantics must update its versioned
contract, independent examples and both language implementations. Supply negative
cases for altered rules and binders. Do not promote a mathematical claim without
precise hypotheses, a source locator and independent review. Run the checks in
docs/DEVELOPMENT.md before proposing a change.

## Test runtime

The default test suite skips full arithmetic fixed-point constructions. GitHub CI
always skips these large cases, including when `GOEDEL_RUN_LARGE_TESTS` is set.
Small syntax, coding, proof-checking and wrapper-composition tests remain active.
For an explicitly requested local research run only, use
`GOEDEL_RUN_LARGE_TESTS=1 python -m pytest tests/test_fixedpoint.py` inside a worker
with operating-system memory and CPU/wall-time limits. A skipped or interrupted
construction is not a successful verification. Installation smoke tests do not
construct full arithmetic fixed points.
