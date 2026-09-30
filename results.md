# CCSP on legitimacy: results as of 2026-10-01

Every number below comes from a logged run in `runs/`. Settings were pre registered in `ccsp/replay.py` and changed only through the dated amendments listed at the end, each with its reason. Nothing was tuned on the final test after seeing it, with one exception stated plainly in section 6.

## 1. Corpus

| Step | Count |
|---|---|
| Anchor papers (declared before the search) | 14, of which 12 ground truth and 2 context |
| Candidates retrieved by chaining and keyword search | 7,077 (a further 19,350 citing papers set aside by a concept filter, kept for audit) |
| Screened, two passes: Haiku 4.5 on all, Opus 5 on Haiku's include and unsure | 7,077 |
| Round two: papers co cited by two or more includes with a concept signal | 187, screened on Opus 5 |
| Abstracts recovered for title only papers (Semantic Scholar, Crossref) | 25 of 391 |
| Unique papers included after merging duplicate records | **242** |
| In the 1975 to 2017 window used for extraction | 123 |
| Sealed holdout drawn from that window before any reading | 18 |
| Unsure after screening, queued for full text | 43 |
| Unsure, excluded with a logged reason | 79 |
| Ground truth anchors that passed the screener without being told | 12 of 12 |

Screening agreement on a 214 paper sample: Haiku and Opus gave the same decision on 86 percent; five hard disagreements, four of which Opus decided as the rule reads. DiMaggio and Powell 1983 was excluded by both models under the rule, with the reason that it treats legitimacy as a background driver of isomorphism. That reading is correct, and the two 1977 and 1983 foundations were reclassified as context (amendment, 2026-09-29).

## 2. Full text and the abstract tier

Full text could be obtained automatically for 57 of 153 papers in the window; publishers block automatic fetching for the rest even under a subscription. The decision (2026-09-30) was to build every record from the abstract and use full text only where it exists, with no manual fetching. Records: 220 from abstracts (22 papers have no abstract), 34 from full text.

What the abstract misses, measured on the 28 papers held both ways:

| Field | From abstract | From full text |
|---|---|---|
| Definition found | 14 of 28 | 27 of 28 |
| Essential attributes per paper | 2.2 | 5.2 |
| Dimensions per paper | 1.4 | 4.2 |
| Rival constructs per paper | 0.3 | 2.4 |
| Explicit disagreement with prior work | 16 of 28 | 27 of 28 |

The abstract tier is thin exactly on the fields that carry materiality, dimensions and boundaries. This biases the replay toward quiet, not toward noise, which matters for reading section 5.

## 3. Extraction

Seven fields per paper: definition, essential attributes, dimensions, level, antecedents, consequences, rival constructs, plus an explicit "disagrees with prior" field. Every value carries the quoted sentence it was taken from. Model claude-opus-5, prompt version `extract-v1-2026-10-01`, instruction to use only the supplied text. Quote verification in code: 11 unverified quotes across 220 abstract records; on full text, 20 percent unverified before normalization, traced to two column PDF layouts rather than invented text. Cost: $4.48 for abstracts, $6.87 for full text.

## 4. The first replay failed, and why

The first replay compared attributes by embedding similarity (MiniLM, threshold 0.55). It never stopped under any of 216 settings or 20 orders. The attribute store grew to 152 items from 99 papers because each paper's wording of the same attribute became a new attribute. This is a failure of the comparison method, not a result about legitimacy: **similarity between phrasings does not identify attributes.** Any convergence measure built on embedding distance alone inherits this problem.

The fix was a codebook (amendment, 2026-10-01): one model call per field grouped every phrasing seen in the corpus into canonical items, logged and editable. 533 attribute phrasings became 28 attributes; 393 dimension phrasings became 98 dimensions, further grouped into 16 families; 157 rival construct phrasings became 35.

## 5. Replay on codebook ids

Development set: 99 records in the 1975 to 2017 window, holdout excluded (32 full text, 67 abstract). Batches of 10, k equals 3, attribute change threshold 0.10, network change threshold 0.25.

With the codebook, attributes saturate: the store reaches 26 by batch 7 (2011 to 2013) and adds one item in the next 30 papers. Attribute change falls from 1.00 to 0.08, network change to near zero. The batches still never go quiet, because dimensions and boundary claims keep arriving:

| Batch | Years | Attribute change | Network change | Material papers of 10 |
|---|---|---|---|---|
| 1 | 1975 to 1997 | 1.00 | 1.00 | 7 |
| 2 | 1997 to 2002 | 0.50 | 0.65 | 5 |
| 3 | 2003 to 2004 | 0.18 | 0.23 | 4 |
| 4 | 2004 to 2007 | 0.31 | 0.40 | 7 |
| 5 | 2007 to 2008 | 0.09 | 0.10 | 4 |
| 6 | 2009 to 2011 | 0.20 | 0.11 | 8 |
| 7 | 2011 to 2013 | 0.12 | 0.12 | 5 |
| 8 | 2013 to 2015 | 0.09 | 0.05 | 5 |
| 9 | 2015 to 2016 | 0.08 | 0.01 | 4 |
| 10 | 2016 to 2017 | 0.15 | 0.03 | 8 |

