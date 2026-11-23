# news-image-20261123

[![make.fun — news-image-20261123](https://make.fun/badge/news-image-20261123.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![rank](https://make.fun/badge/news-image-20261123/veldopratama7-sudo/news-image-20261123/rank.svg)](https://make.fun/bounty/news-image-20261123/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)
[![reward](https://make.fun/badge/news-image-20261123/veldopratama7-sudo/news-image-20261123/reward.svg)](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123)

A poster-style newspaper front page that sums up Monday 23 November 2026's world news in one image, drawn entirely in code: a serif masthead, the day's key numbers, a UTC timeline, three hero stories with drawn scenes, twelve story cards with mini illustrations, a pin-map of where it happened, briefs with sources, and a date check — 39 stories across 7 regions, every one dated, each with its source.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

The program is standard-library-only Python 3.13, deterministic (no clock, no randomness, no network), runs twice and writes the same `/output/entry.png` both times: a 1024x1024 PNG under 1 MiB.

---

<sub>Entered on [make.fun](https://make.fun/bounty/news-image-20261123?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261123) for its “Sum up 23 November's world news in one image” bounty.</sub>
