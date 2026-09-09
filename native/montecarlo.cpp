// Does the closed form actually price a first passage correctly?
//
// The board quotes a touch market with the reflection principle, a formula on paper. This
// binary checks the paper against brute force: simulate a driftless geometric Brownian
// motion at a fine step, count how often the running maximum reaches the target inside the
// window, and compare that frequency with the analytic price.
//
// If the model is wrong, this is where it shows up, and it is why the native engine exists:
// a hundred million steps in Python would take an afternoon.
//
//   ./bin/montecarlo [paths_per_cell] [--seed N] [--tolerance 0.01]

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <random>
#include <string>
#include <vector>

#include "odds.hpp"

namespace {

struct Cell {
    double cap;
    double level;
    double sigma;
    double hours;
    predly::Kind kind;
    const char* label;
};

// One path of a driftless log-normal walk, sampled at `steps` points, reporting whether the
// running extreme crossed the level.
bool crossed(std::mt19937_64& rng, double cap, double level, double sigma, double hours,
             predly::Kind kind, int steps) {
    std::normal_distribution<double> z(0.0, 1.0);
    const double dt = hours / static_cast<double>(steps);
    const double vol = sigma * std::sqrt(dt);
    // Driftless in the arithmetic sense the pricing uses: the log process carries the
    // Ito correction so that the level itself has no systematic direction.
    const double drift = -0.5 * sigma * sigma * dt;
    double log_price = std::log(cap);
    const double log_level = std::log(level);
    for (int i = 0; i < steps; ++i) {
        log_price += drift + vol * z(rng);
        if (kind == predly::Kind::Touch) {
            if (log_price >= log_level) return true;
        } else {
            if (log_price <= log_level) return true;   // floor breached
        }
    }
    return false;
}

}  // namespace

int main(int argc, char** argv) {
    long paths = 200000;
    unsigned long long seed = 20260909ULL;
    double tolerance = 0.012;
    int steps = 2000;

    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--seed" && i + 1 < argc) seed = std::strtoull(argv[++i], nullptr, 10);
        else if (a == "--tolerance" && i + 1 < argc) tolerance = std::strtod(argv[++i], nullptr);
        else if (a == "--steps" && i + 1 < argc) steps = std::atoi(argv[++i]);
        else if (a.rfind("--", 0) != 0) paths = std::strtol(a.c_str(), nullptr, 10);
    }

    const Cell cells[] = {
        {100000, 150000, 0.60, 1.0, predly::Kind::Touch, "reach 1.5x, 1h, sigma 0.6"},
        {100000, 130000, 0.45, 2.0, predly::Kind::Touch, "reach 1.3x, 2h, sigma 0.45"},
        {100000, 200000, 0.90, 1.0, predly::Kind::Touch, "reach 2.0x, 1h, sigma 0.9"},
        {493000000, 986000000, 0.35, 5.5, predly::Kind::Touch, "the README example"},
        {100000, 85000, 0.50, 1.0, predly::Kind::Floor, "hold 0.85x, 1h, sigma 0.5"},
        {100000, 70000, 0.80, 3.0, predly::Kind::Floor, "hold 0.70x, 3h, sigma 0.8"},
        {250000, 240000, 0.25, 0.5, predly::Kind::Floor, "hold 0.96x, 30m, sigma 0.25"},
    };

    std::printf("first passage: closed form against %ld simulated paths per cell, %d steps each\n\n",
                paths, steps);
    std::printf("  %-32s %8s %8s %8s\n", "cell", "model", "sim", "gap");
    std::printf("  %-32s %8s %8s %8s\n", "----", "-----", "---", "---");

    const auto t0 = std::chrono::steady_clock::now();
    int worst_cell = -1;
    double worst_gap = 0.0;
    int idx = 0;

    for (const Cell& c : cells) {
        std::mt19937_64 rng(seed + static_cast<unsigned long long>(idx) * 7919ULL);
        long hits = 0;
        for (long p = 0; p < paths; ++p) {
            if (crossed(rng, c.cap, c.level, c.sigma, c.hours, c.kind, steps)) ++hits;
        }
        const double sim_cross = static_cast<double>(hits) / static_cast<double>(paths);
        // A touch market pays when the level is crossed; a floor market pays when it is not.
        const double sim_yes = c.kind == predly::Kind::Touch ? sim_cross : 1.0 - sim_cross;
        const predly::Quote q = predly::quote(c.cap, c.level, c.sigma, c.hours, c.kind);

        // Compare before the clamp bites, otherwise the clamp is what gets measured.
        const double raw = c.kind == predly::Kind::Touch
                               ? 2.0 * (1.0 - predly::phi(q.d))
                               : 2.0 * predly::phi(q.d) - 1.0;
        const double gap = std::fabs(raw - sim_yes);
        if (gap > worst_gap) {
            worst_gap = gap;
            worst_cell = idx;
        }
        std::printf("  %-32s %7.4f %8.4f %8.4f%s\n", c.label, raw, sim_yes, gap,
                    gap > tolerance ? "   <-- over tolerance" : "");
        ++idx;
    }

    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::steady_clock::now() - t0).count();
    const double total_steps = static_cast<double>(paths) * steps * (sizeof(cells) / sizeof(cells[0]));
    std::printf("\n  %.0f million steps in %lld ms\n", total_steps / 1e6, static_cast<long long>(ms));

    if (worst_gap > tolerance) {
        std::printf("  worst gap %.4f on cell %d, tolerance %.4f: the closed form and the "
                    "simulation disagree\n", worst_gap, worst_cell, tolerance);
        return 1;
    }
    std::printf("  worst gap %.4f, inside the %.4f tolerance: the formula holds\n", worst_gap, tolerance);
    return 0;
}
