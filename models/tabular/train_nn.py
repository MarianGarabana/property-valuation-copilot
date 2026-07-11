import sys
from pathlib import Path

import joblib
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import mean_absolute_error, mean_squared_error

torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))

TABULAR_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TABULAR_DIR))

import prep  # noqa: E402
from nn_model import TabularMLP  # noqa: E402

NN_MODEL_PATH = TABULAR_DIR / "production_nn.pt"
NN_RESULT_PATH = TABULAR_DIR / "_nn_result.joblib"
RANDOM_SEED = 42


def metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mape = float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100.0)
    return {"mae": mae, "rmse": rmse, "mape": mape}


def main():
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    frames = prep.load_split_frames()
    cat_levels = prep.categorical_levels(frames["train"])
    x_train_df, y_train = prep.to_pandas_xy(frames["train"], cat_levels)
    x_val_df, y_val = prep.to_pandas_xy(frames["val"], cat_levels)
    x_test_df, y_test = prep.to_pandas_xy(frames["test"], cat_levels)

    preproc = prep.fit_nn_preprocessor(x_train_df)
    x_train = prep.transform_nn(x_train_df, preproc)
    x_val = prep.transform_nn(x_val_df, preproc)
    x_test = prep.transform_nn(x_test_df, preproc)

    y_train_log = np.log(y_train)
    target_mean = float(y_train_log.mean())
    target_std = float(y_train_log.std())
    z_train = (y_train_log - target_mean) / target_std

    model = TabularMLP(prep.nn_input_dim(preproc))
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-5)
    loss_fn = nn.SmoothL1Loss()

    xt = torch.tensor(x_train, dtype=torch.float32)
    zt = torch.tensor(z_train, dtype=torch.float32)
    xv = torch.tensor(x_val, dtype=torch.float32)
    xtest = torch.tensor(x_test, dtype=torch.float32)
    dataset = torch.utils.data.TensorDataset(xt, zt)
    loader = torch.utils.data.DataLoader(dataset, batch_size=512, shuffle=True)

    hparams = {
        "hidden_layers": "256-128-64",
        "dropout": 0.15,
        "batch_size": 512,
        "lr": 1e-3,
        "weight_decay": 1e-5,
        "optimizer": "adam",
        "loss": "smooth_l1_on_standardized_log_price",
        "max_epochs": 200,
        "early_stopping_patience": 15,
    }

    def predict_euros(x_tensor):
        model.eval()
        with torch.no_grad():
            z = model(x_tensor).cpu().numpy()
        return np.exp(z * target_std + target_mean)

    best_val_mae = np.inf
    best_state = None
    patience = hparams["early_stopping_patience"]
    wait = 0
    best_epoch = 0
    for epoch in range(1, hparams["max_epochs"] + 1):
        model.train()
        for xb, zb in loader:
            optimizer.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, zb)
            loss.backward()
            optimizer.step()
        val_pred = predict_euros(xv)
        val_mae = mean_absolute_error(y_val, val_pred)
        if val_mae < best_val_mae - 1.0:
            best_val_mae = val_mae
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            best_epoch = epoch
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    model.load_state_dict(best_state)
    val_pred = predict_euros(xv)
    test_pred = predict_euros(xtest)
    torch.save(model.state_dict(), NN_MODEL_PATH)

    result = {
        "params": hparams,
        "best_epoch": best_epoch,
        "val_metrics": metrics(y_val, val_pred),
        "test_metrics": metrics(y_test, test_pred),
        "val_residuals": np.asarray(y_val - val_pred),
        "preproc": preproc,
        "target_mean": target_mean,
        "target_std": target_std,
        "input_dim": prep.nn_input_dim(preproc),
        "model_path": NN_MODEL_PATH.name,
    }
    joblib.dump(result, NN_RESULT_PATH)

    print("NN best epoch:", best_epoch)
    print("NN test metrics:", result["test_metrics"])


if __name__ == "__main__":
    main()
