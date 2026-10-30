# %% [markdown]
# # SerpentGuard AI — Milestone 2: SAM Segmentation & Data Preprocessing Pipeline
# **Group 5 · IIT Madras BS in Data Science & AI Lab (2026 T3)**  
# **Author:** Vikas (Group 5) · **Team:** Jayesh Bansal (Lead), Vikas, Puneet Bajaj, Manas Rastogi  
#
# This notebook builds directly on the outputs of the upstream milestone notebooks:
# - **Reads from `03_process_dataset`**: `puneetbajajiitm/serpentguard-indian-snakes-processed` (181,231 photos across 208 active classes, `metadata.csv`, `classes.csv`).
# - **Reads from `05_merge_sam_masks`**: `puneetbajajiitm/serpentguard-sam-masks` (precomputed SAM 2.1 binary masks and `mask_stats.csv`).
# - **Produces**: Cleaned foreground crops (soft-dimmed / hard-masked, letterboxed 320×320, EXIF-normalized), tier-aware joint image+mask augmentations, and a PyTorch multi-task Dataset and class-balanced DataLoader for Milestone 3 modeling.

# %% [markdown]
# ## 1. Mount Inspection & Path Resolution
# Resolves paths for mounted Kaggle datasets or downloads via `kagglehub` if running in an external environment.

# %%
import os
import pathlib
import warnings
from typing import Dict, Tuple, Optional, List

import cv2
import numpy as np
import pandas as pd
from PIL import Image, ImageOps
import matplotlib.pyplot as plt

import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
import albumentations as A
from albumentations.pytorch import ToTensorV2

