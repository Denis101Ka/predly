// Native mirror of `python -m verify`, for scripting and for speed checks.
//
//   ./bin/odds --cap 493e6 --target 986e6 --sigma 0.35 --hours 5.5
//   ./bin/odds --cap 188e6 --floor 184e6 --sigma 0.42 --hours 0.57
//   ./bin/odds --cap 188e6 --sigma 0.42 --hours 1 --ladder
//   ./bin/odds --bench 5000000

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <string>

#include "odds.hpp"

namespace {

void usage() {
    std::printf(
        "usage: odds --cap C --sigma S --hours H [--target T | --floor F] [--ladder]\n"
        "       odds --bench N        price N markets and report throughput\n");
}

std::string human(double n) {
    char buf[64];
    if (std::fabs(n) >= 1e9) std::snprintf(buf, sizeof(buf), "$%.2fB", n / 1e9);
    else if (std::fabs(n) >= 1e6) std::snprintf(buf, sizeof(buf), "$%.2fM", n / 1e6);
    else if (std::fabs(n) >= 1e3) std::snprintf(buf, sizeof(buf), "$%.1fK", n / 1e3);
    else std::snprintf(buf, sizeof(buf), "$%.0f", n);
    return buf;
}

int bench(long n) {
    const auto t0 = std::chrono::steady_clock::now();
    double sink = 0.0;
    for (long i = 0; i < n; ++i) {
        const double cap = 100000.0 + static_cast<double>(i % 5000);
        const predly::Quote q = predly::quote(cap, cap * 1.4, 0.55, 1.0, predly::Kind::Touch);
        sink += q.p_yes;
    }
    const auto us = std::chrono::duration_cast<std::chrono::microseconds>(
                        std::chrono::steady_clock::now() - t0).count();
    const double per_sec = static_cast<double>(n) / (static_cast<double>(us) / 1e6);
    std::printf("priced %ld markets in %.1f ms, %.1f million per second (checksum %.3f)\n",
                n, static_cast<double>(us) / 1000.0, per_sec / 1e6, sink);
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    double cap = 0, target = 0, floor = 0, sigma = 0, hours = 0;
    bool ladder = false;
    long bench_n = 0;

    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        auto next = [&](double& dst) { if (i + 1 < argc) dst = std::strtod(argv[++i], nullptr); };
        if (a == "--cap") next(cap);
        else if (a == "--target") next(target);
        else if (a == "--floor") next(floor);
        else if (a == "--sigma") next(sigma);
        else if (a == "--hours") next(hours);
        else if (a == "--ladder") ladder = true;
        else if (a == "--bench" && i + 1 < argc) bench_n = std::strtol(argv[++i], nullptr, 10);
        else if (a == "-h" || a == "--help") { usage(); return 0; }
    }

    if (bench_n > 0) return bench(bench_n);

    if (!(cap > 0) || !(sigma > 0) || !(hours > 0)) {
        usage();
        return 2;
    }

    try {
        if (ladder) {
            std::printf("cap %s, sigma %.3f per hour, %.2fh left\n\n", human(cap).c_str(), sigma, hours);
            for (double k : {0.5, 1.0, 1.5, 2.0}) {
                const double level = predly::target_for(cap, sigma, hours, k);
                const predly::Quote q = predly::quote(cap, level, sigma, hours, predly::Kind::Touch);
                std::printf("  k %.1f  target %10s   d=%7.4f  p_yes=%.4f  YES %2dc / NO %2dc\n", k,
                            human(level).c_str(), q.d, q.p_yes, q.yes_cents, q.no_cents);
            }
            return 0;
        }

        const predly::Kind kind = floor > 0 ? predly::Kind::Floor : predly::Kind::Touch;
        const double level = floor > 0 ? floor : target;
        if (!(level > 0)) {
            usage();
            return 2;
        }
        const predly::Quote q = predly::quote(cap, level, sigma, hours, kind);
        std::printf("%s  d=%.4f  p_yes=%.4f  YES %dc / NO %dc\n", predly::kind_name(q.kind), q.d,
                    q.p_yes, q.yes_cents, q.no_cents);
        return 0;
    } catch (const std::exception& e) {
        std::printf("error: %s\n", e.what());
        return 2;
    }
}