Under the primary rule the drivers from batch 6 on are new dimension typologies (four to six per batch) and new rival constructs, not attributes.

## 6. Variants of the materiality rule

Three readings were run side by side. A, primary as pre registered with one bug fix (a level change is a level never seen before, not a deviation from the majority level). B, dimensions compared at the family level. C, a dimension counts only when a second paper uses it. Then the deck's tolerance parameter tau_v, the material fraction a batch may contain and still count as quiet.

| Variant | tau_v | Full window stop | Freeze at 2010 stop | Random orders that stop, of 20 | 2011 and 2014 anchors caught as material after the freeze | Holdout papers material after the stop |
|---|---|---|---|---|---|---|
| A primary | 0 to 0.3 | never | never | 0 | yes, yes | |
| B families | 0 | never | never | 0 | yes, no | |
| B families | 0.1 | **2016, batch 9** | never | 0 | yes, no | 1 of 17 |
| B families | 0.2 | 2016, batch 9 | never | 0 | yes, no | 1 of 17 |
| B families | 0.3 | 2016, batch 9 | never | 2 | yes, no | 1 of 17 |
| C confirmed | 0 to 0.3 | never | never | 0 | yes, no | |

The exception to pre registration: variants B and C and the tolerance parameter were added after the primary rule had been observed never to stop. They are reported as sensitivity, not as the result.

## 7. The freeze test

Cut at the end of 2010, 57 records, names and years stripped from the model's view. **No variant, tolerance, or order stops before 2011.** Fed in afterwards, Bitektine 2011 registers as material under every variant (a new attribute and a new rival construct), and Bitektine and Haack 2014 under the primary rule (two new dimensions and a level never seen before). Tost 2011 has no abstract in OpenAlex and no full text, so it has no record and could not be tested.

Result: **no false stop.** The protocol did not declare saturation before the reconceptualization the field later published.

## 8. The one stop it produces, and what happened to it

Under B with tolerance 0.1 or more, the rule proposes a stop after batch 9, in 2016, following three quiet batches covering 2011 to 2016. Two checks:

- The sealed holdout, 17 papers with records, fed in after the stop: one reopens the construct.
- The next batch in the actual sequence, 2016 to 2017, contains three material papers: a 2016 accountability lens adding an attribute, a 2016 inter partner paper adding a rival construct, and Boutilier's 2017 "Social license to operate: legitimacy by another name?" adding two rival constructs.

So the only stop the rule can be tuned to produce was overturned within a year by the holdout and by the next ten papers. **A measured false stop, one paper of 17 and three of the next ten.**

## 9. What the run says, in order of confidence

1. **Similarity between phrasings cannot stand in for attribute identity.** Without a codebook, every paper is a change. This applies to any published method that measures convergence with embedding distance.
2. **On legitimacy, the rule did not stop early.** No setting stopped before 2011, and the 2011 reconceptualization was caught. That is the conservative behavior the method is supposed to have.
3. **Under the strict rule legitimacy never saturates through 2017.** Attributes settle by 2011; typologies and boundary claims do not. Suddaby, Bitektine and Haack 2017 describe the field as split three ways, which is what a non stopping rule looks like from the inside.
4. **Making the rule stoppable makes it less sensitive.** The family level reading that produces the 2016 stop is also the reading that no longer sees Bitektine and Haack 2014 as material. That trade off is the central design problem of the method.
5. **The one stop was false and the checks caught it.** The holdout and the next batch both reopened the construct.

## 10. Cost and time

Logged API spend for everything above: about $40, plus about $5 for unlogged sample runs. Retrieval and screening: one working day. Extraction: under an hour. Replay, variants, tolerance, orders, holdout: minutes each on a laptop, since they run on cached records. Embedding model: sentence transformers all MiniLM L6 v2, local, pinned.

## 11. Limitations that are also findings

- Full text for 34 of 99 development records. The abstract tier under detects dimensions and boundaries, which biases toward quiet, so the "never stops" result is if anything understated.
- Tost 2011 absent; the 2011 test rests on Bitektine.
- The codebook is one model's grouping. It is logged and editable; a second codebook at a different granularity is the next sensitivity check and is cheap.
- No human validation labels yet. The 25 to 30 paper sample is scheduled and needs two coders.
- Thresholds were pre registered by argument, not calibrated on a second construct.

## Amendments log

| Date | Change | Reason |
|---|---|---|
| 2026-09-29 | Meyer and Rowan 1977 and DiMaggio and Powell 1983 reclassified from ground truth to context | Both screening models excluded 1983 under the rule with a correct reason |
| 2026-09-30 | Extraction from abstracts for all papers, full text where available, no manual fetching | Publishers block automatic fetching; manual fetching of 150 papers is not a method anyone will use |
| 2026-10-01 | Codebook step added: phrasings grouped into canonical ids by one logged model call per field | First replay showed similarity matching turns every paper into a change |
| 2026-10-01 | Level change redefined as a level never seen before | Majority level rule fired on every paper at a minority level in a multilevel literature |
| 2026-10-01 | Variants B, C and tolerance tau_v added as sensitivity | Primary rule never stops; needed to know what it would take |