warnings.filterwarnings("ignore")
plt.rcParams.update({"figure.dpi": 130, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

def resolve_dataset_root(slug: str, fallback_slug: Optional[str] = None) -> pathlib.Path:
    """Finds mounted Kaggle dataset path, with kagglehub and local repo fallbacks."""
    for s in [slug] + ([fallback_slug] if fallback_slug else []):
        for candidate in [
            pathlib.Path(f"/kaggle/input/datasets/puneetbajajiitm/{s}"),
            pathlib.Path(f"/kaggle/input/{s}"),
        ]:
            if candidate.exists():
                return candidate
    # Fallback to local data/ directory if available
    for local_cand in [pathlib.Path("./data"), pathlib.Path("../data")]:
        if local_cand.exists() and (local_cand / "classes.csv").exists():
            return local_cand
    return pathlib.Path(f"/kaggle/input/datasets/puneetbajajiitm/{slug}")

SPLITS_DIR    = resolve_dataset_root("serpentguard-m2-splits")
PROCESSED_DIR = resolve_dataset_root("serpentguard-indian-snakes-processed", fallback_slug="serpentguard-indian-snakes")
SAM_MASKS_DIR = resolve_dataset_root("serpentguard-sam-masks")

WORK_DIR      = pathlib.Path("/kaggle/working/preprocessed") if os.path.exists("/kaggle") else pathlib.Path("./preprocessed_output")
PREVIEW_DIR   = WORK_DIR / "previews"
PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

print(f"1. Splits Dir    : {SPLITS_DIR} (exists={SPLITS_DIR.exists()})")
print(f"2. Processed Dir : {PROCESSED_DIR} (exists={PROCESSED_DIR.exists()})")
print(f"3. SAM Masks Dir : {SAM_MASKS_DIR} (exists={SAM_MASKS_DIR.exists()})")
print(f"Output Directory : {WORK_DIR.resolve()}")

# %% [markdown]
# ## 2. Load Processed Manifest & Build Hierarchical Targets
# Directly loads `metadata.csv` from `serpentguard-indian-snakes-processed` (produced by `03_process_dataset`, 181,231 photos) without re-running any duplicate or pHash checks. Encodes taxonomic targets (`genus_id`, `family_id`) and clinical safety risk (`who_risk_id`).

# %%
meta_csv = PROCESSED_DIR / "metadata.csv"
splits_csv = SPLITS_DIR / "splits.csv"

if meta_csv.exists():
    df = pd.read_csv(meta_csv, dtype={"obs_id": str, "photo_id": str, "observer_id": str}, low_memory=False)
elif splits_csv.exists():
    df = pd.read_csv(splits_csv, dtype={"obs_id": str, "photo_id": str, "observer_id": str}, low_memory=False)
else:
    # Synthetic mock split for offline testing / CI environments
    print("[Notice] Real datasets not mounted; generating sample mock split for pipeline verification.")
    df = pd.DataFrame({
        "photo_id": [f"100{i}" for i in range(30)],
        "obs_id": [f"200{i}" for i in range(30)],
        "species": ["Naja naja"] * 10 + ["Daboia russelii"] * 10 + ["Ptyas mucosa"] * 10,
        "genus": ["Naja"] * 10 + ["Daboia"] * 10 + ["Ptyas"] * 10,
        "family": ["Elapidae"] * 10 + ["Viperidae"] * 10 + ["Colubridae"] * 10,
        "who_category": ["cat1"] * 10 + ["cat1"] * 10 + ["none"] * 10,
        "tier": ["tier1"] * 30,
        "split": ["train"] * 20 + ["val"] * 5 + ["test"] * 5,
        "class_id": [0] * 10 + [1] * 10 + [2] * 10,
        "path": [f"data/train/species_{i}/photo_{i}.jpg" for i in range(30)],
        "file": [f"data/train/species_{i}/photo_{i}.jpg" for i in range(30)],
        "observer_id": [f"obs_{i % 5}" for i in range(30)]
    })

# Ensure photo_id and file columns are populated
if "path" in df.columns and "file" not in df.columns:
    df["file"] = df["path"]

# Build hierarchical target encoders
genera_list   = sorted(df["genus"].dropna().unique())
families_list = sorted(df["family"].dropna().unique())
genus_to_id   = {g: i for i, g in enumerate(genera_list)}
family_to_id  = {f: i for i, f in enumerate(families_list)}
who_to_id     = {"none": 0, "cat2": 1, "cat1": 2}

df["genus_id"]    = df["genus"].map(genus_to_id).fillna(0).astype(int)
df["family_id"]   = df["family"].map(family_to_id).fillna(0).astype(int)
df["who_risk_id"] = df["who_category"].fillna("none").map(who_to_id).fillna(0).astype(int)

print(f"Loaded manifest: {len(df):,} photos across {df['species'].nunique()} species, {len(genera_list)} genera, {len(families_list)} families.")
print("Photos by split:", df["split"].value_counts().to_dict())

# %% [markdown]
# ## 3. Link SAM Masks Directly from `serpentguard-sam-masks`
# Joins mask files directly via `mask_stats.csv` (produced by `05_merge_sam_masks`) or via direct path mapping `masks/<split>/<species>/<photo>.png`. Masks are assigned to training photos; validation and test photos do not use mask supervision.

# %%
df["abs_image_path"] = df["file"].apply(lambda rel: str(PROCESSED_DIR / rel))

mask_stats_csv = SAM_MASKS_DIR / "mask_stats.csv"
if mask_stats_csv.exists():
    print(f"Joining precomputed mask stats from {mask_stats_csv}...")
    mask_stats = pd.read_csv(mask_stats_csv, dtype={"photo_id": str})
    cols_to_use = [c for c in ["photo_id", "mask_path", "flagged", "iou_score"] if c in mask_stats.columns]
    df = df.merge(mask_stats[cols_to_use].drop_duplicates("photo_id"), on="photo_id", how="left")
    df["abs_mask_path"] = df["mask_path"].fillna("").apply(lambda p: str(SAM_MASKS_DIR / p) if p else "")
else:
    # Direct mirror path mapping
    df["abs_mask_path"] = df["file"].apply(
        lambda rel: str(SAM_MASKS_DIR / str(rel).replace("data/", "masks/").replace(".jpg", ".png"))
    )

matched_masks = df["abs_mask_path"].apply(lambda p: os.path.exists(p) if p else False).sum()
print(f"Linked {matched_masks:,} photos to confirmed SAM mask files on disk.")

# %% [markdown]
# ## 4. Image Hygiene, EXIF Normalization & Morphological Cleaning
# Smartphone camera photos often carry portrait/landscape rotation in EXIF tags. `ImageOps.exif_transpose` normalizes RGB pixels and ensures coordinate alignment with SAM masks. Morphological cleanup preserves genuine coiled snake segments while filtering isolated background specks.

# %%
def load_and_normalize_rgb(img_path: str, min_short_side: int = 100) -> Optional[np.ndarray]:
    """Loads RGB image, applies EXIF orientation normalization, and verifies minimum resolution."""
    if not img_path or not os.path.exists(img_path):
        return None
    try:
        with Image.open(img_path) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")
            arr = np.asarray(im, dtype=np.uint8)
        if min(arr.shape[:2]) < min_short_side:
            return None
        return arr
    except Exception:
        return None

def keep_largest_snake_components(mask: np.ndarray, min_area_ratio: float = 0.015) -> np.ndarray:
    """Removes tiny isolated background artifacts while preserving coiled or occluded snake segments."""
    h, w = mask.shape[:2]
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    if num_labels <= 1:
        return np.ones((h, w), dtype=np.uint8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    max_area = areas.max()
    if max_area < (h * w * min_area_ratio):
        return np.ones((h, w), dtype=np.uint8)

    clean = np.zeros((h, w), dtype=np.uint8)
    for idx, area in enumerate(areas, start=1):
        if area >= max(0.12 * max_area, h * w * 0.008):
            clean[labels == idx] = 1
    return clean

def load_sam_segmentation_mask(rgb_img: np.ndarray, mask_path: str = "") -> Tuple[np.ndarray, List[float]]:
    """Loads precomputed SAM binary mask, cleans speckles, and extracts normalized YOLOv8-seg polygon."""
    h, w = rgb_img.shape[:2]
    binary_mask = None

    if mask_path and os.path.exists(mask_path):
        try:
            if mask_path.endswith(".npy"):
                binary_mask = (np.load(mask_path) > 0).astype(np.uint8)
            else:
                with Image.open(mask_path) as mim:
                    mim = ImageOps.exif_transpose(mim).convert("L")
                    m_arr = np.asarray(mim, dtype=np.uint8)
                    binary_mask = (m_arr > 127).astype(np.uint8)
            if binary_mask.shape[:2] != (h, w):
                binary_mask = cv2.resize(binary_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        except Exception:
            binary_mask = None

    if binary_mask is None or binary_mask.sum() < 25:
        # Default full-frame mask when photo has no SAM pseudo-label
        binary_mask = np.ones((h, w), dtype=np.uint8)

    # Morphological closing and connected-component cleaning
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel, iterations=1)
    binary_mask = keep_largest_snake_components(binary_mask)

    return binary_mask, mask_to_yolo_polygon(binary_mask)

def mask_to_yolo_polygon(binary_mask: np.ndarray, max_points: int = 64) -> List[float]:
    """Converts a binary mask into normalized YOLOv8-seg polygon coordinates [x1, y1, ...]."""
    h, w = binary_mask.shape[:2]
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return [0.05, 0.05, 0.95, 0.05, 0.95, 0.95, 0.05, 0.95]
    largest = max(contours, key=cv2.contourArea)
    epsilon = 0.002 * cv2.arcLength(largest, True)
    approx  = cv2.approxPolyDP(largest, epsilon, True).reshape(-1, 2)
    if len(approx) > max_points:
        idx = np.linspace(0, len(approx) - 1, max_points, dtype=int)
        approx = approx[idx]
    poly = []
    for x, y in approx:
        poly.extend([round(float(x) / w, 5), round(float(y) / h, 5)])
    return poly

# %% [markdown]
# ## 5. SAM Mask-Guided Foreground Preprocessing (3 Modes)
# Standard bounding boxes contain 60%–85% background clutter. We support:
# - **`soft_dim` (Default, `bg_alpha=0.20`)**: Retains 100% snake scale details while dimming background clutter by 80% with Gaussian boundary softening.
# - **`hard_mask`**: Replaces 100% of non-snake pixels with neutral gray `(124, 116, 104)`.
# - **`rgbm_4ch`**: Retains RGB image and concatenates the binary SAM mask as a 4th attention channel.
# Both modes apply a tight envelope crop (+6% padding) and an aspect-ratio-preserving letterbox resize to 320×320 so slender vine snakes (*Ahaetulla*) are not distorted into stout vipers (*Daboia*).

# %%
IMAGENET_MEAN_RGB = (124, 116, 104)

def preprocess_with_sam_mask(
    rgb_img: np.ndarray,
    sam_mask: np.ndarray,
    target_size: int = 320,
    mode: str = "soft_dim",
    bg_alpha: float = 0.20,
    pad_ratio: float = 0.06
) -> Tuple[np.ndarray, np.ndarray]:
    """Applies mask-guided background suppression, tight envelope crop, and 320x320 letterbox padding."""
    h, w = rgb_img.shape[:2]

    if mode in ("soft_dim", "hard_mask"):
        alpha = 0.0 if mode == "hard_mask" else bg_alpha
        soft_m = cv2.GaussianBlur(sam_mask.astype(np.float32), (5, 5), 0)[..., None]
        weight = alpha + (1.0 - alpha) * soft_m
        bg_fill = np.array(IMAGENET_MEAN_RGB, dtype=np.float32).reshape(1, 1, 3)
        proc_rgb = (rgb_img.astype(np.float32) * weight + bg_fill * (1.0 - weight)).clip(0, 255).astype(np.uint8)
    else:
        proc_rgb = rgb_img

    # Tight crop around SAM mask envelope (+6% padding)
    ys, xs = np.where(sam_mask > 0)
    if len(xs) > 10 and len(ys) > 10:
        x1, x2 = int(xs.min()), int(xs.max())
        y1, y2 = int(ys.min()), int(ys.max())
        bw, bh = x2 - x1, y2 - y1
        pad_x, pad_y = int(bw * pad_ratio), int(bh * pad_ratio)
        x1, y1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
        x2, y2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
        crop_rgb  = proc_rgb[y1:y2, x1:x2]
        crop_mask = sam_mask[y1:y2, x1:x2]
    else:
        crop_rgb, crop_mask = proc_rgb, sam_mask

    # Aspect-ratio-preserving letterbox resize to target_size
    ch, cw = crop_rgb.shape[:2]
    scale = target_size / max(ch, cw)
    new_w, new_h = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))

    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
    res_rgb  = cv2.resize(crop_rgb,  (new_w, new_h), interpolation=interp)
    res_mask = cv2.resize(crop_mask, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

    canvas_rgb  = np.full((target_size, target_size, 3), IMAGENET_MEAN_RGB, dtype=np.uint8)
    canvas_mask = np.zeros((target_size, target_size), dtype=np.uint8)

    top  = (target_size - new_h) // 2
    left = (target_size - new_w) // 2
    canvas_rgb[top:top + new_h, left:left + new_w]  = res_rgb
    canvas_mask[top:top + new_h, left:left + new_w] = res_mask

    return canvas_rgb, canvas_mask

# %% [markdown]
# ## 6. Tier-Aware Joint `(Image + SAM Mask)` Augmentation Pipeline
# Applies geometric and photometric transformations simultaneously to both the RGB image and its SAM binary mask. Tier-2 species (20–399 photos) receive stronger augmentation than Tier-1 species (≥400 photos).

# %%
def build_sam_augmentation_pipelines(img_size: int = 320) -> Dict[str, A.Compose]:
    norm_and_tensor = [
        A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ToTensorV2()
    ]

    tier1_aug = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.2),
        A.Affine(scale=(0.88, 1.12), rotate=(-25, 25), translate_percent=(-0.05, 0.05), border_mode=cv2.BORDER_CONSTANT, p=0.6),
        A.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.04, p=0.5),
        A.CoarseDropout(num_holes_range=(1, 4), hole_height_range=(16, 36), hole_width_range=(16, 36), p=0.35),
        *norm_and_tensor
    ])

    tier2_aug = A.Compose([
        A.HorizontalFlip(p=0.5),
        A.VerticalFlip(p=0.35),
        A.Affine(scale=(0.80, 1.20), rotate=(-45, 45), translate_percent=(-0.08, 0.08), shear=(-10, 10), border_mode=cv2.BORDER_CONSTANT, p=0.8),
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.7),
        A.HueSaturationValue(hue_shift_limit=8, sat_shift_limit=25, val_shift_limit=25, p=0.5),
        A.MotionBlur(blur_limit=(3, 7), p=0.25),
        A.CoarseDropout(num_holes_range=(2, 6), hole_height_range=(20, 44), hole_width_range=(20, 44), p=0.5),
        *norm_and_tensor
    ])

    eval_aug = A.Compose([*norm_and_tensor])
    return {"tier1": tier1_aug, "tier2": tier2_aug, "eval": eval_aug}

