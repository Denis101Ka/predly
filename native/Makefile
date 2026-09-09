# Native tools. No dependencies, no build system required beyond make and a C++17 compiler.
#
#   make            build everything into bin/
#   make test       build and replay the shared vectors
#   make check      vectors plus the Monte Carlo validation of the closed form
#   make clean

CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra -Wpedantic
BIN      := bin
ROOT     := ..

TARGETS := $(BIN)/odds $(BIN)/vectors_test $(BIN)/montecarlo $(BIN)/backtest

all: $(TARGETS)

$(BIN):
	mkdir -p $(BIN)

$(BIN)/odds: odds_cli.cpp odds.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ odds_cli.cpp

$(BIN)/vectors_test: vectors_test.cpp odds.hpp json.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ vectors_test.cpp

$(BIN)/montecarlo: montecarlo.cpp odds.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ montecarlo.cpp

$(BIN)/backtest: backtest.cpp odds.hpp json.hpp | $(BIN)
	$(CXX) $(CXXFLAGS) -o $@ backtest.cpp

test: $(BIN)/vectors_test
	./$(BIN)/vectors_test $(ROOT)/verify/vectors.json

check: test $(BIN)/montecarlo
	./$(BIN)/montecarlo 60000 --steps 800

backtest: $(BIN)/backtest
	./$(BIN)/backtest $(ROOT)/data/snapshot-latest.json

bench: $(BIN)/odds
	./$(BIN)/odds --bench 5000000

clean:
	rm -rf $(BIN)

.PHONY: all test check backtest bench clean
