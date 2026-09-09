// Predly pricing engine, native implementation.
//
// Third copy of the same maths that lives in verify/odds.py and verify/odds.ts. It exists
// for the work the scripting engines are too slow for: validating the closed form against
// millions of simulated paths, and sweeping a parameter grid across every historical price
// path in data/. CI replays the shared vectors through all three engines and diffs the
// cents, so a drift in any one of them fails the build.
//
// C++17, standard library only.

#ifndef PREDLY_ODDS_HPP
#define PREDLY_ODDS_HPP

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace predly {

constexpr double P_MIN = 0.03;
constexpr double P_MAX = 0.97;
constexpr double SIGMA_MIN = 0.05;
constexpr double SIGMA_MAX = 3.0;
constexpr double TAU_MIN_HOURS = 1.0 / 60.0;
constexpr int BARS_PER_HOUR = 12;
constexpr int VOL_WINDOW_HOURS = 6;

enum class Kind { Touch, Floor };

inline Kind kind_from(const std::string& s) {
    if (s == "touch") return Kind::Touch;
    if (s == "floor") return Kind::Floor;
    throw std::invalid_argument("unknown market kind: " + s);
}

inline const char* kind_name(Kind k) { return k == Kind::Touch ? "touch" : "floor"; }

inline double clampd(double v, double lo, double hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Standard normal CDF, Abramowitz and Stegun 26.2.17.
// Deliberately not std::erf: the three engines must agree to the cent on every platform,
// and sharing one approximation is the cheapest way to guarantee that.
inline double phi(double x) {
    const double p = 0.2316419;
    const double b[5] = {0.31938153, -0.356563782, 1.781477937, -1.821255978, 1.330274429};
    const double sign = x >= 0.0 ? 1.0 : -1.0;
    const double ax = std::fabs(x);
    const double t = 1.0 / (1.0 + p * ax);
    double poly = 0.0;
    double tp = t;
    for (int i = 0; i < 5; ++i) {
        poly += b[i] * tp;
        tp *= t;
    }
    const double cdf = 1.0 - (1.0 / std::sqrt(2.0 * M_PI)) * std::exp(-ax * ax / 2.0) * poly;
    return sign > 0.0 ? cdf : 1.0 - cdf;
}

struct Quote {
    Kind kind = Kind::Touch;
    double d = 0.0;
    double p_yes = 0.0;
    int yes_cents = 0;
    int no_cents = 0;
};

// Hourly realized volatility from close to close log returns of five minute candles.
inline double realized_sigma(const std::vector<double>& closes, int bars_per_hour = BARS_PER_HOUR) {
    if (closes.size() < 3) return SIGMA_MIN;
    std::vector<double> rets;
    rets.reserve(closes.size());
    for (std::size_t i = 1; i < closes.size(); ++i) {
        const double a = closes[i - 1], b = closes[i];
        if (a > 0.0 && b > 0.0) rets.push_back(std::log(b / a));
    }
    if (rets.size() < 2) return SIGMA_MIN;
    double mean = 0.0;
    for (double r : rets) mean += r;
    mean /= static_cast<double>(rets.size());
    double var = 0.0;
    for (double r : rets) var += (r - mean) * (r - mean);
    var /= static_cast<double>(rets.size() - 1);
    return clampd(std::sqrt(var) * std::sqrt(static_cast<double>(bars_per_hour)), SIGMA_MIN, SIGMA_MAX);
}

// Realized volatility over the trailing window only, the way a market open measures it.
inline double sigma_from_candles(const std::vector<double>& closes, int window_hours = VOL_WINDOW_HOURS) {
    const std::size_t need = static_cast<std::size_t>(window_hours * BARS_PER_HOUR + 1);
    if (closes.size() <= need) return realized_sigma(closes);
    return realized_sigma(std::vector<double>(closes.end() - static_cast<long>(need), closes.end()));
}

// touch: will the cap reach `level` before the deadline (reach, double templates).
// floor: will the cap stay above `level` until the deadline (hold template).
inline Quote quote(double cap, double level, double sigma, double hours, Kind kind = Kind::Touch) {
    if (!(cap > 0.0) || !(level > 0.0)) throw std::invalid_argument("cap and level must be positive");
    if (!(sigma > 0.0)) throw std::invalid_argument("sigma must be positive");

    const double tau = std::max(hours, TAU_MIN_HOURS);
    const double denom = clampd(sigma, SIGMA_MIN, SIGMA_MAX) * std::sqrt(tau);

    Quote q;
    q.kind = kind;
    if (kind == Kind::Touch) {
        q.d = std::log(level / cap) / denom;
        q.p_yes = 2.0 * (1.0 - phi(q.d));   // reflection principle on the running maximum
    } else {
        q.d = std::log(cap / level) / denom;
        q.p_yes = 2.0 * phi(q.d) - 1.0;     // complement: never touching the floor
    }
    q.p_yes = clampd(q.p_yes, P_MIN, P_MAX);
    q.yes_cents = static_cast<int>(clampd(static_cast<double>(std::llround(q.p_yes * 100.0)), 1.0, 99.0));
    q.no_cents = 100 - q.yes_cents;
    return q;
}

// Where a volatility scaled goalpost sits: k sigma root T away from the cap.
inline double target_for(double cap, double sigma, double hours, double k = 1.0) {
    return cap * std::exp(k * clampd(sigma, SIGMA_MIN, SIGMA_MAX) * std::sqrt(std::max(hours, TAU_MIN_HOURS)));
}

}  // namespace predly

#endif  // PREDLY_ODDS_HPP