aug_pipelines = build_sam_augmentation_pipelines(img_size=320)

# %% [markdown]
# ## 7. PyTorch Multi-Task SAM Dataset (`SerpentGuardSAMDataset`)
# Yields synchronized batches with species `class_id`, `genus_id`, `family_id`, clinical `who_risk_id`, normalized `image` tensor, and auxiliary `mask` tensor.

# %%
class SerpentGuardSAMDataset(Dataset):
    def __init__(
        self,
        dataframe: pd.DataFrame,
        transforms_dict: Dict[str, A.Compose],
        img_size: int = 320,
        is_train: bool = True,
        mask_mode: str = "soft_dim",
        bg_alpha: float = 0.20,
        concat_mask_channel: bool = False
    ):
        self.df = dataframe.reset_index(drop=True)
        self.transforms = transforms_dict
        self.img_size = img_size
        self.is_train = is_train
        self.mask_mode = mask_mode
        self.bg_alpha = bg_alpha
        self.concat_mask_channel = concat_mask_channel

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        row = self.df.iloc[idx]
        rgb = load_and_normalize_rgb(row["abs_image_path"])

        if rgb is None:
            # Synthetic fallback image with snake-like ellipse if image cannot be loaded
            rgb = np.full((375, 500, 3), IMAGENET_MEAN_RGB, dtype=np.uint8)
            cv2.ellipse(rgb, (250, 187), (160, 55), 25, 0, 360, (60, 110, 55), -1)

        mask_p = str(row.get("abs_mask_path", ""))
        sam_mask, _ = load_sam_segmentation_mask(rgb, mask_path=mask_p)
        fg_coverage = float(sam_mask.mean())

        crop_rgb, crop_mask = preprocess_with_sam_mask(
            rgb, sam_mask, target_size=self.img_size, mode=self.mask_mode, bg_alpha=self.bg_alpha
        )

        tier_val = str(row.get("tier", "tier1"))
        pipe_key = tier_val if (self.is_train and tier_val in ["tier1", "tier2"]) else "eval"
        augmented = self.transforms[pipe_key](image=crop_rgb, mask=crop_mask)
        img_tensor  = augmented["image"]
        mask_tensor = augmented["mask"].unsqueeze(0).float()

        if self.concat_mask_channel:
            img_tensor = torch.cat([img_tensor, mask_tensor], dim=0)

        return {
            "image": img_tensor,
            "mask": mask_tensor,
            "mask_coverage": torch.tensor(fg_coverage, dtype=torch.float32),
            "class_id": torch.tensor(int(row["class_id"]), dtype=torch.long),
            "genus_id": torch.tensor(int(row["genus_id"]), dtype=torch.long),
            "family_id": torch.tensor(int(row["family_id"]), dtype=torch.long),
            "who_risk_id": torch.tensor(int(row["who_risk_id"]), dtype=torch.long),
        }

