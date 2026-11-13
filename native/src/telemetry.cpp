#include "astroguard/telemetry.hpp"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <numeric>
#include <stdexcept>

namespace astroguard {

namespace {

bool is_blank_channel(const std::string& channel) {
    if (channel.empty()) {
        return true;
    }

    for (const unsigned char character : channel) {
        if (std::isspace(character) == 0) {
            return false;
        }
    }

    return true;
}

}  // namespace

ValidationResult validate_sample(const TelemetrySample& sample) {
    if (sample.timestamp_ms < 0) {
        return {false, "Timestamp cannot be negative"};
    }

    if (is_blank_channel(sample.channel)) {
        return {false, "Channel cannot be empty or whitespace"};
    }

    if (!std::isfinite(sample.value)) {
        return {false, "Telemetry value must be finite"};
    }

    return {true, "Sample valid"};
}

double calculate_mean(const std::vector<double>& values) {
    if (values.empty()) {
        throw std::invalid_argument(
            "Cannot calculate mean of empty data"
        );
    }

    double scale = 0.0;

    for (const double value : values) {
        if (!std::isfinite(value)) {
            throw std::invalid_argument(
                "Input contains non-finite value"
            );
        }

        scale = std::max(scale, std::abs(value));
    }

    if (scale == 0.0) {
        return 0.0;
    }

    // Normalize values before accumulation. Each normalized value
    // is in [-1, 1], preventing intermediate overflow from large
    // finite input values.
    //
    // Neumaier compensated summation reduces accumulated rounding
    // error, particularly when magnitudes differ substantially.

    double sum = 0.0;
    double compensation = 0.0;

    for (const double value : values) {
        const double normalized = value / scale;
        const double next_sum = sum + normalized;

        if (std::abs(sum) >= std::abs(normalized)) {
            compensation += (sum - next_sum) + normalized;
        } else {
            compensation += (normalized - next_sum) + sum;
        }

        sum = next_sum;
    }

    const double normalized_mean =
        (sum + compensation) /
        static_cast<double>(values.size());

    const double mean = normalized_mean * scale;

    if (!std::isfinite(mean)) {
        throw std::invalid_argument(
            "Calculated mean is not finite"
        );
    }

    return mean;
}

}  // namespace astroguard