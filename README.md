# CCSP on legitimacy

Research artifact for the Stage 1 proposal "Knowing When to Stop Reading: A Computational Test of Saturation Rules for Construct Definition," Organization Science special issue "AI Enabled Frontiers in Organizational Science."

The Computational Construct Saturation Protocol reads a construct's literature in publication order, keeps a structured record of the construct, measures whether it is still changing, proposes a stop when it is not, and then tries to break the stop. This repository runs it end to end on organizational legitimacy and reports every result, including the ones that did not work. See `results.md` for the findings and `APPENDIX.md` for the technical appendix.

## Reproduce the reported replay without any API key

    /opt/anaconda3/bin/python3 -m pip install -r requirements.txt sentence-transformers
    python3 stage10_variants.py      # chronological replay, 2010 freeze, counter batch, variants, orders
    python3 stage11_tolerance.py     # tolerance parameter, holdout injection

Both run from the cached records in `runs/stage7_*` and the codebook in `data/corpus/codebook.json`, in minutes, on a laptop.

## Rerun the pipeline from the start

Requires `ANTHROPIC_API_KEY` in `.env` (copy `.env.example`). OpenAlex needs no key.

    python3 stage1_retrieve.py            # anchors -> candidates (OpenAlex)
    python3 stage2_screen.py --model claude-haiku-4-5 --direct --tag haiku_full
    python3 stage2_screen.py --model claude-opus-5 --direct --from-run stage2_haiku_full --tag opus_stage2
    python3 stage3_chain.py               # second chaining round
    python3 stage4_recover_abstracts.py   # abstracts for title only papers
    python3 stage5_freeze.py              # freeze, holdout, hashes
    python3 stage7_extract.py --tier abstract
    python3 stage7_extract.py --tier fulltext   # only for PDFs present in Zotero
    python3 stage9_codebook.py && python3 stage9b_dimension_families.py
    python3 stage10_variants.py && python3 stage11_tolerance.py

## Layout

- `declaration/` the inclusion rule and anchor list, committed before any result
- `data/corpus/` frozen corpus, sealed holdout ids, codebook, SHA 256 hashes (`FREEZE.json`)
- `runs/` audit logs (one JSON line per API call or decision) and results of every run
- `ccsp/` extraction and replay engines; `litsearch/` OpenAlex connector, audit log, screener
- `results.md`, `APPENDIX.md`

No publisher PDFs are included. Models: claude-haiku-4-5, claude-opus-5, sentence transformers all MiniLM L6 v2.

## License

MIT for the code. Corpus metadata is from OpenAlex (CC0).
