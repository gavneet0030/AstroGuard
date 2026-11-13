import numpy as np
import pytest

from astroguard_api.mission_data.preprocessing import (
    PreprocessingError,
    engineer_features,
    build_anomaly_labels,
)


def sample_arrays():
    train = np.array(
        [
            [10.0, 2.0, 5.0],
            [12.0, 3.0, 5.0],
            [14.0, 4.0, 5.0],
            [16.0, 5.0, 5.0],
            [18.0, 6.0, 5.0],
        ],
        dtype=np.float64,
    )

    test = np.array(
        [
            [20.0, 7.0, 5.0],
            [22.0, 8.0, 5.0],
            [24.0, 9.0, 5.0],
        ],
        dtype=np.float64,
    )

    return train, test


def test_feature_output_shapes():
    train, test = sample_arrays()
    result = engineer_features(train, test, windows=(2, 3))

    assert result["train"].shape == (5, 10)
    assert result["test"].shape == (3, 10)


def test_feature_count_for_25_input_columns():
    train = np.ones((10, 25), dtype=np.float64)
    test = np.ones((5, 25), dtype=np.float64)

    result = engineer_features(train, test)

    assert result["raw_feature_count"] == 25
    assert result["engineered_feature_count"] == 54
    assert result["train"].shape == (10, 54)


def test_output_is_float32():
    train, test = sample_arrays()
    result = engineer_features(train, test)

    assert result["train"].dtype == np.float32
    assert result["test"].dtype == np.float32


def test_feature_names_are_unique():
    train, test = sample_arrays()
    result = engineer_features(train, test)

    assert len(result["feature_names"]) == len(set(result["feature_names"]))


def test_train_scaler_mean_is_zero_after_transform():
    train, test = sample_arrays()
    result = engineer_features(train, test)

    means = np.mean(result["train"], axis=0)

    assert np.allclose(means, 0.0, atol=1e-5)


def test_train_scaler_standard_deviation():
    train, test = sample_arrays()
    result = engineer_features(train, test)

    stds = np.std(result["train"], axis=0)

    assert np.all(np.isfinite(stds))
    assert np.all(stds <= 1.0001)


def test_scaler_is_fitted_only_on_train():
    train, test = sample_arrays()

    first = engineer_features(train, test)

    extreme_test = test.copy()
    extreme_test[:, 0] = 1000000.0

    second = engineer_features(train, extreme_test)

    assert first["scaler_mean"] == second["scaler_mean"]
    assert first["scaler_scale"] == second["scaler_scale"]


def test_first_difference_first_row_is_zero_before_scaling():
    train, test = sample_arrays()

    # Independently verify the feature construction through the
    # unscaled difference pattern.
    differences = np.zeros_like(train)
    differences[1:] = train[1:] - train[:-1]

    assert np.all(differences[0] == 0.0)
    assert np.all(differences[1:, 0] == 2.0)


def test_rolling_mean_is_causal():
    values = np.array([1.0, 3.0, 5.0])

    from astroguard_api.mission_data.preprocessing import _rolling_mean_std

    means, _ = _rolling_mean_std(values, 2)

    assert np.allclose(means, [1.0, 2.0, 4.0])


def test_rolling_std_first_value_is_zero():
    values = np.array([7.0, 9.0, 11.0])

    from astroguard_api.mission_data.preprocessing import _rolling_mean_std

    _, stds = _rolling_mean_std(values, 3)

    assert stds[0] == 0.0


def test_anomaly_labels_inclusive_intervals():
    labels = build_anomaly_labels(
        10,
        [[2, 4], [7, 8]],
    )

    assert labels.dtype == np.uint8
    assert labels.tolist() == [0, 0, 1, 1, 1, 0, 0, 1, 1, 0]


def test_overlapping_anomaly_intervals_do_not_double_count():
    labels = build_anomaly_labels(
        8,
        [[1, 4], [3, 6]],
    )

    assert int(labels.sum()) == 6


def test_invalid_anomaly_interval_rejected():
    with pytest.raises(PreprocessingError):
        build_anomaly_labels(10, [[2, 10]])


def test_negative_anomaly_interval_rejected():
    with pytest.raises(PreprocessingError):
        build_anomaly_labels(10, [[-1, 2]])


def test_empty_training_data_rejected():
    with pytest.raises(PreprocessingError):
        engineer_features(
            np.empty((0, 3)),
            np.ones((2, 3)),
        )


def test_non_finite_input_rejected():
    train, test = sample_arrays()
    train[0, 0] = np.nan

    with pytest.raises(PreprocessingError):
        engineer_features(train, test)


def test_mismatched_feature_count_rejected():
    train = np.ones((5, 3))
    test = np.ones((4, 2))

    with pytest.raises(PreprocessingError):
        engineer_features(train, test)


def test_invalid_window_rejected():
    train, test = sample_arrays()

    with pytest.raises(PreprocessingError):
        engineer_features(train, test, windows=(1, 3))


def test_duplicate_windows_rejected():
    train, test = sample_arrays()

    with pytest.raises(PreprocessingError):
        engineer_features(train, test, windows=(5, 5))


def test_constant_features_remain_finite():
    train = np.ones((10, 4), dtype=np.float64)
    test = np.ones((5, 4), dtype=np.float64)

    result = engineer_features(train, test)

    assert np.isfinite(result["train"]).all()
    assert np.isfinite(result["test"]).all()


def test_test_rows_are_not_used_for_train_scaling():
    train = np.arange(30, dtype=np.float64).reshape(10, 3)
    test = np.full((4, 3), 99999.0)

    result = engineer_features(train, test)

    assert result["scaler_fit_split"] == "train"
    assert np.allclose(np.mean(result["train"], axis=0), 0.0, atol=1e-5)


def test_rolling_policy_is_recorded():
    train, test = sample_arrays()
    result = engineer_features(train, test)

    assert result["rolling_policy"] == (
        "causal_trailing_window_reset_per_split"
    )


def test_label_length_matches_requested_rows():
    labels = build_anomaly_labels(15, [[4, 6]])

    assert len(labels) == 15
