#!/usr/bin/env python3
"""Bulk symbol validation for all markets.

Tests ticker + klines availability for every symbol listed in BIST, US Stocks.
Crypto is dynamic from Binance so it's always valid.
"""
import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf

from app.core.bist_data import DEFAULT_SYMBOLS as BIST_SYMBOLS
from app.core.stocks_data import DEFAULT_SYMBOLS as STOCKS_SYMBOLS


def validate_batch(symbols, market_name, batch_size=50):
    """Validate symbols via yf.download batch."""
    working = []
    broken = []
    total = len(symbols)

    for i in range(0, total, batch_size):
        batch = symbols[i:i+batch_size]
        tickers_str = " ".join(batch)
        try:
            data = yf.download(tickers_str, period="5d", interval="1d",
                               progress=False, threads=True)
            if data is not None and not data.empty:
                if len(batch) == 1:
                    last = data['Close'].dropna()
                    if not last.empty and float(last.iloc[-1]) > 0:
                        working.append(batch[0])
                    else:
                        broken.append(batch[0])
                else:
                    for sym in batch:
                        try:
                            if sym in data['Close'].columns:
                                col = data['Close'][sym].dropna()
                                if not col.empty and float(col.iloc[-1]) > 0:
                                    working.append(sym)
                                else:
                                    broken.append(sym)
                            else:
                                broken.append(sym)
                        except Exception:
                            broken.append(sym)
            else:
                broken.extend(batch)
        except Exception as e:
            print(f"  Batch error: {e}")
            broken.extend(batch)

        done = min(i + batch_size, total)
        print(f"  [{market_name}] {done}/{total} tested "
              f"({len(working)} ok, {len(broken)} broken)")
        time.sleep(0.5)

    return working, broken


def main():
    results = {}

    # ── BIST ──
    print(f"\n{'='*60}")
    print(f"BIST — {len(BIST_SYMBOLS)} symbols")
    print('='*60)
    bist_ok, bist_bad = validate_batch(BIST_SYMBOLS, "BIST")
    results['bist'] = {'total': len(BIST_SYMBOLS), 'working': len(bist_ok),
                        'broken': len(bist_bad), 'broken_list': bist_bad}
    print(f"\n  BIST Result: {len(bist_ok)} working / {len(bist_bad)} broken")
    if bist_bad:
        print(f"  Broken: {bist_bad}")

    # ── US Stocks ──
    print(f"\n{'='*60}")
    print(f"US STOCKS — {len(STOCKS_SYMBOLS)} symbols")
    print('='*60)
    stk_ok, stk_bad = validate_batch(STOCKS_SYMBOLS, "STOCKS")
    results['stocks'] = {'total': len(STOCKS_SYMBOLS), 'working': len(stk_ok),
                          'broken': len(stk_bad), 'broken_list': stk_bad}
    print(f"\n  Stocks Result: {len(stk_ok)} working / {len(stk_bad)} broken")
    if stk_bad:
        print(f"  Broken: {stk_bad}")

    # ── Summary ──
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    for mkt, r in results.items():
        print(f"  {mkt:10s}: {r['working']:>4}/{r['total']:<4} working "
              f"({r['broken']} broken)")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), 'validation_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == '__main__':
    main()
