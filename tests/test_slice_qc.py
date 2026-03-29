import numpy as np

from slice_qc import compute_slicemean, mean_correct


def test_compute_slicemean_shape_and_values() -> None:
    # Shape: x, y, z, t
    data = np.ones((2, 3, 4, 5), dtype=np.float32)
    out = compute_slicemean(data)

    assert out.shape == (5, 4)
    assert np.allclose(out, 1.0)


def test_mean_correct_centers_each_slice() -> None:
    # volumes x slices
    slicemean = np.array(
        [
            [1.0, 4.0],
            [2.0, 5.0],
            [3.0, 6.0],
        ]
    )
    corrected = mean_correct(slicemean)

    # corrected is slices x volumes and each slice should have zero temporal mean
    assert corrected.shape == (2, 3)
    assert np.allclose(corrected.mean(axis=1), 0.0)
