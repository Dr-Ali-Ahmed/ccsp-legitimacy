Draft 2026-10-01, synchronized with the Stage 1 package document.

# Technical Appendix

Everything in this appendix is reproducible from the research artifact described in the final section. Section numbers here are referenced from the proposal.

## A1. What the protocol decides

Given a named construct and its literature, the protocol decides whether reading further is likely to change what the construct is: its definition, essential attributes, dimensions, level of analysis, and boundaries against neighboring constructs. It reads the literature in publication order, keeps a structured record of the construct, measures whether that record is still moving, proposes a stop when it is not, and then tries to break the stop. The output is a dated, scoped statement of provisional saturation, or a statement that the construct has not saturated, with the log that supports either.

## A2. The twelve steps

| Step | Proposes | Computes | Decides |
|---|---|---|---|
| 1 Frame | Researcher names the construct and anchor papers |  | Researcher; committed to version control before any result |
| 2 Discover | AI chains from anchors and runs keyword search | Retrieval, deduplication, audit log | Inclusion rule written by the researcher |
| 3 Boundary | AI screens every abstract with one reason each | Agreement on a labeled sample | Rule by researcher; sample checked by a coder |
| 4 Extract | AI fills seven fields with quotes | Quote verification against the text | Coder spot check |
| 5 Represent | AI merges records into the running state | Codebook mapping of phrasings to canonical ids | Codebook editable by the researcher |
| 6 Materiality | AI flags changes by comparing records | Set differences on canonical ids | Coders label a sample; researcher decides disagreements |
| 7 Indicators |  | Attribute change, network change, semantic novelty, definition drift, Chao1 | Thresholds pre registered |
| 8 Candidate stop |  | Conjunctive rule fires and freezes the state |  |
| 9 Challenge | AI runs holdout, counter batch, reorders, freeze at a known date | Whether the construct moved |  |
| 10 Assess challenge | AI drafts the classification |  | Researcher confirms or overrules, logged |
| 11 Authorize |  |  | Researcher signs with scope and date |
| 12 Audit | AI drafts methods text | Hashes, logs, one command replay | Researcher owns the manuscript |

## A3. Corpus construction

Anchors. Fourteen papers declared before the search: twelve ground truth papers the field's own reviews treat as moments the construct changed (Dowling and Pfeffer 1975; Ashforth and Gibbs 1990; Aldrich and Fiol 1994; Suchman 1995; Zimmerman and Zeitz 2002; Deephouse and Carter 2005; Deephouse and Suchman 2008; Bitektine 2011; Tost 2011; Bitektine and Haack 2015; Suddaby, Bitektine, and Haack 2017; Deephouse, Bundy, Tost, and Suchman 2017) and two context papers (Meyer and Rowan 1977; DiMaggio and Powell 1983).

Retrieval. OpenAlex. Backward chaining over every work the anchors cite; forward chaining over every work citing an anchor, kept if the title contains the construct's stem or the abstract contains it together with a concept word (define, dimension, typology, judgment, review, distinguish, and similar); 19,350 citing works failing that filter were stored for audit. Five keyword queries from 1975. A second round took works cited by two or more included papers and showing a concept signal. Every request is logged with its parameters.

Inclusion rule, committed 2026-09-29. In: papers that define or redefine the construct, propose or revise its types or dimensions, set its boundaries against neighboring constructs, change or argue about its level of analysis, or review the concept itself. Out: papers that use it as a variable, as background institutional theory, study legitimation tactics without revising the concept, or apply an existing instrument to a new sample. Three borderline rules are stated in the artifact.

Screening. Two passes: claude-haiku-4-5 on all 7,077 abstracts with a three way decision and a reason, then claude-opus-5 on every paper the first pass marked include or unsure (1,455). Second round candidates (187) on the second model. Abstracts for title only papers were sought from Semantic Scholar and Crossref (25 of 391 found) and those papers rescreened. Remaining unsure papers were queued for full text if linked by citation to two or more included papers (43) and otherwise excluded with the reason logged (79). On a 214 paper sample the two models agreed on 86 percent of decisions with five hard disagreements. The twelve ground truth anchors had to pass without being told; all twelve did.

| Step | Count |
|---|---|
| Candidates retrieved | 7,077 (plus 19,350 set aside by the concept filter, kept for audit) |
| Round two candidates | 187 |
| Unique papers included | 242 |
| In the 1975 to 2017 window used for extraction | 123 |
| Sealed holdout drawn from that window | 18 |
| Unsure, queued for full text | 43 |
| Unsure, excluded with a logged reason | 79 |
| Ground truth anchors passing the screener unaided | 12 of 12 |

