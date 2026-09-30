# Technical appendix: the Computational Construct Saturation Protocol on legitimacy

Draft, 2026-10-01. Companion to the Stage 1 proposal for the Organization Science special issue "AI Enabled Frontiers in Organizational Science." Everything here is reproducible from the repository; section 12 says how.

## A1. What the protocol decides

Given a named construct and its literature, the protocol decides whether reading further is likely to change what the construct is: its definition, essential attributes, dimensions, level of analysis, and boundaries against neighboring constructs. It reads the literature in publication order, keeps a structured record of the construct, measures whether that record is still moving, proposes a stop when it is not, and then tries to break the stop. The output is a dated, scoped claim of provisional saturation, or a statement that the construct has not saturated, with the log that supports either.

## A2. The twelve steps and who does what

| Step | Proposes | Computes | Decides |
|---|---|---|---|
| 1 Frame | Researcher names the construct and anchor papers | | Researcher; committed to version control before any result |
| 2 Discover | AI chains from anchors, keyword search | Retrieval, deduplication, audit log | Inclusion rule written by the researcher |
| 3 Boundary | AI screens every abstract, one reason each | Agreement on a labeled sample | Rule by researcher; sample by a coder |
| 4 Extract | AI fills seven fields with quotes | Quote verification against the text | Coder spot check |
| 5 Represent | AI merges records into the running state | Codebook mapping of phrasings to canonical ids | Codebook editable by the researcher |
| 6 Materiality | AI flags changes by comparing records | Set differences on canonical ids | Coders label a sample; researcher decides disagreements |
| 7 Indicators | | Attribute change, network change, semantic novelty, definition drift, Chao1 | Thresholds pre registered |
| 8 Candidate stop | | Conjunctive rule fires and freezes the state | |
| 9 Challenge | AI runs holdout, counter batch, reorders, freeze at a known date | Whether the construct moved | |
| 10 Assess challenge | AI drafts the classification | | Researcher confirms or overrules, logged |
| 11 Authorize | | | Researcher signs with scope and date |
| 12 Audit | AI drafts methods text | Hashes, logs, one command replay | Researcher owns the manuscript |

## A3. Corpus construction

**Anchors.** Fourteen papers declared in `declaration/seeds.csv` before the search: twelve ground truth papers that the field's own reviews treat as moments the construct changed (Dowling and Pfeffer 1975; Ashforth and Gibbs 1990; Aldrich and Fiol 1994; Suchman 1995; Zimmerman and Zeitz 2002; Deephouse and Carter 2005; Deephouse and Suchman 2008; Bitektine 2011; Tost 2011; Bitektine and Haack 2015; Suddaby, Bitektine and Haack 2017; Deephouse, Bundy, Tost and Suchman 2017) and two context papers (Meyer and Rowan 1977; DiMaggio and Powell 1983).

**Retrieval.** OpenAlex. Backward chaining: every work the anchors cite. Forward chaining: every work citing an anchor, kept if the title contains the construct's stem or the abstract contains it together with a concept word (define, dimension, typology, judgment, review, distinguish, and so on); 19,350 citing works failing that filter are stored for audit. Five keyword queries from 1975. Round two: works cited by two or more included papers and showing a concept signal. Every request is logged with its parameters.

**Inclusion rule** (`declaration/inclusion_rule.md`, committed 2026-09-29). In: papers that define or redefine the construct, propose or revise its types or dimensions, set its boundaries against neighboring constructs, change or argue about its level of analysis, or review the concept itself. Out: papers that use it as a variable, as background institutional theory, study legitimation tactics without revising the concept, or apply an existing instrument. Three borderline rules stated in the file.

**Screening.** Two passes. Pass one, claude-haiku-4-5 on all 7,077 abstracts, three way decision with a reason. Pass two, claude-opus-5 on every paper Haiku marked include or unsure (1,455). Round two candidates (187) on Opus. Title only papers: abstracts sought from Semantic Scholar and Crossref (25 of 391 found), rescreened on Opus; the remaining unsure papers were sent to full text screening if linked to two or more included papers (43) and otherwise excluded with the reason logged (79). The twelve ground truth anchors must pass without being told; all twelve did.

**Freeze.** 242 unique papers after merging duplicate database records by DOI and by title and year. SHA 256 of every corpus file in `data/corpus/FREEZE.json`, committed 2026-09-30. A random 15 percent holdout (18 papers) drawn from the 1975 to 2017 window before any record was read.

## A4. Extraction schema

Seven fields per paper plus one flag. Each value carries the verbatim sentence it was taken from.

