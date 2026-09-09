from historical_pattern import analyze_historical_pattern


def test_insufficient_history_returns_no_trade():
    candles = [{"close": 100 + i * 0.1} for i in range(12)]
    result = analyze_historical_pattern(candles, "EURUSD_otc")
    assert result["signal"] == "NO TRADE"


def test_engine_never_claims_guaranteed_signal():
    candles = []
    price = 100.0
    for i in range(100):
        price *= 1.001 if (i % 4) else 0.999
        candles.append({"close": price})
    result = analyze_historical_pattern(candles, "EURUSD_otc")
    assert result["signal"] in {"CALL", "PUT", "NO TRADE"}
    assert 0 <= result["confidence"] <= 99
