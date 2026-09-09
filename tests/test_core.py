import unittest

from fastapi.testclient import TestClient

from indicators import analyze_candles
from main import PAIRS, app
from signal_engine import generate_signal


class CoreTests(unittest.TestCase):
    def make_candles(self, count=100):
        candles = []
        price = 1.1000
        for i in range(count):
            close = price + (0.0001 if i % 3 else -0.00003)
            candles.append({
                "timestamp": i,
                "open": price,
                "high": max(price, close) + 0.00005,
                "low": min(price, close) - 0.00005,
                "close": close,
            })
            price = close
        return candles

    def test_indicators_and_signal(self):
        analysis = analyze_candles(self.make_candles())
        result = generate_signal(analysis)
        self.assertEqual(analysis["candles_used"], 100)
        self.assertIn(result["signal"], {"CALL", "PUT", "NO TRADE"})
        self.assertGreaterEqual(result["confidence"], 0)
        self.assertLessEqual(result["confidence"], 100)

    def test_api_pairs(self):
        client = TestClient(app)
        response = client.get("/api/pairs")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pairs"], PAIRS)

    def test_health(self):
        client = TestClient(app)
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
