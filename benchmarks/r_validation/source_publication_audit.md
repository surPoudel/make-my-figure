# Source publication audit

**Purpose.** Establish, from authoritative sources only, what the RSEM matrix in the repository root is, where it
comes from, and which sample labels are *confirmed* versus merely plausible. Nothing biological is asserted below
that is not stated verbatim in a public record.

## 1. Publication record (verified 2026-09-04)

| Field | Value | Source |
|---|---|---|
| Title | Membrane receptors cluster phosphatidylserine to activate LC3-associated phagocytosis | Crossref, PubMed, Europe PMC |
| Authors | Boada-Romero E, Guy CS, Palacios G, Mari L, Poudel S, Li Z, Sharma P, Green DR | Crossref `author` list |
| Journal | Nature Cell Biology **27**(10): 1676–1687 | Crossref `container-title`, `volume`, `issue`, `page` |
| Published | 2025-09-22 (online) | Crossref `published.date-parts`; Europe PMC `firstPublicationDate` |
| DOI | 10.1038/s41556-025-01749-z | Crossref (resolves; publisher Springer Science and Business Media LLC) |
| PMID | 40983659 | PubMed esearch `[doi]` |
| PMCID | PMC12527911 | Europe PMC (`isOpenAccess: Y`) |
| Licence | CC BY-NC-ND 4.0 | Crossref `license[].URL` |
| Funder | NIH (U.S. Department of Health & Human Services) | Crossref `funder` |

Queries used: `https://api.crossref.org/works/10.1038/s41556-025-01749-z`,
`eutils esearch db=pubmed term=10.1038/s41556-025-01749-z[doi]`,
`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:10.1038/s41556-025-01749-z`.
The Nature landing page was not scraped; the bibliographic fields above come from the registries that Nature
deposits into. The article licence (CC BY-NC-ND) is irrelevant to this validation: **no figure, text or
supplementary artefact of the article is reproduced**; only the authors' own GEO-deposited count matrix is used.

## 2. Data record — GEO GSE299655 (verified 2026-09-04)

| Field | Value |
|---|---|
| Series | GSE299655 — "Phosphatidylserine clustering by membrane receptors triggers LC3-associated phagocytosis" |
| Linked PubMed ID (in the GEO record) | 40983659 (matches §1) |
| Organism / platform | *Mus musculus*, GPL24247 (Illumina NovaSeq 6000) |
| Cell line (GEO `characteristics`) | RAW264.7 (TIB-71), tissue "Myeloid" |
| Samples | 16 (GSM9043003–GSM9043018), 4 genotypes × 4 replicates |
| Processing (GEO `data_processing`) | Trim Galore 0.5.0 → STAR 2.7.5a (mm10) → Picard MarkDuplicates → **RSEM** transcript quantification |
| Supplementary file | `GSE299655_GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt.gz` |

**File identity.** The GEO supplementary file was downloaded and decompressed; its SHA-256 is
`37922f561a8dddc41c583cce6eb7e8e356f71f32c462e802ceda496ee4aa1a92`, **byte-identical** to the repository file
`GREEN-318289-STRANDED_RSEM_gene_count.2024-01-10_03-09-06.txt` (6,565,018 bytes). The local matrix is therefore
exactly the deposited matrix, unmodified.

**Sample → group mapping (confirmed).** Every GSM record carries `Sample_description` lines
"Library name: <name>" and "Column names in GREEN-318289-…txt : <column>", which pin each matrix column to a GEO
genotype. The full table is in `data/metadata/geo_sample_map.csv`; summary:

| Matrix column prefix | GEO library names | GEO `genotype` | GEO titles |
|---|---|---|---|
| `Ctrl_1..4` (2686012–2686015) | Ctrl_1..4 | **Parental** | Parental1–4 |
| `sh5-8_1..4` (2686016–2686019) | sh5-8_1..4 | **ORP5/8 KD** | ORP5/8 KD1–4 |
| `shA-C_1..4` (2686020–2686023) | shA-C_1..4 | **ATP11A/C KD** | ATP11A/C KD1–4 |
| `sh50A_1..4` (2686024–2686027) | sh50A_1..4 | **CDC50A KD** | CDC50A KD1–4 |

One clerical inconsistency in the GEO record: GSM9043005 (Parental3, library Ctrl_3) states the column name
`2686013_Ctrl_3`, whereas the matrix column is `2686014_Ctrl_3` (2686013 is Ctrl_2). The library-name field is
unambiguous, so the mapping above uses library names; the typo is noted, not corrected in any source file.

**What is *not* asserted.** GEO gives genotype labels (knock-down targets) only. Which shRNA sequences, the
knock-down efficiency, the biological interpretation of any contrast, and any claim about LAP or phosphatidylserine
are properties of the publication and are **not** used, tested or implied by this validation. Throughout the
benchmark the four groups are treated as *technical contrasts* named by their GEO genotype labels.

## 3. What the numbers are

The GEO processing line says "Transcript quantification was calculated using RSEM" and the file name says
`RSEM_gene_count`. RSEM reports **expected counts** (posterior expected read counts per gene), which are
real-valued. This is consistent with the matrix: 4.63 % of all cells (and ~15.9 % of non-zero cells) are
non-integer (e.g. *Slfn4*: 8956.84, 6433.22, …). Consequences, applied throughout:

* The source matrix is never rounded or altered. Every derived representation (CPM, log-CPM, TMM, voom, filtered
  gene set, rounded copy for DESeq2) is written to a separate file with its transformation recorded.
* edgeR and limma-voom accept fractional expected counts and are used unchanged.
* DESeq2 requires integers; the DESeq2 reference uses `round()` on the *filtered* matrix as an explicit, labelled
  derived representation (the tximport convention). It is a Class B reference only.
* MakeMyFigure's own `validate_integer_counts` correctly refuses the un-rounded matrix for its optional count model,
  and `diagnose_matrix` reports `integer_like = False` — see `reports/RECOMMENDATION_AUDIT.md` for the consequence
  that the QC "suspected type" rule does *not* call this matrix `count_like`.

Library sizes (column sums) range from 24.0 M to 41.5 M; 70.9 % of cells are zero; 55,665 genes; 120 duplicated
`geneSymbol` values but 0 duplicated `geneID` values (so `geneID` is the feature key). Annotation columns
`geneID, geneSymbol, bioType, annotationLevel` are excluded from every numerical operation.
