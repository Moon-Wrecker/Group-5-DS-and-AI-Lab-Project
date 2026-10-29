# SerpentGuard AI: snake detection and classification

Group 5, DS and AI Lab Project (IIT Madras BS, DS & AI Lab course).

SerpentGuard AI finds a snake in a photo or a live camera feed and suggests its species from a fixed list of 27 Indian species. It shows the WHO medical-importance category of each candidate and says "uncertain" or "unknown" when it is not confident. Live video runs the same models as photos, one frame at a time: a YOLOv8n detector, ByteTrack tracking, a MobileViT classifier, and smoothing over recent frames. No LLM or internet API is involved.

> Safety: this is a student research and education project. It does not diagnose bites or give treatment advice, and "no snake detected" never means an area is safe. In an emergency, go to the nearest hospital.

## Team

| Member | Role |
|---|---|
| Jayesh Bansal | Team lead |
| Vikas | Member |
| Puneet Bajaj | Member |
| Manas Rastogi | Member |

Each member's weekly contributions are in [work-contribution-log.md](work-contribution-log.md).

## Milestones

| # | Milestone | Due (2026) | Status | Documents |
|---|---|---|---|---|
| 1 | Problem definition and literature review | 22 Oct | Submitted | [Report](documentation/milestone%201/project-report.md) · [Slides](documentation/milestone%201/assets/SerpentGuard_AI_Group5_Presentation.pdf) |
| 2 | Dataset preparation | 29 Oct | Submitted | [Report](documentation/milestone%202/project-report.md) · [Dataset notebook](notebooks/m2_dataset_pipeline.ipynb) |
| 3 | Model architecture and end-to-end pipeline | 5 Nov | Planned | |
| 4 | Model training | 19 Nov | Planned | |
| 5 | Evaluation and analysis | 26 Nov | Planned | |
| 6 | Deployment and documentation | 10 Dec | Planned | |

Course requirements: [guidelines](https://bsc-iitm.github.io/dsai-lab-project/guidelines.html) · [milestones](https://bsc-iitm.github.io/dsai-lab-project/milestones.html).

## Repository layout

```text
documentation/          milestone reports and slides (one folder per milestone)
notebooks/              Kaggle notebooks: m2_dataset_pipeline.ipynb rebuilds the dataset,
                        m2_sam_masks.ipynb makes snake masks with Grounding DINO and SAM 2.1
data/                   class table and split report (images live on Kaggle, never in git)
work-contribution-log.md  weekly per-member contributions
```

To rebuild the dataset, open `notebooks/m2_dataset_pipeline.ipynb` on Kaggle with internet on and attach `puneetbajajiitm/serpentguard-indian-snakes`. Stages 2 to 4 take about an hour on CPU and reproduce our splits exactly.

## Data and licences

Training images come from iNaturalist research-grade observations of the 289 snake species recorded in India, with photos from anywhere in the world ([Milestone 2 report](documentation/milestone%202/project-report.md)). Each photo keeps its photographer's licence and attribution, recorded per photo in `metadata.csv`: 69% are Creative Commons and 31% are all rights reserved. The images are kept in private Kaggle datasets shared with the team and course staff, never committed here, and used only for this non-commercial course project. The `cc_licensed` column selects a Creative Commons-only subset.
