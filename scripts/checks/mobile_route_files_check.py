from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

ROUTES = [
    "apps/mobile/app/(auth)/signup.tsx",
    "apps/mobile/app/(auth)/quick-profile.tsx",
    "apps/mobile/app/(consumer)/home.tsx",
    "apps/mobile/app/(consumer)/merchant/[id].tsx",
    "apps/mobile/app/(consumer)/booking/[id].tsx",
    "apps/mobile/app/(consumer)/checkin/[id].tsx",
    "apps/mobile/app/(consumer)/payment/[id].tsx",
    "apps/mobile/app/(consumer)/evidence/[id].tsx",
    "apps/mobile/app/(consumer)/profile/index.tsx",
    "apps/mobile/app/(consumer)/rewards/index.tsx",
    "apps/mobile/app/(consumer)/rewards/redeem.tsx",
    "apps/mobile/app/(consumer)/rewards/celebration.tsx",
    "apps/mobile/app/(merchant-onboarding)/signup.tsx",
    "apps/mobile/app/(merchant-onboarding)/shop-info.tsx",
    "apps/mobile/app/(merchant-onboarding)/photos-services.tsx",
    "apps/mobile/app/(merchant-onboarding)/payment-setup.tsx",
    "apps/mobile/app/(merchant)/queue/index.tsx",
    "apps/mobile/app/(merchant)/slots/index.tsx",
    "apps/mobile/app/(merchant)/summary/index.tsx",
    "apps/mobile/app/(merchant)/bookings/[id].tsx",
]


def main() -> None:
    missing = [route for route in ROUTES if not (ROOT / route).exists()]
    if missing:
        for route in missing:
            print(f"missing mobile route file: {route}")
        raise SystemExit(1)
    print(f"ok: {len(ROUTES)} mobile route files present")


if __name__ == "__main__":
    main()