## A4. Extraction schema

| Field | Content | Type |
|---|---|---|
| definition | How this paper defines the construct | text with quote |
| essential_attributes | Properties the construct must have to be the construct | list of value and quote |
| dimensions | Named types, components, or facets | list |
| level | individual, group, organization, field, society, multilevel, not stated | enum with quote |
| antecedents | What the paper says produces the construct | list |
| consequences | What the paper says the construct produces | list |
| rival_constructs | Constructs the paper distinguishes it from or relates it to | list |
| disagrees_with_prior | Any explicit claim that an earlier conceptualization is wrong or incomplete | text with quote |
| text_sufficient | Whether the supplied text could support the record | boolean |

The prompt instructs the model to use only the supplied text and to record nothing it cannot quote; every value carries the verbatim sentence it came from, verified in code by substring match after whitespace normalization. Model claude-opus-5, prompt version extract-v1-2026-10-01, structured output, cached system prompt; every prompt and response is logged. Full text was obtained automatically for 57 of 153 papers in the window; every record was built from the abstract and replaced by the full text record where one existed.

## A5. Codebook

Comparing records requires knowing when two phrasings name the same item. The codebook step collects every phrasing seen in the corpus for each list field and groups them into canonical items in one model call per field, with an instruction to discard entries that are not of the field's kind. The mapping is written to a file, logged, and editable by a person. A second, coarser grouping of dimensions into families was produced the same way.

| Field | Phrasings | Canonical items | Discarded |
|---|---|---|---|
| Essential attributes | 533 | 28 | 30 |
| Dimensions | 393 | 98, grouped into 16 families | 19 |
| Rival constructs | 157 | 35 | 3 |
| Antecedents | 436 | 76 | 2 |
| Consequences | 295 | 30 | 14 |

## A6. Running state, materiality, indicators, and rule

State after batch b: the set of canonical attribute ids A, dimension ids M, antecedent and consequence ids N, rival construct ids B, the set of levels seen L, and the most recent definition D. Materiality of one paper is computed by comparing its record with the state before it: the paper is material if it adds an attribute id not in A, a dimension id not in M, a level not in L, or a rival construct id not in B. A new antecedent or consequence is flagged nomological and is not material by default.

Indicators per batch. Attribute change AC = 1 minus Jaccard(A ∪ M before, A ∪ M after). Network change NC = 1 minus Jaccard over N ∪ B. Semantic novelty SN = mean over the batch's items of 1 minus cosine similarity to the nearest prior item, 1 for a new canonical id. Definition drift DD = 1 minus cosine(embed(D after), embed(D before)), diagnostic only. Chao1 on attribute recurrence counts estimates unseen attributes.

Rule, pre registered 2026-10-01. Batch size 10. A batch is quiet if the material fraction is at most tau_v, AC is below 0.10, and NC is below 0.25. A quiet batch adds one to a streak; anything else resets it. When the streak reaches k = 3 the rule proposes a candidate stop and freezes the state. tau_v was 0 in the primary run and 0.1, 0.2, 0.3 in sensitivity. Synonym threshold for phrasings not in the codebook: cosine 0.55 on sentence transformers all MiniLM L6 v2, run locally.

## A7. Challenge tests

Freeze at a known date: truncate the corpus at the end of 2010, hide names and years from the model, run the rule; the field dates the next reconceptualization to 2011. Counter batch: feed the 2011 and 2015 anchors on top of the frozen state and record whether they register as material. Holdout: after any stop on the full window, feed the sealed papers and count how many reopen the construct. Order: twenty random orders of the pre 2011 records. Threshold sweep: batch size 5, 10, 15; k from 2 to 5; synonym threshold 0.45 to 0.65; attribute threshold 0.05 to 0.20; nomological counted or not, 216 settings. Next batch: after any stop, the material count in the batch that actually followed.

## A8. First replay: similarity is not identity

With attributes matched by embedding similarity alone, the rule never stopped under any of 216 settings or 20 orders, and the attribute store reached 152 items from 99 papers. Inspection showed the same attribute recorded five times in five wordings. This is a property of similarity based comparison, not of the construct: without canonical ids every paper is a change, and a rule with zero tolerance can never fire. The codebook step was added in response and is logged as an amendment.

## A9. Abstract tier loss

