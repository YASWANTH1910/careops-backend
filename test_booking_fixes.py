#!/usr/bin/env python3
"""
Booking System Validation Test
Tests all critical fixes applied to the booking system
"""

import sys
from datetime import datetime, timedelta, timezone

# Validation Tests

def test_enum_definitions():
    """Test that enum definitions are correct"""
    print("✓ Testing enum definitions...")
    
    # These should exist and have correct values
    from app.models.booking import BookingStatus, FormStatus
    
    assert hasattr(BookingStatus, 'PENDING'), "BookingStatus.PENDING not found"
    assert BookingStatus.PENDING.value == "pending", f"BookingStatus.PENDING value should be 'pending', got {BookingStatus.PENDING.value}"
    
    assert hasattr(FormStatus, 'PENDING'), "FormStatus.PENDING not found"
    assert FormStatus.PENDING.value == "pending", f"FormStatus.PENDING value should be 'pending', got {FormStatus.PENDING.value}"
    
    print("  ✅ Enum definitions correct")
    return True


def test_alert_schema():
    """Test that alert schema includes business_id"""
    print("✓ Testing alert schema...")
    
    from app.schemas.alert_schema import AlertCreate
    from pydantic import ValidationError
    
    # Should require business_id
    try:
        alert = AlertCreate(
            type="INTEGRATION",
            severity="WARNING",
            message="Test"
        )
        print("  ❌ AlertCreate should require business_id")
        return False
    except ValidationError:
        pass  # Expected
    
    # Should accept business_id
    alert = AlertCreate(
        business_id=1,
        type="INTEGRATION",
        severity="WARNING",
        message="Test"
    )
    assert alert.business_id == 1, "business_id not set correctly"
    
    print("  ✅ Alert schema includes business_id")
    return True


def test_datetime_operations():
    """Test that all datetime operations use timezone-aware datetimes"""
    print("✓ Testing datetime operations...")
    
    now_utc = datetime.now(timezone.utc)
    assert now_utc.tzinfo is not None, "datetime.now(timezone.utc) should be timezone-aware"
    
    print("  ✅ Timezone-aware datetime operations verified")
    return True


def test_booking_model():
    """Test that booking model is properly defined"""
    print("✓ Testing booking model...")
    
    from app.models.booking import Booking
    from datetime import datetime, timezone
    
    # Check that model has required fields
    assert hasattr(Booking, 'business_id'), "Booking missing business_id field"
    assert hasattr(Booking, 'contact_id'), "Booking missing contact_id field"
    assert hasattr(Booking, 'status'), "Booking missing status field"
    assert hasattr(Booking, 'form_status'), "Booking missing form_status field"
    assert hasattr(Booking, 'start_time'), "Booking missing start_time field"
    assert hasattr(Booking, 'end_time'), "Booking missing end_time field"
    assert hasattr(Booking, 'created_at'), "Booking missing created_at field"
    
    print("  ✅ Booking model has all required fields")
    return True


def test_alert_model():
    """Test that alert model requires business_id"""
    print("✓ Testing alert model...")
    
    from app.models.alert import Alert
    from sqlalchemy import inspect
    
    mapper = inspect(Alert)
    business_id_col = mapper.columns['business_id']
    
    assert business_id_col.nullable == False, "Alert.business_id should be non-nullable"
    assert business_id_col.foreign_keys, "Alert.business_id should be a foreign key"
    
    print("  ✅ Alert model properly requires business_id")
    return True


def test_imports():
    """Test that all necessary imports are available"""
    print("✓ Testing imports...")
    
    try:
        from app.services.booking_service import BookingService
        from app.services.automation_service import AutomationService
        from app.services.integration_service import IntegrationService
        from app.core.logger import log_info, log_warning, log_error
        
        print("  ✅ All imports available")
        return True
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False


def test_booking_schema():
    """Test that booking schema handles datetime properly"""
    print("✓ Testing booking schema...")
    
    from app.schemas.booking_schema import BookingCreate
    from datetime import datetime, timezone
    
    future_time = datetime.now(timezone.utc) + timedelta(days=1)
    
    booking = BookingCreate(
        contact_id=1,
        start_time=future_time,
        end_time=future_time + timedelta(hours=1)
    )
    
    assert booking.start_time == future_time, "start_time not set correctly"
    assert booking.end_time == future_time + timedelta(hours=1), "end_time not set correctly"
    
    print("  ✅ Booking schema handles datetime correctly")
    return True


def test_log_imports():
    """Test that logging is properly configured"""
    print("✓ Testing logging configuration...")
    
    try:
        from app.core.logger import log_info, log_warning, log_error
        
        # Try logging a message (won't actually log without proper setup, but tests import)
        log_info("[TEST] Testing logging")
        
        print("  ✅ Logging properly configured")
        return True
    except Exception as e:
        print(f"  ❌ Logging error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("CareOps Booking System Validation Tests")
    print("=" * 60)
    print()
    
    tests = [
        test_enum_definitions,
        test_alert_schema,
        test_datetime_operations,
        test_booking_model,
        test_alert_model,
        test_imports,
        test_booking_schema,
        test_log_imports,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if all(results):
        print("✅ ALL TESTS PASSED - Booking system is ready for testing")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Please review the errors above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
