from pathlib import Path

import numpy as np
import pandas as pd

from compare_3t_7t_mriqc import load_metric_table, summarize


def test_load_metric_table_parses_subject_and_metric(tmp_path: Path) -> None:
    tsv = tmp_path / "ses-06_task-rest_bold.tsv"
    pd.DataFrame(
        {
            "bids_name": [
                "sub-00001_ses-06_task-rest_bold",
                "sub-00002_ses-06_task-rest_bold",
            ],
            "tsnr": [22.5, 25.0],
        }
    ).to_csv(tsv, sep="\t", index=False)

    out = load_metric_table(tsv, "tsnr")

    assert list(out.columns) == ["subject", "value"]
    assert out["subject"].tolist() == ["sub-00001", "sub-00002"]
    assert np.allclose(out["value"].to_numpy(), np.array([22.5, 25.0]))


def test_summarize_returns_expected_stats() -> None:
    arr = np.array([1.0, 2.0, 3.0, 4.0])
    stats = summarize(arr)

    assert stats["n"] == 4.0
    assert stats["mean"] == 2.5
    assert stats["median"] == 2.5
    assert stats["min"] == 1.0
    assert stats["max"] == 4.0
