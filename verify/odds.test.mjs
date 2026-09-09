/**
 * The TypeScript engine has to agree with the published vectors, cent for cent.
 * Run with: npm test   (compiles verify/odds.ts, then executes this file)
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { phi, quote, realizedSigma, targetFor, P_MIN, P_MAX } from "../dist/verify/odds.js";

const here = dirname(fileURLToPath(import.meta.url));
const V = JSON.parse(readFileSync(join(here, "vectors.json"), "utf8"));

test("phi matches known points of the normal CDF", () => {
  assert.ok(Math.abs(phi(0) - 0.5) < 1e-6);
  assert.ok(Math.abs(phi(1) - 0.8413) < 1e-3);
  assert.ok(Math.abs(phi(-1) - 0.1587) < 1e-3);
  assert.ok(Math.abs(phi(1.96) - 0.975) < 1e-3);
});

test("phi is symmetric around zero", () => {
  for (const x of [0.13, 0.84, 1.5, 2.7]) {
    assert.ok(Math.abs(phi(x) + phi(-x) - 1) < 1e-6);
  }
});

test("every published vector reproduces", () => {
  for (const v of V.vectors) {
    const q = quote(v.cap, v.level, v.sigma, v.hours, v.kind);
    assert.equal(q.yesCents, v.yes_cents, v.name);
    assert.equal(q.noCents, v.no_cents, v.name);
    assert.ok(Math.abs(q.d - v.d) < 1e-5, `${v.name}: d drifted`);
  }
});

test("realized sigma matches the published series", () => {
  const s = V.sigma_series;
  assert.ok(Math.abs(realizedSigma(s.closes) - s.expected_sigma) < 1e-6);
});

test("yes and no always add up to a dollar", () => {
  const cases = [
    [1e5, 2e5, 0.5, 1, "touch"], [5e6, 4e6, 0.2, 12, "floor"],
    [9e8, 1e9, 1.2, 0.1, "touch"], [3e4, 2.9e4, 2.5, 24, "floor"],
  ];
  for (const [cap, level, sigma, hours, kind] of cases) {
    const q = quote(cap, level, sigma, hours, kind);
    assert.equal(q.yesCents + q.noCents, 100);
  }
});

test("probability stays inside the clamps", () => {
  assert.ok(quote(1e3, 1e12, 0.1, 0.02, "touch").pYes >= P_MIN);
  assert.ok(quote(1e12, 1, 0.1, 24, "floor").pYes <= P_MAX);
});

test("a closer target is never cheaper", () => {
  const base = quote(100000, 150000, 0.6, 3, "touch");
  const closer = quote(100000, 120000, 0.6, 3, "touch");
  assert.ok(closer.pYes >= base.pYes);
});

test("time helps a touch market and hurts a floor market", () => {
  assert.ok(quote(100000, 150000, 0.6, 8, "touch").pYes > quote(100000, 150000, 0.6, 1, "touch").pYes);
  assert.ok(quote(100000, 80000, 0.6, 8, "floor").pYes < quote(100000, 80000, 0.6, 1, "floor").pYes);
});

test("a volatility scaled goalpost sits above the cap", () => {
  assert.ok(targetFor(250000, 0.4, 1, 1) > 250000);
});

test("nonsense inputs throw", () => {
  assert.throws(() => quote(0, 1, 0.5, 1));
  assert.throws(() => quote(1, 0, 0.5, 1));
  assert.throws(() => quote(1, 1, 0, 1));
});
