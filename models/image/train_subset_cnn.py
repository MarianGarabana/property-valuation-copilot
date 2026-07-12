from pathlib import Path

import numpy as np
import polars as pl
import torch
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, balanced_accuracy_score, roc_auc_score
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ResNet18_Weights, resnet18

from download_tiles import TILE_DIR
from tiles import SUBSET_MANIFEST_PATH, TILE_ASSIGNMENT_PATH

FEATURES_PATH = Path(__file__).resolve().parent / "features_subset.npz"
BATCH_SIZE = 128
SEED = 42


class TileDataset(Dataset):
    def __init__(self, tile_ids: list[str], transform):
        self.tile_ids = tile_ids
        self.transform = transform

    def __len__(self) -> int:
        return len(self.tile_ids)

    def __getitem__(self, idx: int):
        img = Image.open(TILE_DIR / f"{self.tile_ids[idx]}.jpg").convert("RGB")
        return self.transform(img)


def extract_features(tile_ids: list[str]) -> np.ndarray:
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    weights = ResNet18_Weights.IMAGENET1K_V1
    model = resnet18(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval().to(device)
    dataset = TileDataset(tile_ids, weights.transforms())
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, num_workers=4)
    chunks = []
    with torch.no_grad():
        for i, batch in enumerate(loader):
            chunks.append(model(batch.to(device)).cpu().numpy())
            if (i + 1) % 20 == 0:
                print(f"features {(i + 1) * BATCH_SIZE}/{len(tile_ids)}", flush=True)
    return np.concatenate(chunks)


def main() -> None:
    manifest = pl.read_parquet(SUBSET_MANIFEST_PATH)
    exists = pl.Series("has_file", [(TILE_DIR / f"{t}.jpg").exists() for t in manifest["tile_id"]])
    manifest = manifest.with_columns(exists)
    print(manifest.group_by("role", "has_file").len().sort("role", "has_file"))
    manifest = manifest.filter(pl.col("has_file"))

    if FEATURES_PATH.exists():
        cached = np.load(FEATURES_PATH, allow_pickle=False)
        feats, ids = cached["features"], list(cached["tile_ids"])
    else:
        ids = manifest["tile_id"].to_list()
        feats = extract_features(ids)
        np.savez_compressed(FEATURES_PATH, features=feats, tile_ids=np.array(ids))

    order = {t: i for i, t in enumerate(ids)}
    manifest = manifest.with_columns(pl.col("tile_id").replace_strict(order).alias("row"))
    train = manifest.filter(pl.col("role") == "train")
    ev = manifest.filter(pl.col("role") == "eval")
    x_train, y_train = feats[train["row"].to_numpy()], train["tile_label"].to_numpy()
    x_eval, y_eval = feats[ev["row"].to_numpy()], ev["tile_label"].to_numpy()

    scaler = StandardScaler().fit(x_train)
    clf = LogisticRegression(max_iter=3000, C=0.1, class_weight="balanced", random_state=SEED)
    clf.fit(scaler.transform(x_train), y_train)
    p_eval = clf.predict_proba(scaler.transform(x_eval))[:, 1]

    print(f"eval tiles: {len(y_eval)}  positive rate: {y_eval.mean():.4f}")
    print(f"tile AUC: {roc_auc_score(y_eval, p_eval):.4f} (chance 0.5)")
    print(f"tile avg precision: {average_precision_score(y_eval, p_eval):.4f} (chance {y_eval.mean():.4f})")
    print(f"tile balanced accuracy: {balanced_accuracy_score(y_eval, p_eval >= 0.5):.4f} (chance 0.5)")

    assignment = pl.read_parquet(TILE_ASSIGNMENT_PATH)
    scores = ev.select("tile_id").with_columns(score=pl.Series(p_eval))
    val_listings = assignment.filter(pl.col("split") == "val").join(scores, on="tile_id", how="inner")
    y_l = val_listings["label"].to_numpy()
    p_l = val_listings["score"].to_numpy()
    print(f"val listings on eval tiles: {len(y_l)}  positive rate: {y_l.mean():.4f}")
    print(f"listing AUC: {roc_auc_score(y_l, p_l):.4f} (chance 0.5)")


if __name__ == "__main__":
    main()
