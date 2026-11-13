#include "astroguard/telemetry.hpp"

#include <iostream>
#include <vector>

int main() {
    using astroguard::TelemetrySample;
    using astroguard::calculate_mean;
    using astroguard::validate_sample;

    const TelemetrySample sample{
        1730000000000LL,
        "BATTERY_VOLTAGE",
        28.4
    };

    const auto result = validate_sample(sample);

    if (!result.valid) {
        std::cerr << "Validation failed: " << result.message << '\n';
        return 1;
    }

    const std::vector<double> readings{28.1, 28.4, 28.3, 28.2};

    std::cout << "AstroGuard C++20 Native Engine\n";
    std::cout << "Sample status: " << result.message << '\n';
    std::cout << "Channel: " << sample.channel << '\n';
    std::cout << "Mean voltage: " << calculate_mean(readings) << '\n';

    return 0;
}