| Field | From abstract | From full text |
|---|---|---|
| Definition found | 14 of 28 | 27 of 28 |
| Essential attributes per paper | 2.2 | 5.2 |
| Dimensions per paper | 1.4 | 4.2 |
| Rival constructs per paper | 0.3 | 2.4 |
| Explicit disagreement with prior work | 16 of 28 | 27 of 28 |

Measured on the 28 papers held both ways. The abstract tier under detects exactly the fields that carry materiality; its bias is toward quiet, so the never stopping result below is understated rather than produced by thin data.

## A10. Replay results, in detail

How to read this section. The replay walks the 99 development records from 1975 to 2017 in publication order, ten papers at a time. After each batch it asks three questions of the running record: did any paper in this batch add something the record did not already contain (a material paper); how much did the set of attributes and dimensions change (attribute change); and how much did the set of relationships and rival constructs change (network change). A batch is quiet when all three are low. The rule proposes a stop after three quiet batches in a row. Everything below is a reading of that batch log.

What settled and when. The attribute set, the properties papers say legitimacy must have, grows quickly in the first six batches and then stops growing. It holds 25 canonical attributes by batch 6 (2009 to 2011), 26 by batch 7, and adds one more in the remaining 30 papers through 2017. Attribute change falls from 1.00 in the first batch to 0.08 to 0.15 from batch 5 on. Network change falls further, to between 0.01 and 0.05 from batch 8. On these two indicators, which are the deck's AC and NC, the construct looks settled from about 2011. The thin abstract records make this look, if anything, more settled than it is.

What did not settle. The batches never go quiet because every batch contains at least one material paper, and from batch 6 on those papers are material for two reasons only: they name a typology of legitimacy not seen before, or they distinguish legitimacy from a construct not seen before. Attributes contribute nothing after batch 7. Typologies arrive at a rate of four to six per batch under the fine codebook (98 dimensions) and one to three per batch under the coarse one (16 families). Rival constructs arrive at one or two per batch. This is the literature the 2017 review describes: agreed on what legitimacy is, unable to agree on how to cut it, and still drawing its boundary against accountability, social license, trust, and reputation as late as 2017.

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

The variants. Three readings of the materiality rule were run to learn what it would take for the rule to fire. A is the rule as pre registered, with one bug repaired: a paper at a minority level of analysis had been counted as a level change, which misfires in a literature that is 47 organization level, 25 multilevel, and a scatter of individual, group, field, and society; the repaired rule counts only a level never seen before. B compares dimensions at the family level, so a new member of an existing typology is not a change. C counts a new dimension only when a second paper uses it, so one paper's private typology cannot reset the clock. Then tau_v, from the deck's own rule: the fraction of material papers a batch may contain and still be quiet, run at 0, 0.1, 0.2, and 0.3.

| Variant | tau_v | Full window stop | Freeze 2010 stop | Orders stopping, of 20 | 2011 and 2015 anchors material after freeze | Holdout material after stop |
|---|---|---|---|---|---|---|
| A primary | 0 to 0.3 | never | never | 0 | yes, yes |  |
| B families | 0 | never | never | 0 | yes, no |  |
| B families | 0.1 to 0.3 | 2016, batch 9 | never | 0 to 2 | yes, no | 1 of 17 |
| C confirmed | 0 to 0.3 | never | never | 0 | yes, no |  |

The freeze test, in full. The corpus was cut at the end of 2010, leaving 57 records, and the model was shown records with author names and years removed. The rule was run under every variant, every tolerance, and 20 random orders of those 57 papers. It stopped in none of them. Then the 2011 and 2015 anchor papers were fed onto the frozen state one at a time. Bitektine (2011), which reframes legitimacy as a social judgment and separates it from status and reputation, was flagged material under every variant: it adds an attribute the record lacked and a rival construct the record lacked. Bitektine and Haack (2015), which makes legitimacy a multilevel process, was flagged material under the primary rule for two new dimensions and a level never seen; under the family reading its two dimensions fold into existing families and it is not flagged. Tost (2011) could not be tested because it has no abstract in any source we can reach and no full text. The result is that the protocol did not declare saturation before the reconceptualization the field dates to 2011, and it recognized that reconceptualization when it arrived.

