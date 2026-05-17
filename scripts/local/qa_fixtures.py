from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from sqlalchemy import delete, or_, select

from app.db.models import (
    AccountDeletionRequest,
    AuditLog,
    Booking,
    Complaint,
    DataExportJob,
    DeviceRegistration,
    Evidence,
    Merchant,
    MerchantEkycSubmission,
    MerchantGoldenHour,
    MerchantPaymentSetup,
    MerchantService,
    NotificationPreference,
    Payment,
    PriceChangeLog,
    Profile,
    PromoCode,
    PromoCodeUsage,
    Rating,
    Referral,
    RefreshToken,
    RewardStamp,
    RewardVoucher,
    ServiceTemplate,
    SlotCapacity,
    SupportRequest,
    Tenant,
    TenantMembership,
    User,
    Vehicle,
)
from app.db.session import get_sessionmaker, set_local_context
from app.services.auth_service import AuthService, password_hasher
from app.services.marketplace_service import round_to_current_slot

TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
CONSUMER_ID = UUID("00000000-0000-0000-0002-000000000001")
MERCHANT_OWNER_ID = UUID("00000000-0000-0000-0002-000000000002")
OPS_USER_ID = UUID("00000000-0000-0000-0002-000000000003")
MERCHANT_ID = UUID("00000000-0000-0000-0003-000000000001")
SERVICE_ID = UUID("00000000-0000-0000-0003-000000000002")
COMPLETED_SLOT_ID = UUID("00000000-0000-0000-0003-000000000003")
COMPLETED_BOOKING_ID = UUID("00000000-0000-0000-0003-000000000004")
COMPLETED_PAYMENT_ID = UUID("00000000-0000-0000-0003-000000000005")
COMPLETED_RATING_ID = UUID("00000000-0000-0000-0003-000000000006")
COMPLAINT_ID = UUID("00000000-0000-0000-0003-000000000007")
PROMO_ID = UUID("00000000-0000-0000-0003-000000000008")
VOUCHER_ID = UUID("00000000-0000-0000-0003-000000000009")
VEHICLE_ID = UUID("00000000-0000-0000-0003-000000000010")

PASSWORD = "correct-horse-battery"
SMOKE_SIGNUP_EMAIL = "qa.signup@truecare.local"
PERSONAS = {
    "consumer": {
        "id": CONSUMER_ID,
        "email": "qa.consumer@truecare.local",
        "name": "Local QA Consumer",
        "role": "consumer",
    },
    "merchant_owner": {
        "id": MERCHANT_OWNER_ID,
        "email": "qa.merchant@truecare.local",
        "name": "Local QA Merchant",
        "role": "merchant",
    },
    "ops": {
        "id": OPS_USER_ID,
        "email": "qa.ops@truecare.local",
        "name": "Local QA Ops",
        "role": "ops",
    },
}


async def _upsert_user(session, *, user_id: UUID, email: str, name: str, role: str) -> User:
    user = await session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            tenant_id=TENANT_ID,
            email=email,
            password_hash=password_hasher.hash(PASSWORD),
            name=name,
            role=role,
            referral_code=email.split("@", 1)[0].replace(".", "").upper()[:10],
        )
        session.add(user)
    else:
        user.email = email
        user.name = name
        user.role = role
        user.password_hash = password_hasher.hash(PASSWORD)
        user.deleted_at = None

    membership = await session.get(TenantMembership, (user_id, TENANT_ID))
    if membership is None:
        session.add(TenantMembership(user_id=user_id, tenant_id=TENANT_ID, role=role))
    else:
        membership.role = role

    profile = await session.get(Profile, user_id)
    if profile is None:
        session.add(Profile(user_id=user_id, tenant_id=TENANT_ID, display_name=name, locale="vi"))
    else:
        profile.display_name = name
        profile.locale = "vi"

    preference = await session.get(NotificationPreference, user_id)
    if preference is None:
        session.add(NotificationPreference(user_id=user_id, tenant_id=TENANT_ID))
    await session.flush()
    return user