| Field | Content | Type |
|---|---|---|
| definition | How this paper defines the construct | text, quote |
| essential_attributes | Properties the construct must have to be the construct | list of value, quote |
| dimensions | Named types, components or facets | list |
| level | individual, group, organization, field, society, multilevel, not stated | enum, quote |
| antecedents | What the paper says produces the construct | list |
| consequences | What the paper says the construct produces | list |
| rival_constructs | Constructs the paper distinguishes it from or relates it to | list |
| disagrees_with_prior | Any explicit claim that an earlier conceptualization is wrong or incomplete | text, quote |
| text_sufficient | Whether the supplied text could support the record | boolean |

The prompt (`ccsp/extract.py`, version `extract-v1-2026-10-01`) instructs the model to use only the supplied text and to record nothing it cannot quote. Quote verification is done in code by substring match after whitespace normalization. Model claude-opus-5, temperature not settable on this model; determinism is approximated by structured output and cached system prompt, and every prompt and response is logged.

**Sources.** Full text was obtained automatically for 57 of 153 papers in the window; the remainder are blocked to automated fetching by their publishers. Every record is built from the abstract; the full text record replaces it where one exists. The loss is measured in section A9.

## A5. Codebook

Comparing records requires knowing when two phrasings name the same item. Embedding similarity alone does not (section A8). The codebook step collects every phrasing seen in the corpus for each list field and groups them into canonical items in one model call per field (claude-opus-5, effort high), with an instruction to discard entries that are not of the field's kind (for example, consequences listed as attributes). The mapping is written to `data/corpus/codebook.json`, logged, and editable by a person. A second, coarser grouping of dimensions into families was produced the same way.

| Field | Phrasings | Canonical items | Discarded |
|---|---|---|---|
| Essential attributes | 533 | 28 | 30 |
| Dimensions | 393 | 98, grouped into 16 families | 19 |
| Rival constructs | 157 | 35 | 3 |
| Antecedents | 436 | 76 | 2 |
| Consequences | 295 | 30 | 14 |

## A6. Running state, materiality, indicators, rule

**State after batch b**, following the deck's R_b: the set of canonical attribute ids A_b, dimension ids M_b, antecedent and consequence ids N_b, rival construct ids B_b, the set of levels seen L_b, and the most recent definition D_b.

**Materiality of one paper** is computed by comparing its record with the state before it. The paper is material if it adds an attribute id not in A_b, a dimension id not in M_b, a level not in L_b, or a rival construct id not in B_b. A new antecedent or consequence is flagged nomological and is not material by default (deck slide 41). Category labels: dimension or definition, boundary, level, nomological, redundant or contextual.

**Indicators per batch.**
- Attribute change AC_b = 1 minus Jaccard(A_{b-1} ∪ M_{b-1}, A_b ∪ M_b).
- Network change NC_b = 1 minus Jaccard over N ∪ B.
- Semantic novelty SN: mean over the batch's items of 1 minus the cosine similarity to the nearest prior item; 1 for a new canonical id.
- Definition drift DD_b = 1 minus cosine(embed(D_b), embed(D_{b-1})), diagnostic only.
- Chao1 on attribute recurrence counts: an estimate of unseen attributes.

**Rule** (pre registered 2026-10-01, `ccsp/replay.py`). Batch size 10. A batch is quiet if the material fraction is at most tau_v, AC_b < 0.10, and NC_b < 0.25. A quiet batch adds one to the streak; anything else resets it to zero. When the streak reaches k = 3 the rule proposes a candidate stop and freezes the state. tau_v was 0 in the primary run and 0.1, 0.2, 0.3 in sensitivity. Synonym threshold for phrasings not in the codebook: 0.55 cosine on sentence transformers all MiniLM L6 v2.

## A7. Challenge tests

- **Freeze at a known date.** Truncate the corpus at the end of 2010, strip names and years from the records, run the rule. The field's reviews date the next reconceptualization to 2011 (Bitektine; Tost) and 2014 to 2015 (Bitektine and Haack). A stop inside the window is a candidate false stop; whether it is one depends on the counter batch.
- **Counter batch.** Feed the 2011 and 2014 anchors on top of the frozen state and record whether they register as material.
- **Holdout.** After any stop on the full window, feed the sealed 18 and count how many reopen the construct.
- **Order.** Twenty random orders of the pre 2011 records; report how many produce a stop.
- **Threshold sweep.** Batch size 5, 10, 15; k 2 to 5; synonym threshold 0.45 to 0.65; AC threshold 0.05 to 0.20; nomological counted or not: 216 settings.
- **Next batch.** After any stop, the material count in the batch that actually followed.