The 2016 stop, in full. Under the family reading with tolerance 0.1 or more, batches 7, 8, and 9 (2011 to 2016) each contain at most one material paper in ten, and the rule proposes a stop after the 90th paper, in 2016. Two checks followed. The sealed holdout, 18 papers drawn before any reading, 17 of them with records, was fed onto the frozen 2016 state: one reopened the construct. The next batch in the real sequence, papers 91 to 99 covering 2016 to 2017, was then read: three were material. One adds an attribute through an accountability lens, one adds a rival construct from inter partner legitimacy, and Boutilier (2017), "Social license to operate: legitimacy by another name?", adds two rival constructs. So the only stop the rule can be tuned to produce was contradicted by the sealed evidence and by the very next ten papers. That is a false stop with its size attached: one of 17 and three of ten.

The trade off. The reading that produces the 2016 stop is the family reading, and the family reading is the one that no longer sees Bitektine and Haack (2015) as material. Coarsening the categories makes the rule capable of stopping and makes it blind to a reconceptualization the field recognizes. Tightening the categories restores the sensitivity and the rule never stops. No setting in the sweep delivers both, and this is not a matter of thresholds: it holds across batch sizes, k, synonym thresholds, and tolerances.

The order test. Twenty random reorderings of the pre 2011 papers produced no stop under any variant at tolerance 0.2 or below, and two stops of 20 under the family reading at tolerance 0.3. Reading order does not change the answer on this construct, because there is no order in which three consecutive batches of ten are free of a new typology or a new boundary claim.

What can and cannot be concluded. It can be concluded that on legitimacy, with these records, the stated rule never declares saturation; that its conservatism was correct at 2010; that the one stop obtainable by tolerance was false; and that the answer hinges on the granularity of dimensions, a choice no threshold can remove. It cannot be concluded that the literature is exhausted, that the codebook is the right one, that a human coder would agree with the computed labels, or that other constructs behave the same way. The scheduled human validation, the second codebook granularity, and the two further constructs are the tests for those.

## A11. Human validation, scheduled

Two coders will label 25 to 30 papers chosen to span the categories, blind to the machine's labels, and a 100 decision screening sample; agreement with the computed labels and between coders will be reported as Krippendorff's alpha. Neither has run. The codebook will be regenerated at two further granularities to test whether the stopping result depends on it.

## A12. Amendments to the pre registration

| Date | Change | Reason |
|---|---|---|
| 2026-09-29 | Meyer and Rowan 1977 and DiMaggio and Powell 1983 reclassified from ground truth to context | Both screening models excluded 1983 under the rule with a correct reason |
| 2026-09-30 | Records from abstracts for all papers, full text where available, no manual fetching | Publishers block automated retrieval; a method needing 150 downloads per construct would not be adopted |
| 2026-10-01 | Codebook step added | Similarity matching turned every paper into a change |
| 2026-10-01 | Level change redefined as a level never seen before | Majority level rule misfired in a multilevel literature |
| 2026-10-01 | Variants B and C and tolerance tau_v added as sensitivity | Primary rule never stops; needed to learn what it would take |

## A13. Cost

Logged API spend for the full run: about 40 dollars, plus about 5 dollars for unlogged sample runs. Retrieval and screening: one working day. Extraction: under an hour. Replay, variants, tolerance, orders, and holdout run on cached records in minutes on a laptop. Models: claude-haiku-4-5, claude-opus-5, and sentence transformers all MiniLM L6 v2 locally.

# Research Artifact

The prototype is a Git repository containing the complete pipeline and every log from the run reported above. Repository: https://github.com/Dr-Ali-Ahmed/ccsp-legitimacy (private during review; access is granted to the editors on request, and the repository is made public on acceptance).

Contents. declaration/: the inclusion rule and the anchor list, in the commit that predates any result. data/corpus/: the frozen corpus (242 records with identifiers, metadata, and abstracts), the sealed holdout ids, the codebook, and SHA 256 hashes of each file. runs/: the audit log for every stage, one JSON line per API call or decision, and the results of every replay, variant, tolerance, order, and holdout run. ccsp/: the extraction and replay engines. Numbered stage scripts run the pipeline in order. results.md reports every table with its source run.

Reproduction. Replay, variants, tolerance, orders, and holdout run from cached records with no API calls in minutes. Screening and extraction require an Anthropic API key; OpenAlex retrieval requires no key. No publisher PDFs are included; the acquisition log records which papers had full text. Model identifiers and prompt versions are pinned in the code and recorded in every log entry.

Commits. Pre registration of the rule and anchors 2026-09-29; amendment 2026-09-29; corpus frozen 2026-09-30; extraction, codebook, replay, and results 2026-09-30. Each amendment to the pre registration is recorded in the repository with its date and reason.
