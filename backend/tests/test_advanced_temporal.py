from __future__ import annotations

import numpy as np
import pytest

from astroguard_api.mission_data.advanced_temporal import (
    FEATURE_NAMES,
    FEATURE_COUNT,
    EXPECTED_TOTAL_FEATURES,
    AdvancedFeatureError,
    build_temporal_features,
    fit_train_scaler,
    apply_train_scaler,
)


def test_feature_count_is_fifteen():
    assert FEATURE_COUNT == 15
    assert len(FEATURE_NAMES) == 15


def test_expected_total_feature_count():
    assert EXPECTED_TOTAL_FEATURES == 69


def test_output_shape():
    signal = np.arange(100, dtype=np.float64)
    result = build_temporal_features(signal)

    assert result.shape == (100, 15)


def test_output_dtype():
    result = build_temporal_features(np.arange(50))
    assert result.dtype == np.float64


def test_output_is_finite():
    result = build_temporal_features(np.linspace(-5, 5, 100))
    assert np.isfinite(result).all()


def test_first_difference():
    signal = np.array([2.0, 4.0, 7.0])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 0],
        [0.0, 2.0, 3.0],
    )


def test_absolute_difference():
    signal = np.array([5.0, 3.0, 8.0])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 1],
        [0.0, 2.0, 5.0],
    )


def test_percentage_change():
    signal = np.array([10.0, 20.0, 10.0])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 2],
        [0.0, 1.0, -0.5],
    )


def test_rolling_mean_window_five():
    signal = np.array([1., 2., 3., 4., 5., 6.])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 3],
        [1., 1.5, 2., 2.5, 3., 4.],
    )


def test_rolling_std_window_five():
    signal = np.array([1., 2., 3.])
    result = build_temporal_features(signal)

    assert result[0, 4] == pytest.approx(0.0)
    assert result[1, 4] == pytest.approx(0.5)
    assert result[2, 4] == pytest.approx(np.std([1., 2., 3.]))


def test_rolling_minimum():
    signal = np.array([4., 2., 7., 1.])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 5],
        [4., 2., 2., 1.],
    )


def test_rolling_maximum():
    signal = np.array([4., 2., 7., 1.])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 6],
        [4., 4., 7., 7.],
    )


def test_rolling_median():
    signal = np.array([1., 3., 2., 8.])
    result = build_temporal_features(signal)

    np.testing.assert_allclose(
        result[:, 7],
        [1., 2., 2., 2.5],
    )


def test_rolling_mad():
    signal = np.array([1., 3., 2.])
    result = build_temporal_features(signal)

    assert result[2, 8] == pytest.approx(1.0)


def test_rolling_window_thirty():
    signal = np.arange(1., 41.)
    result = build_temporal_features(signal)

    assert result[29, 9] == pytest.approx(15.5)
    assert result[30, 9] == pytest.approx(16.5)


def test_ewma_initialization():
    signal = np.array([10., 20., 30.])
    result = build_temporal_features(signal)

    assert result[0, 13] == pytest.approx(10.0)
    assert result[1, 13] == pytest.approx(11.0)
    assert result[2, 13] == pytest.approx(12.9)


def test_ewma_alpha_point_three():
    signal = np.array([10., 20., 30.])
    result = build_temporal_features(signal)

    assert result[1, 14] == pytest.approx(13.0)
    assert result[2, 14] == pytest.approx(18.1)


def test_constant_signal_is_finite():
    result = build_temporal_features(np.ones(40))
    assert np.isfinite(result).all()


def test_zero_previous_value_percentage_change_is_finite():
    result = build_temporal_features(
        np.array([0.0, 1.0, -1.0])
    )

    assert np.isfinite(result[:, 2]).all()


def test_future_sample_does_not_change_past_features():
    first = np.array([1., 2., 3., 4., 5.])
    second = np.array([1., 2., 3., 4., 5., 10000.])

    a = build_temporal_features(first)
    b = build_temporal_features(second)

    np.testing.assert_allclose(a, b[:5])


def test_non_finite_signal_rejected():
    with pytest.raises(AdvancedFeatureError):
        build_temporal_features(
            np.array([1.0, np.nan, 2.0])
        )


def test_two_dimensional_signal_rejected():
    with pytest.raises(AdvancedFeatureError):
        build_temporal_features(
            np.ones((10, 2))
        )


def test_empty_signal_rejected():
    with pytest.raises(AdvancedFeatureError):
        build_temporal_features(np.array([]))


def test_string_signal_rejected():
    with pytest.raises(AdvancedFeatureError):
        build_temporal_features(
            np.array(["a", "b"])
        )


def test_scaler_fit_uses_training_matrix():
    train = build_temporal_features(
        np.linspace(1, 100, 100)
    )

    mean, scale = fit_train_scaler(train)

    np.testing.assert_allclose(
        mean,
        train.mean(axis=0),
    )

    np.testing.assert_allclose(
        scale,
        np.where(train.std(axis=0) < 1e-8, 1.0, train.std(axis=0)),
    )


def test_scaler_output_is_float32():
    train = build_temporal_features(np.arange(50.))
    mean, scale = fit_train_scaler(train)

    output = apply_train_scaler(train, mean, scale)

    assert output.dtype == np.float32


def test_scaler_training_mean_is_zero():
    train = build_temporal_features(np.arange(50.))
    mean, scale = fit_train_scaler(train)

    output = apply_train_scaler(train, mean, scale)

    np.testing.assert_allclose(
        output.mean(axis=0),
        np.zeros(FEATURE_COUNT),
        atol=1e-5,
    )


def test_constant_column_scale_fallback():
    train = np.ones((10, FEATURE_COUNT))
    mean, scale = fit_train_scaler(train)

    assert np.all(scale == 1.0)


def test_invalid_scaler_shape_rejected():
    with pytest.raises(AdvancedFeatureError):
        fit_train_scaler(np.ones((10, 3)))


def test_invalid_scaler_application_rejected():
    with pytest.raises(AdvancedFeatureError):
        apply_train_scaler(
            np.ones((10, FEATURE_COUNT)),
            np.ones(3),
            np.ones(3),
        )


def test_test_outlier_does_not_change_train_scaler():
    train = build_temporal_features(np.arange(1., 101.))
    mean_before, scale_before = fit_train_scaler(train)

    test = build_temporal_features(
        np.array([1., 2., 3., 1000000.])
    )

    _ = apply_train_scaler(test, mean_before, scale_before)

    mean_after, scale_after = fit_train_scaler(train)

    np.testing.assert_array_equal(mean_before, mean_after)
    np.testing.assert_array_equal(scale_before, scale_after)


def test_split_start_resets_rolling_history():
    first_split = build_temporal_features(
        np.array([100., 100., 100.])
    )

    second_split = build_temporal_features(
        np.array([1., 1., 1.])
    )

    assert second_split[0, 3] == pytest.approx(1.0)
    assert first_split[0, 3] == pytest.approx(100.0)


def test_feature_names_are_unique():
    assert len(set(FEATURE_NAMES)) == FEATURE_COUNT


def test_ewma_feature_names_present():
    assert "target_ewma_alpha_01" in FEATURE_NAMES
    assert "target_ewma_alpha_03" in FEATURE_NAMES


def test_window_feature_names_present():
    assert "target_rolling_mean_w5" in FEATURE_NAMES
    assert "target_rolling_mean_w30" in FEATURE_NAMES