## A8. Result of the first replay: similarity is not identity

With attributes matched by embedding similarity alone, the rule never stopped under any of 216 settings or 20 orders, and the attribute store reached 152 items from 99 papers. Inspection showed the same attribute recorded five times in five wordings. This is a property of similarity based comparison, not of the construct: without canonical ids every paper is a change, and a rule with zero tolerance can never fire. Any convergence measure built on embedding distance between phrasings inherits this. The codebook step was added in response and is logged as an amendment.

## A9. Abstract tier loss

On the 28 papers held both ways: definition found in 14 from abstracts against 27 from full text; 2.2 against 5.2 attributes per paper; 1.4 against 4.2 dimensions; 0.3 against 2.4 rival constructs; disagreement with prior work detected in 16 against 27. The abstract tier under detects exactly the fields that carry materiality. Its bias is toward quiet.

## A10. Replay results on codebook ids

Development set 99 records (32 full text, 67 abstract). Attributes saturate at 26 by batch 7 (2011 to 2013) and add one item in the next 30 papers; AC falls from 1.00 to 0.08; NC to 0.01 to 0.03. Material papers per batch under the primary rule: 7, 5, 4, 7, 4, 8, 5, 5, 4, 8. From batch 6 on the drivers are new dimension typologies and new rival constructs.

| Variant | tau_v | Full window stop | Freeze 2010 stop | Orders stopping of 20 | 2011, 2014 caught after freeze | Holdout material after stop |
|---|---|---|---|---|---|---|
| A primary | 0 to 0.3 | never | never | 0 | yes, yes | |
| B families | 0 | never | never | 0 | yes, no | |
| B families | 0.1 to 0.3 | 2016, batch 9 | never | 0 to 2 | yes, no | 1 of 17 |
| C confirmed | 0 to 0.3 | never | never | 0 | yes, no | |

**Freeze test.** No variant, tolerance or order stops before 2011. Bitektine 2011 is material under every variant (new attribute, new rival construct). Bitektine and Haack 2014 is material under the primary rule (two new dimensions, a level never seen). No false stop.

**The 2016 stop.** Under B with tolerance, three quiet batches span 2011 to 2016 and the rule stops. The holdout then reopens the construct with one paper of 17, and the next actual batch (2016 to 2017) contains three material papers, including Boutilier 2017 "Social license to operate: legitimacy by another name?" adding two rival constructs. A false stop, measured.

**Trade off.** The family level reading that makes the rule stoppable is the reading that stops seeing the 2014 reconceptualization. Sensitivity and stoppability pull against each other on this construct.

## A11. Human validation, scheduled

Two coders will label 25 to 30 papers, chosen by the lead author to span the categories, blind to the machine's labels, and agreement with the computed labels and with each other will be reported as Krippendorff's alpha. A 100 paper screening sample is scheduled the same way. Neither has run yet. The codebook is also to be re generated at a second granularity to test whether the stopping result depends on it.

## A12. Reproducibility

Repository layout: `declaration/` (rule, anchors), `data/corpus/` (frozen corpus, holdout ids, codebook, hashes), `runs/` (every audit log and result), `ccsp/` (extraction, replay), `stage*.py` (the pipeline in order). Commits: `eb8e522` pre registration (2026-09-29), `59afa61` amendment, `d3717e2` corpus frozen (2026-09-30). Replay, variants, tolerance, orders and holdout run from cached records with no API calls: `python3 stage10_variants.py` and `python3 stage11_tolerance.py`. Extraction and screening require an Anthropic key; OpenAlex requires none. No PDFs are in the repository; the acquisition log records which papers had full text. Models: claude-haiku-4-5, claude-opus-5, sentence transformers all MiniLM L6 v2. Total logged spend about $40.

## A13. Amendments

| Date | Change | Reason |
|---|---|---|
| 2026-09-29 | 1977 and 1983 foundations reclassified as context | Correctly excluded by the rule |
| 2026-09-30 | Abstract tier for all papers, full text where available, no manual fetching | Publisher blocks; a method needing 150 downloads will not be adopted |
| 2026-10-01 | Codebook step | Similarity matching turned every paper into a change |
| 2026-10-01 | Level change means a level never seen before | Majority rule misfired in a multilevel literature |
| 2026-10-01 | Variants B and C and tau_v added as sensitivity | Primary rule never stops; needed to know what it would take |
