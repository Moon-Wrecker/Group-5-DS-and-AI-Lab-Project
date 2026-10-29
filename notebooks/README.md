# Notebooks

Each notebook attaches its inputs by handle (`kagglehub.dataset_download`), does one job, and saves its
output as a private Kaggle dataset under the account that runs it. Later notebooks read those datasets,
so any step can be rerun on its own without redoing the steps before it.

| # | Notebook | Reads | Saves | Runs on | Time |
|---|---|---|---|---|---|
| 01 | [`01_build_raw_dataset.ipynb`](01_build_raw_dataset.ipynb) | iNaturalist API | `serpentguard-indian-snakes` | CPU, internet on | about 2.5 h |
| 02 | [`02_clean_and_split.ipynb`](02_clean_and_split.ipynb) | 01 | `serpentguard-m2-splits` | CPU, internet on | about 3 min |
| 03 | [`03_process_dataset.ipynb`](03_process_dataset.ipynb) | 01 and 02 | `serpentguard-indian-snakes-processed` | CPU, internet on | about 35 min |
| 04 | [`04_sam_masks.ipynb`](04_sam_masks.ipynb) | 01 and 02 | snake masks, one zip per shard (notebook output) | GPU T4 x2, internet on | about 40 min per shard |
| 05 | [`05_merge_sam_masks.ipynb`](05_merge_sam_masks.ipynb) | the 04 shards | `serpentguard-sam-masks` | CPU | a few minutes |
| | [`load_dataset_example.ipynb`](load_dataset_example.ipynb) | 02 and 03 | nothing | CPU | a minute |

The team's copies, built on 24 to 29 October 2026, are private datasets owned by `puneetbajajiitm`:

- `puneetbajajiitm/serpentguard-indian-snakes` (raw photos and manifest)
- `puneetbajajiitm/serpentguard-m2-splits` (split table, class table, removed photos)
- `puneetbajajiitm/serpentguard-indian-snakes-processed` (final folders and metadata)
- `puneetbajajiitm/serpentguard-sam-masks` (snake masks for 24,907 training photos, with quality flags)

Ask the team to add your Kaggle username as a collaborator. To rebuild a step under your own account,
run its notebook; to build on our copies instead, keep the default handles in the notebook's first cell.

Notes:

- Notebook 02 pins scikit-learn 1.9.1, the version that made our split. `StratifiedGroupKFold` assigns
  folds differently in other releases.
- Notebook 04 splits its photos into shards (`SHARD_INDEX`, `SHARD_COUNT`) so several accounts can run
  it at once. Each shard saves `masks_shard<k>.zip` and its own review list.
- Always take class ids from `classes.csv` (`class_id`). `val/` and `test/` lack some species folders,
  so loaders that number classes by folder (plain `ImageFolder`) would mislabel photos.

## Adding an EDA or training notebook

Start from `load_dataset_example.ipynb`, name the notebook after what it does (for example
`eda_class_balance.ipynb`), and read from the datasets above instead of copying data. If it produces
something other notebooks need, save that as its own dataset and add a row to the table.
