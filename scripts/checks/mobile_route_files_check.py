from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ROUTES = {
    "apps/mobile/app/(auth)/signup.tsx": "auth-signup",
    "apps/mobile/app/(auth)/quick-profile.tsx": "quick-profile",
    "apps/mobile/app/(consumer)/home.tsx": "consumer-home",
    "apps/mobile/app/(consumer)/merchant/[id].tsx": "merchant-detail",
    "apps/mobile/app/(consumer)/booking/[id].tsx": "booking-detail",
    "apps/mobile/app/(consumer)/checkin/[id].tsx": "checkin",
    "apps/mobile/app/(consumer)/payment/[id].tsx": "payment",
    "apps/mobile/app/(consumer)/evidence/[id].tsx": "evidence",
    "apps/mobile/app/(consumer)/profile/index.tsx": "profile",
    "apps/mobile/app/(consumer)/rewards/index.tsx": "rewards",
    "apps/mobile/app/(consumer)/rewards/redeem.tsx": "reward-redeem",
    "apps/mobile/app/(consumer)/rewards/celebration.tsx": "reward-celebration",
    "apps/mobile/app/(merchant-onboarding)/signup.tsx": "merchant-signup",
    "apps/mobile/app/(merchant-onboarding)/shop-info.tsx": "merchant-shop-info",
    "apps/mobile/app/(merchant-onboarding)/photos-services.tsx": "merchant-photos-services",
    "apps/mobile/app/(merchant-onboarding)/payment-setup.tsx": "merchant-payment-setup",
    "apps/mobile/app/(merchant)/queue/index.tsx": "merchant-queue",
    "apps/mobile/app/(merchant)/slots/index.tsx": "merchant-slots",
    "apps/mobile/app/(merchant)/summary/index.tsx": "merchant-summary",
    "apps/mobile/app/(merchant)/bookings/[id].tsx": "merchant-booking",
}
REQUIRED_STATES = {"loading", "empty", "error", "offline", "forbidden"}


def main() -> None:
    errors: list[str] = []
    for route, test_id_prefix in ROUTES.items():
        path = ROOT / route
        if not path.exists():
            errors.append(f"missing mobile route file: {route}")
            continue
        text = path.read_text()
        if "StateScaffold" not in text:
            errors.append(f"{route} does not use StateScaffold")
        if f'testIDPrefix="{test_id_prefix}"' not in text:
            errors.append(f"{route} does not expose testIDPrefix={test_id_prefix}")

    scaffold = (ROOT / "apps/mobile/components/StateScaffold.tsx").read_text()
    for state in REQUIRED_STATES:
        if state not in scaffold:
            errors.append(f"StateScaffold missing {state} state surface")

    if errors:
        for error in errors:
            print(error)
        raise SystemExit(1)
    print(f"ok: {len(ROUTES)} mobile route files present with test IDs and state scaffold")


if __name__ == "__main__":
    main()
