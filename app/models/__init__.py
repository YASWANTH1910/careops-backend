# Import all models to ensure they're registered with SQLAlchemy Base
# Business MUST be imported first — all other models FK into it
from app.models.business import Business, BusinessPlan
from app.models.user import User, UserRole
from app.models.contact import Contact
from app.models.booking import Booking, BookingStatus, FormStatus
from app.models.inventory import Inventory
from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.message import Message, MessageChannel, MessageDirection, MessageStatus
from app.models.form import Form, FormSubmission, FormStatus as FormTemplateStatus
from app.models.service import Service

__all__ = [
    "Business",
    "BusinessPlan",
    "User",
    "UserRole",
    "Contact",
    "Booking",
    "BookingStatus",
    "FormStatus",
    "Inventory",
    "Alert",
    "AlertType",
    "AlertSeverity",
    "Message",
    "MessageChannel",
    "MessageDirection",
    "MessageStatus",
    "Form",
    "FormSubmission",
    "FormTemplateStatus",
    "Service",
]
