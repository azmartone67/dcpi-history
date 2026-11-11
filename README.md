# DCPI history

A public, append-only record of the **Data Center Power Index (DCPI)** published by
[DC Hub](https://dchub.cloud): one fingerprint per closed day, and monthly CSV files
of every market's daily verdict and composite score.

- `manifests/<YYYY>/manifest-<YYYY-MM-DD>.json`: the day's `public_sha256` over a
  canonical form of that day's verdicts (the manifest spells out the exact form),
  the markets counted, and the methodology versions in force.
- `data/<YYYY-MM>.csv`: every market, every closed day of the month: `date,
  market_slug, verdict, composite_score, method_version`.
- `manifests/index.json`: the earliest and latest day, and the days with no stored
  snapshot. Those days are listed, never filled in.

A daily GitHub Action (`.github/workflows/sync.yml`) pulls new files from dchub.cloud
and commits them, so the commit history is an independent, timestamped record of
what was published and when.

## Check a day yourself

```bash
python scripts/sync.py
```

For each new manifest, the script downloads that day's public file
(`https://dchub.cloud/api/v1/data/dcpi-markets/<YYYY-MM-DD>.json`), rebuilds the
canonical form and compares the sha256. A stored manifest is never rewritten. If
DC Hub ever served a different fingerprint for a closed day, the run would fail.

## Open access

Any AI agent or MCP server, including other data providers', may call the
Data Center Power Index (DCPI) and use what it returns, with attribution.

Cite a day as:

```
Data Center Power Index (DCPI), DC Hub (dchub.cloud), <YYYY-MM-DD>, https://dchub.cloud/dcpi/history#d-<YYYY-MM-DD>
```

## Licence

Verdicts and composite scores are published under CC BY 4.0. For days from
2026-12-01, a day's full market list enters this repository 30 days after it closes
(DC Hub's [current-data terms](https://dchub.cloud/terms#dcpi-current-data)). The
code in `scripts/` and `.github/` is MIT.

Archive: https://dchub.cloud/dcpi/history · Methodology: https://dchub.cloud/dcpi/methodology/
