"""Exercise an explicitly supplied protected preview, using only its isolated test document."""

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from mcp_http_smoke import check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--share-url-file", required=True)
    args = parser.parse_args()
    share_url = Path(args.share_url_file).read_text().strip()
    assert urlsplit(args.url).scheme == "https"
    assert urlsplit(args.url).netloc == urlsplit(share_url).netloc
    headers = {"x-preview-token": os.environ["PREVIEW_ACCESS_TOKEN"]}
    borrower = ("borrower-a", os.environ["LOCAL_BORROWER_A_PASSWORD"])
    other = ("borrower-b", os.environ["LOCAL_BORROWER_B_PASSWORD"])
    staff = ("equipment-staff", os.environ["LOCAL_STAFF_PASSWORD"])
    operator = ("local-operator", os.environ["LOCAL_OPERATOR_PASSWORD"])

    with httpx.Client(base_url=args.url, headers=headers, timeout=60, follow_redirects=True) as client:
        assert client.get(share_url).status_code == 200
        status = client.get("/")
        assert status.status_code == 200
        assert status.json()["document"] == "demo/" + os.environ["VERCEL_TEST_DOCUMENT_ID"]
        assert status.json()["document"].startswith("demo/vercel-test-")
        with httpx.Client(base_url=args.url, cookies=client.cookies, timeout=30) as anonymous:
            assert anonymous.get("/mcp").status_code == 401
        assert client.get("/dev-login").status_code == 404
        assert client.get("/static/locker.css").status_code == 200
        assert client.get("/locker", auth=staff).status_code == 200

        def post(path, auth, body=None, expected=200):
            response = client.post(path, auth=auth, json=body)
            assert response.status_code == expected, (path, response.status_code, response.text[:300])
            return response.json() if response.content else None

        def reset(scenario="spare_available"):
            post("/local-test/reset", operator, {"scenario": scenario}, expected=204)

        post("/local-test/reset", staff, {"scenario": "spare_available"}, expected=403)
        reset()
        offer = post("/reservation-offers", borrower, {
            "category": "projector", "pickup_at": "2026-11-07T10:30", "duration_minutes": 60,
        }, expected=201)
        booking = post(f"/reservation-offers/{offer['id']}/confirm", borrower)
        assert post(f"/reservation-offers/{offer['id']}/confirm", borrower) == booking
        post(f"/reservations/{booking['id']}/load", staff)
        post("/local-test/clock/advance", operator, {"minutes": 30}, expected=204)
        pickups = client.get("/pickups", auth=borrower).json()
        pickup = next(item for item in pickups if item["id"] == booking["id"])
        post(f"/reservations/{booking['id']}/unlock", borrower, {"code": pickup["code"]})
        loan = post(f"/reservations/{booking['id']}/confirm-pickup", borrower)
        assert loan["status"] == "active"
        asset = booking["asset_id"]
        post(f"/assets/{asset}/return-request", borrower)
        returned = next(item for item in client.get("/returns", auth=borrower).json() if item["asset_id"] == asset)
        post(f"/assets/{asset}/return-unlock", borrower, {"code": returned["code"]})
        post(f"/assets/{asset}/return-drop", borrower)
        post(f"/assets/{asset}/verify-return", staff, {"result": "pass"})
        loans = client.get("/returns", auth=borrower).json()
        assert not any(item["asset_id"] == asset for item in loans)
        print("Vercel API booking, pickup, return, and role checks passed.")

        reset()
        request = {"category": "projector", "pickup_at": "2026-11-07T14:00",
                   "duration_minutes": 60, "require_built_in_speakers": True}
        offers = [(auth, post("/reservation-offers", auth, request, expected=201)) for auth in (borrower, other)]
        def confirm(item):
            auth, offer = item
            return client.post(f"/reservation-offers/{offer['id']}/confirm", auth=auth).status_code
        with ThreadPoolExecutor(max_workers=2) as workers:
            assert sorted(workers.map(confirm, offers)) == [200, 409]
        print("Vercel competing confirmations: one success, one conflict.")

        for scenario in ("spare_available", "spare_unavailable"):
            reset(scenario)
            post("/local-test/clock/advance", operator, {"minutes": 61}, expected=204)
            async def exercise():
                async with httpx.AsyncClient(headers=headers, cookies=client.cookies, timeout=60) as transport:
                    await check(args.url + "/mcp", scenario, http_client=transport)
            asyncio.run(exercise())
        print("Protected Vercel API and MCP checks passed against isolated cloud data.")


if __name__ == "__main__":
    main()
