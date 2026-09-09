// Replay verify/vectors.json through the native engine.
//
// The same file drives the Python and the TypeScript suites. If this binary and those two
// ever disagree by a single cent, CI stops the build: three independent implementations of
// one formula is the cheapest proof that the number on the board is not hand-placed.
//
//   ./bin/vectors_test [path/to/vectors.json]

#include <cmath>
#include <cstdio>
#include <iostream>
#include <string>

#include "json.hpp"
#include "odds.hpp"

using predly::Kind;
using predly::Quote;

namespace {

int failures = 0;

void check(bool ok, const std::string& what) {
    if (!ok) {
        std::cout << "  FAIL " << what << "\n";
        ++failures;
    }
}

void near(double got, double want, double tol, const std::string& what) {
    if (std::fabs(got - want) > tol) {
        std::printf("  FAIL %s: got %.8f want %.8f\n", what.c_str(), got, want);
        ++failures;
    }
}

void test_phi() {
    std::cout << "phi, the normal CDF\n";
    near(predly::phi(0.0), 0.5, 1e-6, "phi(0)");
    near(predly::phi(1.0), 0.8413, 1e-3, "phi(1)");
    near(predly::phi(-1.0), 0.1587, 1e-3, "phi(-1)");
    near(predly::phi(1.96), 0.9750, 1e-3, "phi(1.96)");
    for (double x : {0.13, 0.84, 1.5, 2.7}) {
        near(predly::phi(x) + predly::phi(-x), 1.0, 1e-6, "symmetry");
    }
    // The approximation should track the exact CDF closely enough that rounding to a cent
    // can never land on a different integer.
    for (double x = -3.0; x <= 3.0; x += 0.25) {
        const double exact = 0.5 * (1.0 + std::erf(x / std::sqrt(2.0)));
        near(predly::phi(x), exact, 8e-8, "against erf");
    }
}

void test_vectors(const std::string& path) {
    std::cout << "published vectors from " << path << "\n";
    const auto doc = predly::json::load(path);
    const auto* vecs = doc.find("vectors");
    if (!vecs || !vecs->is_array()) {
        std::cout << "  FAIL vectors array missing\n";
        ++failures;
        return;
    }
    int n = 0;
    for (const auto& v : vecs->arr()) {
        const std::string name = v.str_or("name", "unnamed");
        const Quote q = predly::quote(v.num_or("cap", 0), v.num_or("level", 0), v.num_or("sigma", 0),
                                      v.num_or("hours", 0), predly::kind_from(v.str_or("kind", "touch")));
        const int want_yes = static_cast<int>(v.num_or("yes_cents", -1));
        const int want_no = static_cast<int>(v.num_or("no_cents", -1));
        check(q.yes_cents == want_yes, name + ": yes cents");
        check(q.no_cents == want_no, name + ": no cents");
        near(q.d, v.num_or("d", 0), 1e-5, name + ": d");
        std::printf("  %-44s %2dc / %2dc\n", name.c_str(), q.yes_cents, q.no_cents);
        ++n;
    }
    std::printf("  %d vectors replayed\n", n);

    const auto* series = doc.find("sigma_series");
    if (series && series->is_object()) {
        const auto* closes = series->find("closes");
        if (closes && closes->is_array()) {
            std::vector<double> xs;
            for (const auto& c : closes->arr()) xs.push_back(c.num());
            near(predly::realized_sigma(xs), series->num_or("expected_sigma", 0), 1e-6, "realized sigma");
        }
    }
}

void test_invariants() {
    std::cout << "invariants\n";
    struct Case { double cap, level, sigma, hours; Kind kind; };
    const Case cases[] = {
        {1e5, 2e5, 0.5, 1, Kind::Touch},
        {5e6, 4e6, 0.2, 12, Kind::Floor},
        {9e8, 1e9, 1.2, 0.1, Kind::Touch},
        {3e4, 2.9e4, 2.5, 24, Kind::Floor},
    };
    for (const auto& c : cases) {
        const Quote q = predly::quote(c.cap, c.level, c.sigma, c.hours, c.kind);
        check(q.yes_cents + q.no_cents == 100, "cents sum to a dollar");
        check(q.p_yes >= predly::P_MIN - 1e-12 && q.p_yes <= predly::P_MAX + 1e-12, "probability clamped");
    }

    const Quote base = predly::quote(100000, 150000, 0.6, 3, Kind::Touch);
    const Quote closer = predly::quote(100000, 120000, 0.6, 3, Kind::Touch);
    check(closer.p_yes >= base.p_yes, "a closer target is never cheaper");

    check(predly::quote(100000, 150000, 0.6, 8, Kind::Touch).p_yes >
          predly::quote(100000, 150000, 0.6, 1, Kind::Touch).p_yes, "time helps a touch market");
    check(predly::quote(100000, 80000, 0.6, 8, Kind::Floor).p_yes <
          predly::quote(100000, 80000, 0.6, 1, Kind::Floor).p_yes, "time hurts a floor market");
    check(predly::target_for(250000, 0.4, 1.0, 1.0) > 250000, "goalpost sits above the cap");

    bool threw = false;
    try {
        predly::quote(0, 1, 0.5, 1, Kind::Touch);
    } catch (const std::invalid_argument&) {
        threw = true;
    }
    check(threw, "a zero cap is rejected");
}

}  // namespace

int main(int argc, char** argv) {
    const std::string path = argc > 1 ? argv[1] : "verify/vectors.json";
    try {
        test_phi();
        test_vectors(path);
        test_invariants();
    } catch (const std::exception& e) {
        std::cout << "error: " << e.what() << "\n";
        return 2;
    }
    if (failures == 0) {
        std::cout << "\nall native checks passed\n";
        return 0;
    }
    std::printf("\n%d check(s) failed\n", failures);
    return 1;
}
