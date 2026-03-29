import numpy as np

from iqm import compute_cov, compute_dvars, compute_gcor, compute_tsnr, make_brain_mask


def synthetic_bold(seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # Positive-valued synthetic signal with moderate temporal variance.
    return rng.normal(loc=100.0, scale=10.0, size=(6, 6, 4, 80)).astype(np.float32)


def test_make_brain_mask_returns_expected_shape() -> None:
    data = synthetic_bold()
    mask = make_brain_mask(data)

    assert mask.shape == data.shape[:3]
    assert mask.dtype == np.bool_
    assert mask.sum() > 0


def test_tsnr_and_cov_are_consistent() -> None:
    data = synthetic_bold()
    mask = make_brain_mask(data)

    tsnr_map, tsnr_median = compute_tsnr(data, mask)
    cov_map, cov_median = compute_cov(data, mask)

    assert tsnr_map.shape == data.shape[:3]
    assert cov_map.shape == data.shape[:3]
    assert tsnr_median > 0
    assert cov_median > 0

    # CoV (%) is approximately 100 / tSNR for strictly positive signals.
    assert np.isclose(cov_median, 100.0 / tsnr_median, rtol=0.25)


def test_dvars_shape_and_values() -> None:
    data = synthetic_bold()
    mask = make_brain_mask(data)

    dvars, dvars_median, n_spikes = compute_dvars(data, mask)

    assert dvars.shape == (data.shape[-1],)
    assert np.isnan(dvars[0])
    assert np.nanmin(dvars[1:]) >= 0
    assert dvars_median > 0
    assert 0 <= n_spikes <= (data.shape[-1] - 1)


def test_gcor_in_reasonable_bounds() -> None:
    data = synthetic_bold()
    mask = make_brain_mask(data)

    gcor = compute_gcor(data, mask)

    assert 0.0 <= gcor <= 1.1
