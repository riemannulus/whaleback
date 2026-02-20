#!/usr/bin/env python3
"""Whaleback E2E Smoke Test

Usage:
    python scripts/smoke_test.py [--api-url http://localhost:8000]

Requires: httpx (pip install httpx)
Tests all API endpoints and reports status.
"""

import sys
import argparse
import httpx


def main():
    parser = argparse.ArgumentParser(description="Whaleback smoke test")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()

    base = args.api_url
    passed = 0
    failed = 0

    tests = [
        # (name, method, path, expected_status, check_fn)
        ("Health check", "GET", "/api/v1/health", 200, lambda r: r.json()["status"] == "ok"),
        ("Pipeline status", "GET", "/api/v1/health/pipeline", 200, lambda r: "data" in r.json()),
        ("List stocks", "GET", "/api/v1/stocks?page=1&size=5", 200, lambda r: "data" in r.json()),
        ("Stock detail", "GET", "/api/v1/stocks/005930", 200, lambda r: r.json()["data"]["ticker"] == "005930"),
        ("Stock price", "GET", "/api/v1/stocks/005930/price", 200, lambda r: "data" in r.json()),
        ("Stock investors", "GET", "/api/v1/stocks/005930/investors", 200, lambda r: "data" in r.json()),
        # Quant endpoints - may 404 if analysis not computed yet
        ("Quant valuation", "GET", "/api/v1/analysis/quant/valuation/005930", [200, 404], None),
        ("Quant F-Score", "GET", "/api/v1/analysis/quant/fscore/005930", [200, 404], None),
        ("Quant grade", "GET", "/api/v1/analysis/quant/grade/005930", [200, 404], None),
        ("Quant rankings", "GET", "/api/v1/analysis/quant/rankings?page=1&size=5", 200, lambda r: "data" in r.json()),
        # Whale endpoints - may 404 if analysis not computed yet
        ("Whale score", "GET", "/api/v1/analysis/whale/score/005930", [200, 404], None),
        ("Whale accumulation", "GET", "/api/v1/analysis/whale/accumulation/005930", 200, lambda r: "data" in r.json()),
        ("Whale top", "GET", "/api/v1/analysis/whale/top?page=1&size=5", 200, lambda r: "data" in r.json()),
        # Trend endpoints - may 404 if analysis not computed yet
        ("Sector ranking", "GET", "/api/v1/analysis/trend/sector-ranking", 200, lambda r: "data" in r.json()),
        ("Relative strength", "GET", "/api/v1/analysis/trend/relative-strength/005930", [200, 404], None),
        ("Sector rotation", "GET", "/api/v1/analysis/trend/sector-rotation", 200, lambda r: "data" in r.json()),
    ]

    # Run tests with nice output
    client = httpx.Client(base_url=base, timeout=30.0)

    print(f"\n{'='*60}")
    print(f"  Whaleback Smoke Test")
    print(f"  API: {base}")
    print(f"{'='*60}\n")

    for test_data in tests:
        name = test_data[0]
        method = test_data[1]
        path = test_data[2]
        expected_status = test_data[3]
        check_fn = test_data[4] if len(test_data) > 4 else None

        # Handle both single status and list of acceptable statuses
        if isinstance(expected_status, list):
            acceptable_statuses = expected_status
        else:
            acceptable_statuses = [expected_status]

        try:
            resp = client.request(method, path)
            status_ok = resp.status_code in acceptable_statuses
            check_ok = True

            if check_fn and status_ok and resp.status_code == 200:
                try:
                    check_ok = check_fn(resp)
                except Exception as e:
                    check_ok = False
                    print(f"  FAIL  {name} (check failed: {e})")
                    failed += 1
                    continue

            if status_ok and check_ok:
                status_msg = f"{resp.status_code}"
                if resp.status_code == 404:
                    status_msg += " - analysis not computed"
                print(f"  PASS  {name} ({status_msg})")
                passed += 1
            else:
                print(f"  FAIL  {name} (got {resp.status_code}, expected {acceptable_statuses})")
                failed += 1
        except httpx.ConnectError:
            print(f"  ERROR {name}: Cannot connect to {base}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            failed += 1

    client.close()

    # Summary
    total = passed + failed
    print(f"\n{'='*60}")
    print(f"  Results: {passed}/{total} passed, {failed} failed")
    print(f"{'='*60}\n")

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
