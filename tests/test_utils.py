from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

import utils


def test_is_real_file_false_for_missing(tmp_path: Path) -> None:
    assert utils.is_real_file(tmp_path / "missing.nii.gz") is False


def test_is_real_file_false_for_small_file(tmp_path: Path) -> None:
    file_path = tmp_path / "pointer.nii.gz"
    file_path.write_bytes(b"x" * 512)
    assert utils.is_real_file(file_path) is False


def test_is_real_file_true_for_large_file(tmp_path: Path) -> None:
    file_path = tmp_path / "bold.nii.gz"
    file_path.write_bytes(b"x" * (1024 * 1024 + 1))
    assert utils.is_real_file(file_path) is True


def test_find_bold_returns_path_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    subject = "sub-00001"
    session = "ses-06"
    bold_dir = tmp_path / subject / session / "func"
    bold_dir.mkdir(parents=True)

    bold_path = bold_dir / f"{subject}_{session}_task-rest_bold.nii.gz"
    bold_path.write_bytes(b"x" * (1024 * 1024 + 10))

    monkeypatch.setattr(utils, "DATASET_ROOT", tmp_path)
    found = utils.find_bold(subject, session)

    assert found == bold_path


def test_find_bold_raises_system_exit_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(utils, "DATASET_ROOT", tmp_path)
    with pytest.raises(SystemExit):
        utils.find_bold("sub-00002", "ses-06")


def test_load_bold_loads_4d_data(tmp_path: Path) -> None:
    data = np.random.default_rng(1).normal(size=(4, 5, 3, 10)).astype(np.float32)
    affine = np.eye(4)
    img_path = tmp_path / "sample_bold.nii.gz"
    nib.save(nib.Nifti1Image(data, affine), img_path)

    _, loaded, loaded_affine = utils.load_bold(img_path)

    assert loaded.shape == data.shape
    assert loaded.dtype == np.float32
    assert np.allclose(loaded_affine, affine)
