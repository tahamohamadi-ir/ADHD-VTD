# DATASET_CARD.md Draft - VTD Health Intelligent Dashboard NL2SQL Dataset

## Dataset Name

VTD Health Intelligent Dashboard Persian NL2SQL Dataset

## Version

v1.0 / aligned with PARS-SQL v2.3 execution-ready roadmap

## Database

```text
vtd_health_research_v1.db
SQLite dialect
```

## Composition

```text
400 SQL-positive NL2SQL examples
100 behavioral evaluation examples
500 total items
```

## Intended Use

- Persian Text-to-SQL evaluation
- few-shot / golden example retrieval
- local LLM benchmarking
- safety, ambiguity, abstention, and chart/storytelling evaluation
- synthetic fine-tuning seed data if allowed by project policy

## Not Intended For

- real clinical diagnosis
- individual medical decision-making
- direct deployment without expert validation
- cloud API evaluation with private or identifiable patient data

## Data Origin

Document whether the data is:

```text
[ ] synthetic
[ ] de-identified
[ ] manually authored
[ ] generated with LLM assistance
[ ] reviewed by domain expert
```

## Annotation Process

Current status:

```text
Primary author-created benchmark.
At least 50 items must be reviewed by a second reviewer or independent LLM-as-judge before paper submission.
Report Cohen's Kappa or agreement percentage.
```

## Known Limitations

- Some benchmark items may be single-annotator.
- Gold SQL must be audited against the current schema.
- Behavioral examples should not be mixed with SQL-positive EX evaluation.
- Persian colloquial, Finglish, and Jalali date coverage must be stress-tested separately.

## Clinical Safety Disclaimer

This dataset and system are for research and educational analytics only. The system does not provide diagnosis, treatment, triage, or clinical recommendations.
