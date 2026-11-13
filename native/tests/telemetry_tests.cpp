#include "astroguard/telemetry.hpp"

#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

int failures = 0;
int assertions = 0;

void check(bool condition, const char* name) {
    ++assertions;

    if (condition) {
        std::cout << "[PASS] " << name << '\n';
    } else {
        std::cerr << "[FAIL] " << name << '\n';
        ++failures;
    }
}

bool approximately_equal(
    double actual,
    double expected,
    double tolerance = 1e-10
) {
    if (actual == expected) {
        return true;
    }

    if (!std::isfinite(actual) || !std::isfinite(expected)) {
        return false;
    }

    const double scale =
        std::max(std::abs(actual), std::abs(expected));

    if (scale == 0.0) {
        return true;
    }

    return std::abs(actual / scale - expected / scale) <= tolerance;
}

template <typename Function>
bool throws_invalid_argument(Function&& function) {
    try {
        function();
    } catch (const std::invalid_argument&) {
        return true;
    } catch (...) {
        return false;
    }

    return false;
}

}  // namespace

int main() {
    using namespace astroguard;

    const double infinity =
        std::numeric_limits<double>::infinity();

    const double maximum =
        std::numeric_limits<double>::max();

    const double lowest =
        std::numeric_limits<double>::lowest();

    const double quiet_nan =
        std::numeric_limits<double>::quiet_NaN();

    // =============================================================
    // SECTION A — PRESERVED ORIGINAL TESTS
    // =============================================================

    check(
        validate_sample({1000, "TEMP", 20.5}).valid,
        "Valid telemetry accepted"
    );

    check(
        !validate_sample({-1, "TEMP", 20.5}).valid,
        "Negative timestamp rejected"
    );

    check(
        !validate_sample({1000, "", 20.5}).valid,
        "Empty channel rejected"
    );

    check(
        !validate_sample({1000, "TEMP", quiet_nan}).valid,
        "NaN value rejected"
    );

    check(
        approximately_equal(
            calculate_mean({10.0, 20.0, 30.0}),
            20.0
        ),
        "Mean calculation correct"
    );

    check(
        throws_invalid_argument([] {
            calculate_mean({});
        }),
        "Empty mean input rejected"
    );

    check(
        throws_invalid_argument([infinity] {
            calculate_mean({1.0, infinity});
        }),
        "Infinite mean input rejected"
    );

    // =============================================================
    // SECTION B — TIMESTAMP BOUNDARIES
    // =============================================================

    check(
        validate_sample({0, "TEMP", 20.0}).valid,
        "Zero timestamp accepted"
    );

    check(
        validate_sample({
            std::numeric_limits<std::int64_t>::max(),
            "TEMP",
            20.0
        }).valid,
        "Maximum signed timestamp accepted"
    );

    check(
        !validate_sample({-1, "TEMP", 20.0}).valid,
        "Negative timestamp boundary rejected"
    );

    // =============================================================
    // SECTION C — CHANNEL VALIDATION
    // =============================================================

    check(
        !validate_sample({1000, " ", 20.0}).valid,
        "Single-space channel rejected"
    );

    check(
        !validate_sample({1000, "\t", 20.0}).valid,
        "Tab-only channel rejected"
    );

    check(
        !validate_sample({1000, "\n", 20.0}).valid,
        "Newline-only channel rejected"
    );

    check(
        validate_sample({
            1000,
            "BATTERY_VOLTAGE",
            28.4
        }).valid,
        "Underscore channel identifier accepted"
    );

    check(
        validate_sample({
            1000,
            "TEMP SENSOR",
            20.0
        }).valid,
        "Channel containing internal space accepted"
    );

    // =============================================================
    // SECTION D — TELEMETRY FLOATING POINT BOUNDARIES
    // =============================================================

    check(
        !validate_sample({
            1000,
            "TEMP",
            -infinity
        }).valid,
        "Negative infinity telemetry rejected"
    );

    check(
        validate_sample({
            1000,
            "TEMP",
            -0.0
        }).valid,
        "Negative zero telemetry accepted"
    );

    check(
        validate_sample({
            1000,
            "TEMP",
            maximum
        }).valid,
        "Maximum finite double telemetry accepted"
    );

    check(
        validate_sample({
            1000,
            "TEMP",
            lowest
        }).valid,
        "Minimum finite double telemetry accepted"
    );

    check(
        !validate_sample({
            1000,
            "TEMP",
            infinity
        }).valid,
        "Positive infinity telemetry rejected"
    );

    check(
        !validate_sample({
            1000,
            "TEMP",
            quiet_nan
        }).valid,
        "NaN telemetry rejected"
    );

    // =============================================================
    // SECTION E — BASIC MEAN CASES
    // =============================================================

    check(
        approximately_equal(
            calculate_mean({-10.0, -20.0, -30.0}),
            -20.0
        ),
        "Mean of negative values correct"
    );

    check(
        approximately_equal(
            calculate_mean({-10.0, 20.0, 30.0}),
            40.0 / 3.0
        ),
        "Mean of mixed-sign values correct"
    );

    check(
        approximately_equal(
            calculate_mean({42.5}),
            42.5
        ),
        "Single-element mean correct"
    );

    check(
        approximately_equal(
            calculate_mean({5.0, 5.0, 5.0, 5.0}),
            5.0
        ),
        "Repeated identical values mean correct"
    );

    check(
        approximately_equal(
            calculate_mean({0.0, 0.0, 0.0}),
            0.0
        ),
        "Zero-valued mean correct"
    );

    check(
        approximately_equal(
            calculate_mean({-0.0, 0.0}),
            0.0
        ),
        "Mixed signed-zero mean correct"
    );

    // =============================================================
    // SECTION F — LARGE FINITE INPUTS
    // =============================================================

    check(
        approximately_equal(
            calculate_mean({maximum, maximum}),
            maximum
        ),
        "Maximum finite values do not overflow mean"
    );

    check(
        approximately_equal(
            calculate_mean({maximum, -maximum}),
            0.0
        ),
        "Opposite maximum values cancel correctly"
    );

    check(
        approximately_equal(
            calculate_mean({maximum, maximum, maximum}),
            maximum
        ),
        "Three maximum finite values produce finite mean"
    );

    check(
        approximately_equal(
            calculate_mean({maximum, 0.0}),
            maximum / 2.0
        ),
        "Maximum finite and zero mean correct"
    );

    check(
        approximately_equal(
            calculate_mean({lowest, lowest}),
            lowest
        ),
        "Minimum finite values do not overflow mean"
    );

    check(
        approximately_equal(
            calculate_mean({maximum, lowest}),
            0.0
        ),
        "Positive and negative extreme values cancel"
    );

    // =============================================================
    // SECTION G — NON-FINITE MEAN INPUTS
    // =============================================================

    check(
        throws_invalid_argument([quiet_nan] {
            calculate_mean({1.0, quiet_nan});
        }),
        "NaN mean input rejected"
    );

    check(
        throws_invalid_argument([infinity] {
            calculate_mean({1.0, infinity});
        }),
        "Positive infinity mean input rejected"
    );

    check(
        throws_invalid_argument([infinity] {
            calculate_mean({1.0, -infinity});
        }),
        "Negative infinity mean input rejected"
    );

    // =============================================================
    // SECTION H — SMALL MAGNITUDE VALUES
    // =============================================================

    const double denormal =
        std::numeric_limits<double>::denorm_min();

    check(
        approximately_equal(
            calculate_mean({denormal, denormal}),
            denormal
        ),
        "Denormal mean remains valid"
    );

    const double minimum_positive =
        std::numeric_limits<double>::min();

    check(
        approximately_equal(
            calculate_mean({
                minimum_positive,
                minimum_positive
            }),
            minimum_positive
        ),
        "Minimum positive normal mean correct"
    );

    // =============================================================
    // SECTION I — DETERMINISM
    // =============================================================

    const std::vector<double> deterministic_values{
        28.1,
        28.4,
        28.3,
        28.2
    };

    const double first_mean =
        calculate_mean(deterministic_values);

    const double second_mean =
        calculate_mean(deterministic_values);

    check(
        first_mean == second_mean,
        "Repeated mean calculation is deterministic"
    );

    check(
        approximately_equal(first_mean, 28.25),
        "Telemetry mean matches expected value"
    );

    // =============================================================
    // SECTION J — EXCEPTION CONTRACT
    // =============================================================

    check(
        throws_invalid_argument([] {
            calculate_mean({});
        }),
        "Empty input consistently throws invalid_argument"
    );

    check(
        throws_invalid_argument([] {
            calculate_mean({
                std::numeric_limits<double>::quiet_NaN()
            });
        }),
        "Single NaN input throws invalid_argument"
    );

    // =============================================================
    // FINAL REPORT
    // =============================================================

    std::cout << '\n';
    std::cout << "========================================\n";
    std::cout << "ASTROGUARD NATIVE TEST SUMMARY\n";
    std::cout << "========================================\n";

    std::cout << "Assertions executed: "
              << assertions << '\n';

    std::cout << "C++ test failures: "
              << failures << '\n';

    std::cout << "========================================\n";

    return failures == 0 ? 0 : 1;
}