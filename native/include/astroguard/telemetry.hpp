#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace astroguard {

struct TelemetrySample {
    std::int64_t timestamp_ms;
    std::string channel;
    double value;
};

struct ValidationResult {
    bool valid;
    std::string message;
};

ValidationResult validate_sample(const TelemetrySample& sample);

double calculate_mean(const std::vector<double>& values);

}  // namespace astroguard