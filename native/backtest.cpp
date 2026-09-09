// Sweep the market templates across every price path in a published snapshot.
//
// For each token the snapshot carries the executed price of its recent fills. This binary
// replays those paths: it opens a market at every point in the series, prices it with the
// same engine the board uses, then walks forward to see whether the market would have
// resolved YES. Grouping by the price the model quoted produces a calibration table, the
// only honest way to answer "when Predly says 30c, how often does it happen".
//
// The grid is deliberately brute force, which is exactly the job a native binary is for.
//
//   ./bin/backtest [data/snapshot-latest.json] [--horizon 24] [--csv out.csv]

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <map>
#include <string>
#include <vector>

#include "json.hpp"
#include "odds.hpp"

namespace {

struct Token {
    std::string symbol;
    std::vector<double> caps;
};

struct Bucket {
    long markets = 0;
    long resolved_yes = 0;
    double priced_sum = 0.0;
};

// One fill is one step. The snapshot stores up to 160 fills per token, which is the entire
// series the board draws, so the horizon is measured in fills rather than in minutes.
constexpr int DEFAULT_HORIZON = 24;

std::vector<Token> load_tokens(const std::string& path, double& eth_usd) {
    const auto doc = predly::json::load(path);
    eth_usd = doc.num_or("eth_usd", 0.0);
    std::vector<Token> out;
    const auto* toks = doc.find("tokens");
    if (!toks || !toks->is_array()) return out;

    for (const auto& t : toks->arr()) {
        const auto* path_v = t.find("path");
        if (!path_v || !path_v->is_array()) continue;
        std::vector<double> raw;
        for (const auto& p : path_v->arr()) raw.push_back(p.num());
        if (raw.size() < 40) continue;

        // The same median trim the readers apply: one misdecoded fill would otherwise
        // dominate every statistic computed here.
        std::vector<double> sorted = raw;
        std::sort(sorted.begin(), sorted.end());
        const double med = sorted[sorted.size() / 2];
        if (!(med > 0.0)) continue;

        Token tok;
        tok.symbol = t.str_or("symbol", "?");
        const double fx = t.str_or("unit", "ETH") == "ETH" ? eth_usd : 1.0;
        for (double p : raw) {
            if (p > med / 6.0 && p < med * 6.0) tok.caps.push_back(p * 1e9 * fx);
        }
        if (tok.caps.size() >= 40) out.push_back(std::move(tok));
    }
    return out;
}

}  // namespace

int main(int argc, char** argv) {
    std::string path = "data/snapshot-latest.json";
    std::string csv;
    int horizon = DEFAULT_HORIZON;

    for (int i = 1; i < argc; ++i) {
        const std::string a = argv[i];
        if (a == "--horizon" && i + 1 < argc) horizon = std::atoi(argv[++i]);
        else if (a == "--csv" && i + 1 < argc) csv = argv[++i];
        else if (a.rfind("--", 0) != 0) path = a;
    }

    double eth_usd = 0.0;
    std::vector<Token> tokens;
    try {
        tokens = load_tokens(path, eth_usd);
    } catch (const std::exception& e) {
        std::printf("cannot read %s: %s\n", path.c_str(), e.what());
        return 2;
    }
    if (tokens.empty()) {
        std::printf("no usable price paths in %s\n", path.c_str());
        return 2;
    }

    std::printf("backtest over %s\n", path.c_str());
    std::printf("  %zu tokens, horizon %d fills, eth/usd %.2f\n\n", tokens.size(), horizon, eth_usd);

    // Difficulty knobs: the goalpost sits k sigma root T away from the cap at the open.
    const double ks[] = {0.5, 1.0, 1.5, 2.0};
    const predly::Kind kinds[] = {predly::Kind::Touch, predly::Kind::Floor};

    std::map<int, Bucket> calibration;   // keyed by the decile of the quoted price
    long total_markets = 0;

    for (const Token& tok : tokens) {
        const std::size_t n = tok.caps.size();
        for (std::size_t open = 20; open + static_cast<std::size_t>(horizon) < n; ++open) {
            // Volatility from the fills before the open, never from the future.
            const std::vector<double> hist(tok.caps.begin() + static_cast<long>(open) - 20,
                                           tok.caps.begin() + static_cast<long>(open));
            const double sigma = predly::realized_sigma(hist);
            const double cap = tok.caps[open];
            // Sigma is per hour and the model counts twelve bars to the hour, so a horizon
            // measured in fills converts the same way. Fills are not evenly spaced in time,
            // which makes this a first order calibration rather than a wall clock backtest.
            const double hours = static_cast<double>(horizon) / predly::BARS_PER_HOUR;

            for (double k : ks) {
                for (predly::Kind kind : kinds) {
                    const double level = kind == predly::Kind::Touch
                                             ? predly::target_for(cap, sigma, hours, k)
                                             : predly::target_for(cap, sigma, hours, -k);
                    const predly::Quote q = predly::quote(cap, level, sigma, hours, kind);

                    bool touched = false;
                    for (int step = 1; step <= horizon; ++step) {
                        const double c = tok.caps[open + static_cast<std::size_t>(step)];
                        if (kind == predly::Kind::Touch ? c >= level : c <= level) {
                            touched = true;
                            break;
                        }
                    }
                    const bool yes = kind == predly::Kind::Touch ? touched : !touched;

                    Bucket& b = calibration[q.yes_cents / 10];
                    ++b.markets;
                    b.priced_sum += q.p_yes;
                    if (yes) ++b.resolved_yes;
                    ++total_markets;
                }
            }
        }
    }

    std::printf("  %-12s %10s %10s %10s %9s\n", "quoted", "markets", "avg price", "hit rate", "gap");
    std::printf("  %-12s %10s %10s %10s %9s\n", "------", "-------", "---------", "--------", "---");

    double worst = 0.0;
    for (const auto& kv : calibration) {
        const Bucket& b = kv.second;
        if (b.markets < 30) continue;
        const double avg = b.priced_sum / static_cast<double>(b.markets);
        const double hit = static_cast<double>(b.resolved_yes) / static_cast<double>(b.markets);
        const double gap = hit - avg;
        worst = std::max(worst, std::fabs(gap));
        char band[16];
        std::snprintf(band, sizeof(band), "%d-%dc", kv.first * 10, kv.first * 10 + 9);
        std::printf("  %-12s %10ld %9.1f%% %9.1f%% %+8.1f%%\n", band, b.markets, avg * 100.0,
                    hit * 100.0, gap * 100.0);
    }

    std::printf("\n  %ld markets replayed, worst calibration gap %.1f%%\n", total_markets, worst * 100.0);
    std::printf("  a positive gap means the model quoted the outcome too cheaply\n");

    if (!csv.empty()) {
        std::ofstream out(csv);
        if (!out) {
            std::printf("  cannot write %s\n", csv.c_str());
            return 2;
        }
        out << "band_low_cents,markets,avg_price,hit_rate\n";
        for (const auto& kv : calibration) {
            const Bucket& b = kv.second;
            out << kv.first * 10 << "," << b.markets << ","
                << b.priced_sum / static_cast<double>(b.markets) << ","
                << static_cast<double>(b.resolved_yes) / static_cast<double>(b.markets) << "\n";
        }
        std::printf("  written %s\n", csv.c_str());
    }
    return 0;
}