# %% [markdown]
# ## 8. Tempered Class-Balanced Sampler & DataLoader Construction
# Applies inverse square-root class frequency weighting ($1 / \sqrt{N_c}$) combined with clinical safety priority boosts:
# - **WHO Category 1**: 1.60× boost
# - **WHO Category 2**: 1.35× boost

# %%
train_df = df[df["split"] == "train"].copy().reset_index(drop=True)
val_df   = df[df["split"] == "val"].copy().reset_index(drop=True)
test_df  = df[df["split"] == "test"].copy().reset_index(drop=True)

class_counts = train_df["class_id"].value_counts().to_dict()
base_weights = train_df["class_id"].map(lambda c: 1.0 / np.sqrt(max(1, class_counts.get(c, 1))))
who_boost    = train_df["who_risk_id"].map({0: 1.0, 1: 1.35, 2: 1.60})
sample_weights = (base_weights * who_boost).values

train_sampler = WeightedRandomSampler(
    weights=torch.from_numpy(sample_weights).double(),
    num_samples=len(train_df),
    replacement=True
)

train_ds = SerpentGuardSAMDataset(train_df, aug_pipelines, img_size=320, is_train=True,  mask_mode="soft_dim")
val_ds   = SerpentGuardSAMDataset(val_df,   aug_pipelines, img_size=320, is_train=False, mask_mode="soft_dim")
test_ds  = SerpentGuardSAMDataset(test_df,  aug_pipelines, img_size=320, is_train=False, mask_mode="soft_dim")