async def _clear_fixture_rows(session) -> None:
    transient_user_ids = (
        await session.scalars(select(User.id).where(User.tenant_id == TENANT_ID, User.email == SMOKE_SIGNUP_EMAIL))
    ).all()
    booking_ids = (
        await session.scalars(
            select(Booking.id).where(
                Booking.tenant_id == TENANT_ID,
                or_(Booking.user_id == CONSUMER_ID, Booking.merchant_id == MERCHANT_ID),
            )
        )
    ).all()
    payment_ids = (
        await session.scalars(select(Payment.id).where(Payment.tenant_id == TENANT_ID, Payment.booking_id.in_(booking_ids)))
    ).all() if booking_ids else []

    await session.execute(delete(AuditLog).where(AuditLog.tenant_id == TENANT_ID, AuditLog.actor_user_id.in_([CONSUMER_ID, MERCHANT_OWNER_ID, OPS_USER_ID])))
    if booking_ids:
        await session.execute(delete(PromoCodeUsage).where(PromoCodeUsage.tenant_id == TENANT_ID, PromoCodeUsage.booking_id.in_(booking_ids)))
        await session.execute(delete(RewardStamp).where(RewardStamp.tenant_id == TENANT_ID, RewardStamp.booking_id.in_(booking_ids)))
        await session.execute(delete(Rating).where(Rating.tenant_id == TENANT_ID, Rating.booking_id.in_(booking_ids)))
        await session.execute(delete(Complaint).where(Complaint.tenant_id == TENANT_ID, Complaint.booking_id.in_(booking_ids)))
        await session.execute(delete(Evidence).where(Evidence.tenant_id == TENANT_ID, Evidence.booking_id.in_(booking_ids)))
        await session.execute(delete(Payment).where(Payment.tenant_id == TENANT_ID, Payment.booking_id.in_(booking_ids)))
        await session.execute(delete(RewardVoucher).where(RewardVoucher.tenant_id == TENANT_ID, or_(RewardVoucher.reserved_booking_id.in_(booking_ids), RewardVoucher.redeemed_booking_id.in_(booking_ids))))
        await session.execute(delete(Booking).where(Booking.tenant_id == TENANT_ID, Booking.id.in_(booking_ids)))

    await session.execute(delete(RewardVoucher).where(RewardVoucher.tenant_id == TENANT_ID, RewardVoucher.user_id == CONSUMER_ID))
    await session.execute(delete(Referral).where(Referral.tenant_id == TENANT_ID, or_(Referral.referrer_id == CONSUMER_ID, Referral.referee_id == CONSUMER_ID)))
    await session.execute(delete(DataExportJob).where(DataExportJob.tenant_id == TENANT_ID, DataExportJob.user_id.in_([CONSUMER_ID, OPS_USER_ID])))
    await session.execute(delete(SupportRequest).where(SupportRequest.tenant_id == TENANT_ID, SupportRequest.created_by_user_id.in_([CONSUMER_ID, OPS_USER_ID])))
    await session.execute(delete(AccountDeletionRequest).where(AccountDeletionRequest.tenant_id == TENANT_ID, AccountDeletionRequest.user_id == CONSUMER_ID))
    await session.execute(delete(DeviceRegistration).where(DeviceRegistration.tenant_id == TENANT_ID, DeviceRegistration.user_id.in_([CONSUMER_ID, MERCHANT_OWNER_ID, OPS_USER_ID])))
    await session.execute(delete(Vehicle).where(Vehicle.tenant_id == TENANT_ID, Vehicle.user_id == CONSUMER_ID))
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_([CONSUMER_ID, MERCHANT_OWNER_ID, OPS_USER_ID])))
    await session.execute(delete(PromoCode).where(PromoCode.tenant_id == TENANT_ID, PromoCode.code == "LOCALQA20"))
    if payment_ids:
        await session.execute(delete(AuditLog).where(AuditLog.tenant_id == TENANT_ID, AuditLog.target_id.in_(payment_ids)))
    await session.execute(delete(MerchantEkycSubmission).where(MerchantEkycSubmission.tenant_id == TENANT_ID, MerchantEkycSubmission.merchant_id == MERCHANT_ID))
    await session.execute(delete(MerchantPaymentSetup).where(MerchantPaymentSetup.tenant_id == TENANT_ID, MerchantPaymentSetup.merchant_id == MERCHANT_ID))
    await session.execute(delete(PriceChangeLog).where(PriceChangeLog.tenant_id == TENANT_ID, PriceChangeLog.merchant_service_id == SERVICE_ID))
    await session.execute(delete(MerchantGoldenHour).where(MerchantGoldenHour.tenant_id == TENANT_ID, MerchantGoldenHour.merchant_id == MERCHANT_ID))
    await session.execute(delete(SlotCapacity).where(SlotCapacity.tenant_id == TENANT_ID, SlotCapacity.merchant_id == MERCHANT_ID))
    await session.execute(delete(MerchantService).where(MerchantService.tenant_id == TENANT_ID, MerchantService.merchant_id == MERCHANT_ID))
    await session.execute(delete(Merchant).where(Merchant.tenant_id == TENANT_ID, Merchant.id == MERCHANT_ID))

    if transient_user_ids:
        await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(transient_user_ids)))
        await session.execute(delete(DeviceRegistration).where(DeviceRegistration.tenant_id == TENANT_ID, DeviceRegistration.user_id.in_(transient_user_ids)))
        await session.execute(delete(NotificationPreference).where(NotificationPreference.tenant_id == TENANT_ID, NotificationPreference.user_id.in_(transient_user_ids)))
        await session.execute(delete(Profile).where(Profile.tenant_id == TENANT_ID, Profile.user_id.in_(transient_user_ids)))
        await session.execute(delete(TenantMembership).where(TenantMembership.tenant_id == TENANT_ID, TenantMembership.user_id.in_(transient_user_ids)))
        await session.execute(delete(User).where(User.tenant_id == TENANT_ID, User.id.in_(transient_user_ids)))


