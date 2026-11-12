import json
import unittest
from test_main import ProtocolTests, hello, batch

class BreakoutTests(ProtocolTests):
    def test_large_sixty_bar_breakout_does_not_need_many_nonflat_bars(self):
        prices = [100_000_000_000] * 60 + [101_000_000_000]
        result = self.run_bot([hello(), *(batch(i, p) for i, p in enumerate(prices)),
                               {"type": "done"}])
        self.assertEqual(result.returncode, 0, result.stderr)
        order = json.loads(result.stdout.splitlines()[-1])["orders"]
        self.assertEqual(len(order), 1)
        self.assertEqual(order[0]["side"], "buy")

if __name__ == "__main__":
    unittest.main()