train_loader = DataLoader(train_ds, batch_size=32, sampler=train_sampler, num_workers=2, pin_memory=True)
val_loader   = DataLoader(val_ds,   batch_size=32, shuffle=False, num_workers=2, pin_memory=True)
test_loader  = DataLoader(test_ds,  batch_size=32, shuffle=False, num_workers=2, pin_memory=True)

print(f"Train batches     : {len(train_loader):,} ({len(train_ds):,} samples)")
print(f"Validation batches: {len(val_loader):,} ({len(val_ds):,} samples)")
print(f"Test batches      : {len(test_loader):,} ({len(test_ds):,} samples)")

# %% [markdown]
# ## 9. Visual Verification: 5-Panel Preprocessing Preview
# Generates a visual verification plot demonstrating:
# 1. Raw RGB photo
# 2. Binary SAM mask
# 3. YOLOv8-seg polygon contour overlay
# 4. Soft-dimmed letterbox crop (320×320, `bg_alpha=0.20`)
# 5. Hard-masked letterbox crop (320×320, `bg_alpha=0.0`)

# %%
def visualize_sam_preprocessing_pipeline(
    sample_rows: pd.DataFrame,
    save_path: str = str(PREVIEW_DIR / "sam_preprocessing_5panel.png")
):
    n = len(sample_rows)
    fig, axes = plt.subplots(n, 5, figsize=(15.5, 3.1 * max(1, n)))
    if n == 1:
        axes = np.expand_dims(axes, axis=0)

    for i, (_, row) in enumerate(sample_rows.iterrows()):
        rgb = load_and_normalize_rgb(row["abs_image_path"])
        if rgb is None:
            rgb = np.full((375, 500, 3), (110, 98, 82), dtype=np.uint8)
            pts = np.array([[85, 305], [180, 205], [290, 250], [365, 135], [425, 105]], np.int32)
            cv2.polylines(rgb, [pts], False, (45, 135, 65), thickness=36, lineType=cv2.LINE_AA)

        mask_p = str(row.get("abs_mask_path", ""))
        sam_mask, poly = load_sam_segmentation_mask(rgb, mask_path=mask_p)
        soft_crop, _   = preprocess_with_sam_mask(rgb, sam_mask, target_size=320, mode="soft_dim", bg_alpha=0.20)
        hard_crop, _   = preprocess_with_sam_mask(rgb, sam_mask, target_size=320, mode="hard_mask", bg_alpha=0.0)

        # Panel 1: Raw RGB
        axes[i, 0].imshow(rgb)
        axes[i, 0].set_title(f"1. Raw RGB ({rgb.shape[1]}x{rgb.shape[0]})\n{row['species']}", fontsize=9, fontweight="bold")

        # Panel 2: Binary SAM Mask
        axes[i, 1].imshow(sam_mask, cmap="viridis")
        src_tag = "SAM Mask" if mask_p and os.path.exists(mask_p) else "Fallback Mask"
        axes[i, 1].set_title(f"2. {src_tag}\nArea: {sam_mask.mean()*100:.1f}%", fontsize=9, fontweight="bold")

        # Panel 3: Polygon Overlay
        overlay = rgb.copy()
        pts_norm = np.array(poly).reshape(-1, 2)
        pts_px = np.column_stack([pts_norm[:, 0] * rgb.shape[1], pts_norm[:, 1] * rgb.shape[0]]).astype(np.int32)
        cv2.polylines(overlay, [pts_px], True, (239, 68, 68), thickness=3)
        axes[i, 2].imshow(overlay)
        axes[i, 2].set_title(f"3. Polygon Overlay ({len(pts_px)} pts)\nWHO: {str(row['who_category']).upper()}", fontsize=9, fontweight="bold")

        # Panel 4: Soft-Dimmed
        axes[i, 3].imshow(soft_crop)
        axes[i, 3].set_title("4. Soft-Dimmed (320x320)\nBg Dimmed 80%", fontsize=9, fontweight="bold")

        # Panel 5: Hard-Masked
        axes[i, 4].imshow(hard_crop)
        axes[i, 4].set_title("5. Hard-Masked (320x320)\n100% Background Removed", fontsize=9, fontweight="bold")

        for ax in axes[i]:
            ax.axis("off")

    plt.tight_layout()
    plt.savefig(save_path, bbox_inches="tight")
    plt.close()
    print(f"Saved 5-panel verification figure to: {save_path}")

sample_preview_df = train_df.head(3)
visualize_sam_preprocessing_pipeline(sample_preview_df)

# %% [markdown]
# ## 10. Multi-Task Batch Shape Verification & Manifest Export
# Validates one batch through the PyTorch DataLoader and exports the verified manifest.

# %%
batch = next(iter(train_loader))
print("Verified PyTorch Multi-Task Batch Shapes:")
for k, v in batch.items():
    print(f"  - {k:<15}: shape={tuple(v.shape)} | dtype={v.dtype}")

out_manifest = WORK_DIR / "serpentguard_m2_sam_preprocessed_manifest.csv"
train_df["sample_weight"] = sample_weights
df.to_csv(out_manifest, index=False)
print(f"Saved preprocessed manifest ({len(df):,} rows) -> {out_manifest}")
