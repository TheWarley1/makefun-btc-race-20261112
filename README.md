# Causal 60-Bar BTC Breakout

Deterministic Node 22, standard-library-only cbBTC/USDC paper-trading bot. It speaks the published hello, batch, reply/orders and done NDJSON protocol. No real wallet funds are traded.

Enter when the latest close is at least 90 basis points above the close 60 observed bars ago. Sell at a 120 bp marked gain, a 150 bp marked loss, or 90 bars after the entry signal. Integer arithmetic owns sizing and decisions. Orders are filled by the official simulator on the next bar, after its fees, slippage and price impact. No future prices, dates, wall clock or random choices are used.

Parameters were selected from a small causal grid on the public dev window. This is tuning data, not an untouched holdout or evidence of future profitability.

Tests: `PYTHONDONTWRITEBYTECODE=1 python3.13 -m unittest test_main test_breakout -v`

Local grade from the kit: `node cli/makefun.mjs grade-local --kit . --bot /path/to/repository --driver process`

Runtime: `node main.ts`, with protocol messages on stdin and replies on stdout. Code is MIT licensed.
