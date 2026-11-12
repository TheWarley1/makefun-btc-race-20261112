import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def hello():
    return {
        "type": "hello",
        "protocol": "agent-fun/bars-replay/v1",
        "seed": "7",
        "symbols": [{"symbol": "CBBTC", "mint": "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij", "price_scale": 6, "qty_scale": 8}],
        "capital": {"quote": "USDC", "quote_scale": 6, "quote_units": "1000000000"},
        "bar_interval": "1m",
        "first_close_ms": 1,
        "caps": {"max_open_positions": 1, "max_orders_per_bar": 16, "max_weight_bps": 10000, "shorts": False, "leverage": False},
        "fees": {"fee_bps": 4, "slippage_bps": 2, "min_notional_quote_units": "1000000"},
        "latency_bars": 1,
    }


def batch(seq, close, cash="1000000000", positions=None):
    return {
        "type": "batch",
        "seq": seq,
        "t": seq + 1,
        "bars": [{"symbol": "CBBTC", "t": seq + 1, "o": str(close), "h": str(close), "l": str(close), "c": str(close), "v": None, "o_depth": ["1000000000000"], "c_depth": ["1000000000000"]}],
        "fills": [],
        "account": {"cash_quote_units": cash, "positions": positions or [], "equity_quote_units": "1000000000"},
    }


class ProtocolTests(unittest.TestCase):
    def run_bot(self, messages):
        wire = "".join(json.dumps(message) + "\n" for message in messages)
        return subprocess.run(
            ["node", str(ROOT / "main.ts")],
            input=wire,
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )

    def test_protocol_replies_to_every_batch(self):
        messages = [hello()]
        messages.extend(batch(i, 100_000_000_000 + i * 10_000_000) for i in range(35))
        messages.append({"type": "done", "seq": 35, "reason": "end_of_data", "account": {"cash_quote_units": "1000000000", "positions": [], "equity_quote_units": "1000000000"}})
        result = self.run_bot(messages)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(replies), 35)
        self.assertEqual([reply["seq"] for reply in replies], list(range(35)))
        self.assertTrue(all(reply["type"] == "reply" for reply in replies))
        self.assertTrue(all(len(reply["orders"]) <= 1 for reply in replies))
    def test_rejects_one_bar_spike_but_accepts_persistent_trend(self):
        flat = [100_000_000_000] * 120 + [100_300_000_000]
        messages = [hello(), *(batch(i, price) for i, price in enumerate(flat))]
        messages.append({"type": "done", "seq": len(flat), "reason": "end_of_data", "account": {"cash_quote_units": "1000000000", "positions": [], "equity_quote_units": "1000000000"}})
        spike = self.run_bot(messages)
        self.assertEqual(spike.returncode, 0, spike.stderr)
        self.assertEqual(json.loads(spike.stdout.splitlines()[-1])["orders"], [])

        rising = [100_000_000_000 + i * 20_000_000 for i in range(121)]
        messages = [hello(), *(batch(i, price) for i, price in enumerate(rising))]
        messages.append({"type": "done", "seq": len(rising), "reason": "end_of_data", "account": {"cash_quote_units": "1000000000", "positions": [], "equity_quote_units": "1000000000"}})
        trend = self.run_bot(messages)
        self.assertEqual(trend.returncode, 0, trend.stderr)
        order = json.loads(trend.stdout.splitlines()[-1])["orders"][0]
        self.assertEqual((order["side"], order["symbol"]), ("buy", "CBBTC"))
    def test_rejects_unknown_protocol(self):
        wrong = hello()
        wrong["protocol"] = "wrong/v1"
        result = self.run_bot([wrong, {"type": "done", "seq": 0, "reason": "aborted", "account": {"cash_quote_units": "1000000000", "positions": [], "equity_quote_units": "1000000000"}}])
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