async def _seed_marketplace(session) -> dict[str, Any]:
    template = await session.scalar(select(ServiceTemplate).order_by(ServiceTemplate.name).limit(1))
    if template is None:
        raise RuntimeError("service_templates are missing; run `make db.migrate` first")

    slot_floor = round_to_current_slot()
    now = datetime.now(UTC)
    merchant = Merchant(
        id=MERCHANT_ID,
        tenant_id=TENANT_ID,
        user_id=MERCHANT_OWNER_ID,
        name="TrueCare Local QA Wash",
        address="5 Ly Thuong Kiet, Hoan Kiem, Ha Noi",
        phone="+84901234567",
        latitude=21.0285,
        longitude=105.8542,
        bay_count=2,
        operating_hours_start="08:00",
        operating_hours_end="20:00",
        status="live",
        pipeline_status="live_full",
        tags=["fast_lane", "local_qa"],
        rating_average=4.8,
        rating_count=18,
        application_status="approved",
        photo_status="confirmed",
        payment_recipient_status="verified",
        ekyc_status="verified",
        storefront_photo_url="local://merchant/local-qa/storefront.jpg",
        bay_photo_url="local://merchant/local-qa/bay.jpg",
    )
    session.add(merchant)
    await session.flush()
    service = MerchantService(
        id=SERVICE_ID,
        tenant_id=TENANT_ID,
        merchant_id=MERCHANT_ID,
        template_id=template.id,
        name=template.name,
        price=template.floor_price,
        duration_min=template.duration_min,
        duration_max=template.duration_max,
        status="active",
        is_custom=False,
    )
    session.add(service)
    await session.flush()
    session.add(MerchantPaymentSetup(id=MERCHANT_ID, tenant_id=TENANT_ID, merchant_id=MERCHANT_ID, bank_name="VCB", account_number="0123456789", account_holder_name="TRUECARE LOCAL QA", qr_object_key="merchant/local-qa/qr.png", status="verified", verified_at=now, verified_by=OPS_USER_ID))
    for index, kind in enumerate(("cmnd", "selfie", "bank")):
        session.add(MerchantEkycSubmission(id=UUID(f"00000000-0000-0000-0003-0000000000{20 + index}"), tenant_id=TENANT_ID, merchant_id=MERCHANT_ID, kind=kind, object_key=f"merchant/local-qa/ekyc/{kind}.jpg", status="accepted", reviewed_at=now))
    for index in range(3):
        session.add(
            SlotCapacity(
                id=UUID(f"00000000-0000-0000-0003-00000000003{index}"),
                tenant_id=TENANT_ID,
                merchant_id=MERCHANT_ID,
                bay_number=1,
                time_slot=slot_floor + timedelta(minutes=30 * (index + 1)),
                status="available",
            )
        )
    session.add(
        SlotCapacity(
            id=COMPLETED_SLOT_ID,
            tenant_id=TENANT_ID,
            merchant_id=MERCHANT_ID,
            bay_number=2,
            time_slot=slot_floor - timedelta(minutes=60),
            status="available",
        )
    )
    await session.flush()
    session.add(MerchantGoldenHour(id=UUID("00000000-0000-0000-0003-000000000040"), tenant_id=TENANT_ID, merchant_id=MERCHANT_ID, day_of_week=1, start_time="14:00", end_time="16:00", discount_percent=20))
    session.add(PromoCode(id=PROMO_ID, tenant_id=TENANT_ID, code="LOCALQA20", discount_type="fixed", discount_value=20_000, min_order_amount=50_000, usage_limit_total=100, usage_limit_per_user=10, is_active=True, created_by_ops=OPS_USER_ID))
    session.add(Vehicle(id=VEHICLE_ID, tenant_id=TENANT_ID, user_id=CONSUMER_ID, kind="sedan", license_plate="30A-LOCAL", make="Toyota", model="Vios", year=2022, color="white", is_default=True))
    session.add(RewardVoucher(id=VOUCHER_ID, tenant_id=TENANT_ID, user_id=CONSUMER_ID, service_template_id=template.id, stamp_threshold_reached_at=now, expires_at=now + timedelta(days=90), status="issued"))

    completed_booking = Booking(
        id=COMPLETED_BOOKING_ID,
        tenant_id=TENANT_ID,
        user_id=CONSUMER_ID,
        merchant_id=MERCHANT_ID,
        merchant_service_id=SERVICE_ID,
        slot_capacity_id=COMPLETED_SLOT_ID,
        bay_number=2,
        status="rated",
        held_at=now - timedelta(hours=2),
        expires_at=now + timedelta(days=1),
        total_amount=service.price,
        discount_amount=0,
        deposit_amount=0,
        idempotency_key="local-qa-completed-booking",
        check_in_token="LOCALQACHECKIN",
        checked_in_at=now - timedelta(hours=2),
        service_completed_at=now - timedelta(hours=1, minutes=30),
        completed_at=now - timedelta(hours=1),
        payment_method="cash",
        payment_status="verified",
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(hours=1),
    )
    session.add(completed_booking)
    session.add(Payment(id=COMPLETED_PAYMENT_ID, tenant_id=TENANT_ID, booking_id=COMPLETED_BOOKING_ID, amount=service.price, method="cash", status="verified", merchant_confirmed_at=now - timedelta(hours=1), commission_amount=0, commission_status="not_applicable", idempotency_key="local-qa-completed-payment"))
    session.add(Rating(id=COMPLETED_RATING_ID, tenant_id=TENANT_ID, booking_id=COMPLETED_BOOKING_ID, user_id=CONSUMER_ID, merchant_id=MERCHANT_ID, rating="positive", comment="Fixture completed booking"))
    session.add(RewardStamp(booking_id=COMPLETED_BOOKING_ID, tenant_id=TENANT_ID, user_id=CONSUMER_ID, status="finalized", finalized_at=now - timedelta(hours=1)))
    session.add(Complaint(id=COMPLAINT_ID, tenant_id=TENANT_ID, booking_id=COMPLETED_BOOKING_ID, user_id=CONSUMER_ID, merchant_id=MERCHANT_ID, category="service_quality", description="Fixture complaint for local Ops QA", evidence_refs=[], status="created"))
    session.add(DataExportJob(id=UUID("00000000-0000-0000-0003-000000000050"), tenant_id=TENANT_ID, user_id=OPS_USER_ID, status="completed", bundle_url="local://exports/ops/local-fixture.csv", expires_at=now + timedelta(days=7), completed_at=now))

    return {
        "service_template_id": str(template.id),
        "next_slot_time": (slot_floor + timedelta(minutes=30)).isoformat(),
    }


