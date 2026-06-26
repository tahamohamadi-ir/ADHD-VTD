# Artifact Rules

## Never cite as final result

Do not cite:

- smoke runs,
- partial runs,
- failed runs,
- config-only files,
- placeholder reranker runs,
- mock judge outputs,
- pilot judge if full judge exists,
- deterministic template pack as main model result.

## Required files for a valid benchmark run

A valid run must include:

- config file
- predictions
- benchmark results
- summary json
- summary md
- failures if any
- manifest entry

## Required consistency checks

The artifact verifier must check:

1. prediction count matches summary total
2. failure count matches summary failures
3. valid SQL count matches predictions
4. EX numerator/denominator matches predictions
5. unsafe SQL count matches predictions
6. config flags match summary
7. deterministic_templates flag is explicit
8. dataset hash is present
9. selected cases hash is present
10. run is not marked smoke unless cited as smoke

## Paper table rule

All paper tables must be generated from artifacts.

Never manually edit final paper numbers.