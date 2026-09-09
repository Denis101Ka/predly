/**
 * Reference implementation of the Predly odds engine, TypeScript side.
 *
 * This is a line for line mirror of verify/odds.py. Both are replayed against
 * verify/vectors.json in CI, so the browser number, the server number and the
 * number you get on your own machine cannot drift apart quietly.
 */

export type Kind = "touch" | "floor";

export const P_MIN = 0.03;
export const P_MAX = 0.97;
export const SIGMA_MIN = 0.05;
export const SIGMA_MAX = 3.0;
export const TAU_MIN_HOURS = 1 / 60;
export const BARS_PER_HOUR = 12;
export const VOL_WINDOW_HOURS = 6;

export interface Quote {
  kind: Kind;
  d: number;
  pYes: number;
  yesCents: number;
  noCents: number;
}

/** Standard normal CDF, Abramowitz and Stegun 26.2.17. */
export function phi(x: number): number {
  const p = 0.2316419;
  const b = [0.31938153, -0.356563782, 1.781477937, -1.821255978, 1.330274429];
  const sign = x >= 0 ? 1 : -1;
  const ax = Math.abs(x);
  const t = 1 / (1 + p * ax);
  let poly = 0;
  for (let i = 0; i < b.length; i++) poly += b[i] * Math.pow(t, i + 1);
  const cdf = 1 - (1 / Math.sqrt(2 * Math.PI)) * Math.exp((-ax * ax) / 2) * poly;
  return sign > 0 ? cdf : 1 - cdf;
}

export function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v;
}

/** Hourly realized volatility from close to close log returns of five minute candles. */
export function realizedSigma(closes: number[], barsPerHour = BARS_PER_HOUR): number {
  if (closes.length < 3) return SIGMA_MIN;
  const rets: number[] = [];
  for (let i = 1; i < closes.length; i++) {
    const a = closes[i - 1];
    const b = closes[i];
    if (a > 0 && b > 0) rets.push(Math.log(b / a));
  }
  if (rets.length < 2) return SIGMA_MIN;
  const mean = rets.reduce((s, r) => s + r, 0) / rets.length;
  const varr = rets.reduce((s, r) => s + (r - mean) ** 2, 0) / (rets.length - 1);
  return clamp(Math.sqrt(varr) * Math.sqrt(barsPerHour), SIGMA_MIN, SIGMA_MAX);
}

/** Realized volatility over the trailing window only, the way a market open measures it. */
export function sigmaFromCandles(closes: number[], windowHours = VOL_WINDOW_HOURS): number {
  const need = windowHours * BARS_PER_HOUR + 1;
  return realizedSigma(closes.slice(-need));
}

/**
 * Price one market.
 * touch: will the cap reach `level` before the deadline (reach, double templates).
 * floor: will the cap stay above `level` until the deadline (hold template).
 */
export function quote(cap: number, level: number, sigma: number, hours: number, kind: Kind = "touch"): Quote {
  if (!(cap > 0) || !(level > 0)) throw new Error("cap and level must be positive");
  if (!(sigma > 0)) throw new Error("sigma must be positive");
  const tau = Math.max(hours, TAU_MIN_HOURS);
  const denom = clamp(sigma, SIGMA_MIN, SIGMA_MAX) * Math.sqrt(tau);

  let d: number;
  let p: number;
  if (kind === "touch") {
    d = Math.log(level / cap) / denom;
    p = 2 * (1 - phi(d));                 // reflection principle on the running maximum
  } else if (kind === "floor") {
    d = Math.log(cap / level) / denom;
    p = 2 * phi(d) - 1;                   // complement: never touching the floor
  } else {
    throw new Error(`unknown market kind: ${kind}`);
  }

  p = clamp(p, P_MIN, P_MAX);
  const yesCents = clamp(Math.round(p * 100), 1, 99);
  return { kind, d, pYes: p, yesCents, noCents: 100 - yesCents };
}

export function quoteFromCandles(cap: number, level: number, closes: number[], hours: number, kind: Kind = "touch"): Quote {
  return quote(cap, level, sigmaFromCandles(closes), hours, kind);
}

/** Where a volatility scaled goalpost sits: k sigma root T away from the cap. */
export function targetFor(cap: number, sigma: number, hours: number, k = 1): number {
  return cap * Math.exp(k * clamp(sigma, SIGMA_MIN, SIGMA_MAX) * Math.sqrt(Math.max(hours, TAU_MIN_HOURS)));
}

export function formatQuote(q: Quote): string {
  return `${q.kind}  d=${q.d.toFixed(4)}  p_yes=${q.pYes.toFixed(4)}  YES ${q.yesCents}c / NO ${q.noCents}c`;
}