async def _issue_tokens(session, users: dict[str, User]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    auth = AuthService(session)
    for persona, user in users.items():
        pair = await auth.issue_token_pair(user, locale="vi")
        result[persona] = {
            "identifier": PERSONAS[persona]["email"],
            "password": PASSWORD,
            "user_id": str(user.id),
            "tenant_id": str(TENANT_ID),
            "roles": [PERSONAS[persona]["role"]],
            "access_token": pair["access_token"],
            "refresh_token": pair["refresh_token"],
        }
    return result


async def seed() -> dict[str, Any]:
    async with get_sessionmaker()() as session:
        async with session.begin():
            tenant = await session.get(Tenant, TENANT_ID)
            if tenant is None:
                session.add(Tenant(id=TENANT_ID, name="TrueCare Pilot"))
                await session.flush()
            await set_local_context(session, tenant_id=TENANT_ID, user_id=OPS_USER_ID, role="admin")
            users = {
                persona: await _upsert_user(
                    session,
                    user_id=data["id"],
                    email=data["email"],
                    name=data["name"],
                    role=data["role"],
                )
                for persona, data in PERSONAS.items()
            }
            await _clear_fixture_rows(session)
            seed_ids = await _seed_marketplace(session)
            tokens = await _issue_tokens(session, users)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "api_base_url": "http://127.0.0.1:8000",
        "ops_web_url": "http://127.0.0.1:5173",
        "mobile_env": "EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000",
        "personas": tokens,
        "ids": {
            "tenant_id": str(TENANT_ID),
            "merchant_id": str(MERCHANT_ID),
            "merchant_service_id": str(SERVICE_ID),
            "fixture_booking_id": str(COMPLETED_BOOKING_ID),
            "fixture_payment_id": str(COMPLETED_PAYMENT_ID),
            "fixture_complaint_id": str(COMPLAINT_ID),
            "fixture_voucher_id": str(VOUCHER_ID),
            "promo_code": "LOCALQA20",
            **seed_ids,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic local E2E QA personas and fixture data.")
    parser.add_argument("--out", default=".local-e2e.json")
    args = parser.parse_args()

    artifact = asyncio.run(seed())
    output = Path(args.out)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    output.chmod(0o600)
    print(f"ok: wrote {output}")
    print("personas: consumer=qa.consumer@truecare.local, merchant=qa.merchant@truecare.local, ops=qa.ops@truecare.local")
    print(f"merchant_id={artifact['ids']['merchant_id']} service_id={artifact['ids']['merchant_service_id']}")


if __name__ == "__main__":
    main()
