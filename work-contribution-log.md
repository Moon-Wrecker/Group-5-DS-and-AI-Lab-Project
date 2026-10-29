# Work contribution log

Project: SerpentGuard AI, snake detection and classification<br>
Team: Group 5, DS and AI Lab Project. Team lead Jayesh Bansal; members Vikas, Puneet Bajaj and Manas Rastogi

The course asks for this log to be updated every week with each member's contributions. Add each new week above the previous one. Members check their own rows, and everyone also signs the acknowledgment page of each milestone report.

## Week 2: 23 to 29 October 2026 (Milestone 2, dataset preparation)

### Contribution entries

| Work item | Contribution / evidence | Contributor(s) | Date or period | Reviewed / confirmed by |
|---|---|---|---|---|
| Dataset build | Collected every research-grade iNaturalist photo of the 289 snake species recorded in India (182,497 photos, 0 failed) into a private Kaggle dataset, and checked 30 random photos (SHA-1 and size) and 8 species counts against iNaturalist | Puneet Bajaj, Jayesh Bansal | 24 to 25 Oct 2026 | Jayesh Bansal |
| Cleaning and splits | Removed duplicates, conflicting labels and tiny files; added genus, family, WHO category and tiers; built photographer-grouped train, validation and test splits with leakage checks ([`data/split_report.json`](data/split_report.json)) | Puneet Bajaj | 29 Oct 2026 | Jayesh Bansal |
| Processed dataset | Kaggle processing run with near-duplicate removal, final folder layout, sample grids and the private processed dataset | Puneet Bajaj | 29 Oct 2026 | Jayesh Bansal |
| Reproducibility | Wrote the notebook chain in [`notebooks/`](notebooks/README.md) (01 raw build, 02 split, 03 process, plus a loader for EDA and training); checked that it rebuilds the processed dataset exactly, and pinned scikit-learn so the split reproduces | Puneet Bajaj | 29 Oct 2026 | Jayesh Bansal |
| Report | Milestone 2 report sections 1 to 4 and 6 to 8 (dataset documentation, splits, folder structure, reproducibility) | Puneet Bajaj, Jayesh Bansal | 29 Oct 2026 | Jayesh Bansal |
| Snake masks | Built [`notebooks/04_sam_masks.ipynb`](notebooks/04_sam_masks.ipynb) (Grounding DINO and SAM 2.1); ran a 500-photo pilot through four versions (hand removal, single-box rule, quality flags, two-GPU speed-up) and started the full sharded run | Puneet Bajaj | 29 Oct 2026 | Jayesh Bansal |
| Presentation | Prepared the Milestone 2 dataset presentation slides ([`SerpentGuard_AI_Milestone2_Dataset_Presentation.pdf`](documentation/milestone%202/SerpentGuard_AI_Milestone2_Dataset_Presentation.pdf)) | Vikas | 29 Oct 2026 | Vikas |

### Milestone 2 acknowledgment

