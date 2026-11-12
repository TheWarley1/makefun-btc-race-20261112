"use strict";

import readline from "node:readline";

const SYMBOL = "CBBTC";
const MAX_SLIPPAGE_BPS = 100;
const BREAKOUT_BPS = 90n;
const HISTORY_BARS = 61;
const TAKE_PROFIT_BPS = 120n;
const STOP_LOSS_BPS = 150n;
const MAX_HOLD_BARS = 90;
const BPS = 10_000n;

const closes = [];
let hello = null;
let nextOrder = 1;
let entrySeq = null;

function returnBps(now, before) {
  return ((now - before) * BPS) / before;
}

function positionValue(qty, price) {
  const spec = hello.symbols.find((item) => item.symbol === SYMBOL);
  const quoteScale = BigInt(hello.capital.quote_scale);
  const assetScale = BigInt(spec.qty_scale + spec.price_scale);
  return (qty * price * 10n ** quoteScale) / 10n ** assetScale;
}

function decide(batch) {
  const bar = batch.bars.find((item) => item.symbol === SYMBOL);
  if (bar === undefined) return [];
  const close = BigInt(bar.c);
  closes.push(close);
  if (closes.length > HISTORY_BARS) closes.shift();

  const held = batch.account.positions.find((item) => item.symbol === SYMBOL);
  if (held !== undefined) {
    const qty = BigInt(held.qty);
    const cost = BigInt(held.cost_quote_units);
    const pnlBps = ((positionValue(qty, close) - cost) * BPS) / cost;
    const expired = entrySeq !== null && batch.seq - entrySeq >= MAX_HOLD_BARS;
    if (expired || pnlBps >= TAKE_PROFIT_BPS || pnlBps <= -STOP_LOSS_BPS) {
      return [{ side: "sell", client_id: `o${nextOrder++}`, symbol: SYMBOL, qty: qty.toString(), max_slippage_bps: MAX_SLIPPAGE_BPS }];
    }
    return [];
  }

  const warmingUp = (hello.warmup_bars ?? 0) > 0 && batch.seq < hello.warmup_bars;
  if (warmingUp || closes.length < HISTORY_BARS) return [];
  if (returnBps(close, closes[0]) < BREAKOUT_BPS) return [];

  const cash = BigInt(batch.account.cash_quote_units);
  const equity = BigInt(batch.account.equity_quote_units);
  const room = (BigInt(hello.caps.max_weight_bps) * equity) / BPS;
  const amount = cash < room ? cash : room;
  if (amount < BigInt(hello.fees.min_notional_quote_units)) return [];
  entrySeq = batch.seq;
  return [{ side: "buy", client_id: `o${nextOrder++}`, symbol: SYMBOL, notional_quote_units: amount.toString(), max_slippage_bps: MAX_SLIPPAGE_BPS }];
}

const lines = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of lines) {
  if (line.trim() === "") continue;
  const message = JSON.parse(line);
  if (message.type === "hello") {
    if (message.protocol !== "agent-fun/bars-replay/v1") {
      throw new Error(`unsupported protocol: ${String(message.protocol)}`);
    }
    hello = message;
  } else if (message.type === "batch") {
    const reply = { type: "reply", seq: message.seq, orders: decide(message) };
    process.stdout.write(`${JSON.stringify(reply)}\n`);
  } else if (message.type === "done") {
    break;
  } else {
    throw new Error(`unknown message type: ${String(message.type)}`);
  }
}