| Team member name | Roll Number | Signature / acknowledgment | Date |
|---|---|---|---|
|Jayesh Bansal|24f100185|![Jayesh Bansal](https://drive.google.com/uc?export=download&id=1imepTm_t9vgJVL367tWU-LPYcLq9Zet0)|29/10/2026|
| Vikas | 23f3001800 | Vikas | 29/10/2026 |
| Puneet Bajaj | 23f3002416 | | |
| Manas Rastogi | 22f3001477 | | |

## Week 1: 18 to 22 October 2026 (Milestone 1, problem definition and literature review)

### Contribution entries

| Work item | Contribution / evidence | Contributor(s) | Date or period | Reviewed / confirmed by |
|---|---|---|---|---|
| Repository setup | Created the GitHub repository | Puneet Bajaj | 18 Oct 2026 | Puneet Bajaj |
| Literature review | Summarized SnakeCLEF benchmarks and added a sourced comparison of Google Lens/Search, Gemini Live, ChatGPT camera/video, direct LLM answers, and prior mobile/offline/video snake systems. | Jayesh Bansal | 22 Oct 2026 | Jayesh Bansal |
| Report editing and verification | Updated the report with current product/research comparisons, cited implementation precedents, and marked unbuilt capabilities as proposals rather than results. | Jayesh Bansal | 22 Oct 2026 | Jayesh Bansal |
| Presentation | Prepared the Milestone 1 slide deck. | Vikas | 22 Oct 2026 | Vikas |
| Feasibility review and data check | Checked the plan against each milestone's requirements. Counted the available data with the iNaturalist API (27 Indian species with at least 200 CC-licensed research-grade observations each), located the released PLOS baseline model, the Open Images snake boxes and the WHO species categories, and found no public species-labelled snake video. | Puneet Bajaj | 22 Oct 2026 | Jayesh Bansal |
| Report and slide revision | Added scope, stakeholders and measurable targets for the M1 rubric, the species table, real data samples and two output mockups, the grouped-split and video-clip plan, the Kaggle and Colab compute plan, and the detector, tracker and classifier architecture. Corrected the PLOS first author, replaced slide figures and chart values that had no source, matched the slide claims to the report, and added a slide on scope, stakeholders and targets. | Puneet Bajaj | 22 Oct 2026 | Jayesh Bansal |
| Repository documentation | Wrote the README, extended `.gitignore` to keep data and model files out of git, and fixed the links in this log. | Puneet Bajaj | 22 Oct 2026 | Jayesh Bansal |
| Lookalike species research | Counted how often iNaturalist identifiers in India confuse our 27 classes (25 pairs that join a WHO-listed and a not-listed species, 107 confusions), checked distinguishing features against the WHO SEARO 2016 guidelines and published papers, and added report section 3.6 with four new references. | Manas Rastogi | 22 Oct 2026 | Manas Rastogi |

### Member contribution summary

| Member name | Work completed | Evidence / report sections | Member confirmation |
|---|---|---|---|
| Jayesh Bansal | Project report | [project-report.md](documentation/milestone%201/project-report.md) | Jayesh Bansal |
| Vikas | Presentation preparation | [SerpentGuard_AI_Group5_Presentation.pdf](documentation/milestone%201/assets/SerpentGuard_AI_Group5_Presentation.pdf) | Vikas |
| Puneet Bajaj | Repository setup; feasibility and data check; report sections 1, 3, 5, 6, 7 and 9 and the references; data samples and output mockups; slide revision; README | [project-report.md](documentation/milestone%201/project-report.md), [README.md](README.md) | Puneet Bajaj |
| Manas Rastogi | Lookalike species pairs: iNaturalist confusion counts, distinguishing features and how they feed the evaluation; report section 3.6 and references 29 to 32 | [project-report.md, section 3.6](documentation/milestone%201/project-report.md#36-lookalike-species-pairs) | Manas Rastogi |

All members must also sign the acknowledgment page at the end of the [Milestone 1 project report](documentation/milestone%201/project-report.md) and the last slide of the presentation.

## Team review and acknowledgment

By signing, each member confirms that they have reviewed this log, that their own entries are accurate, and that they agree with the submission.

| Team member name | Roll Number | Signature / acknowledgment | Date |
|---|---|---|---|
| Jayesh Bansal | 24f100185 |![Jayesh Bansal](https://drive.google.com/uc?export=download&id=1imepTm_t9vgJVL367tWU-LPYcLq9Zet0)|22/10/2026|
| Vikas | 23f3001800 | Vikas | 22/10/2026 |
| Puneet Bajaj | 23f3002416 | Puneet Bajaj | 22/10/2026 |
| Manas Rastogi | 22f3001477 | ![Manas Rastogi](https://drive.google.com/uc?export=download&id=1j9vC0yjI-eb3lGfETUdnK3GAXq77__lT) | 22/10/2026 |
