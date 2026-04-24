"""
Forms Routes — CareOps SaaS

Security patterns used in this router:

  Pattern 1 — Admin-only route (require_admin):
    POST /forms              → only admin can create form templates
    PATCH /forms/{id}        → only admin can modify form templates
    DELETE /forms/{id}       → only admin can delete form templates
    PATCH /submissions/{id}  → admin marks submission complete

  Pattern 2 — Admin-only submission:
    POST /forms/{id}/submit  → admin can submit forms

  Pattern 3 — Business-filtered route (get_current_user + business_id filter):
    GET /forms               → any authenticated user sees only their business's forms
    GET /forms/{id}          → only if form belongs to current business
    GET /submissions         → only submissions from current business

All query filters include: Model.business_id == current_user.business_id
This guarantees zero cross-tenant data leaks.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.logger import log_info
from app.dependencies.auth_dependency import get_current_user, require_admin
from app.models.user import User
from app.schemas.form_schema import (
    FormCreate, FormUpdate, FormResponse,
    FormSubmissionCreate, FormSubmissionUpdate, FormSubmissionResponse,
)
from app.services.form_service import FormService

router = APIRouter(prefix="/forms", tags=["Forms"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATTERN 1: Admin-only routes (require_admin)
# Only the business admin can manage form templates.
# Non-admin users get: 403 "Admin access required."
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("", response_model=FormResponse, status_code=status.HTTP_201_CREATED)
def create_form(
    payload: FormCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # ← ADMIN ONLY
):
    """
    [ADMIN ONLY] Create a new form template for this business.

    business_id is taken from the admin's JWT — cannot be spoofed.
    """
    service = FormService(db)
    form = service.create_form(payload, business_id=admin.business_id)
    return FormResponse.model_validate(form)


@router.patch("/{form_id}", response_model=FormResponse)
def update_form(
    form_id: int,
    payload: FormUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # ← ADMIN ONLY
):
    """[ADMIN ONLY] Update a form template. Scoped to current business."""
    service = FormService(db)
    try:
        form = service.update_form(form_id, payload, business_id=admin.business_id)
        return FormResponse.model_validate(form)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/{form_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_form(
    form_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # ← ADMIN ONLY
):
    """[ADMIN ONLY] Delete a form template and all its submissions."""
    service = FormService(db)
    deleted = service.delete_form(form_id, business_id=admin.business_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form {form_id} not found"
        )
    log_info(f"[Forms] Form {form_id} deleted by admin {admin.id}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATTERN 2: Admin-only form submission
# Only admins can submit form responses.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/{form_id}/submit", response_model=FormSubmissionResponse, status_code=status.HTTP_201_CREATED)
def submit_form(
    form_id: int,
    payload: FormSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),  # ← ADMIN ONLY
):
    """
    [ADMIN ONLY] Submit answers to a form.

    - Admin: always allowed.
    - Non-admin: 403 "Admin access required."
    """
    service = FormService(db)
    
    # Verify form belongs to this business (cross-tenant guard)
    form = service.get_form(form_id, business_id=current_user.business_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form {form_id} not found"
        )
    
    submission = service.create_submission(payload, business_id=current_user.business_id)
    log_info(f"[Forms] Submission created: form={form_id}, by user={current_user.id}")
    return FormSubmissionResponse.model_validate(submission)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PATTERN 3: Business-filtered routes (get_current_user + business_id filter)
# Any authenticated user (admin or user) can read, but only sees
# data from their own business. Cross-tenant data is invisible.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("", response_model=List[FormResponse])
def list_forms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),  # ← BUSINESS FILTER ONLY
):
    """
    [get_current_user] List all forms for the current business.

    business_id filter ensures an admin or user from Business A
    can NEVER see forms from Business B, even if they guess the IDs.
    """
    service = FormService(db)
    forms = service.get_forms(business_id=current_user.business_id)
    return [FormResponse.model_validate(f) for f in forms]


@router.get("/{form_id}", response_model=FormResponse)
def get_form(
    form_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[get_current_user] Get a specific form — only if it belongs to current business."""
    service = FormService(db)
    form = service.get_form(form_id, business_id=current_user.business_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form {form_id} not found"
        )
    return FormResponse.model_validate(form)


@router.get("/{form_id}/submissions", response_model=List[FormSubmissionResponse])
def list_submissions(
    form_id: int,
    contact_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    [get_current_user] List all submissions for a form.

    Optional filter by contact_id.
    Scoped to current business — submissions from other businesses are invisible.
    """
    service = FormService(db)
    
    # First verify the form itself belongs to this business
    form = service.get_form(form_id, business_id=current_user.business_id)
    if not form:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Form {form_id} not found"
        )
    
    submissions = service.get_submissions_for_form(
        form_id=form_id,
        business_id=current_user.business_id
    )
    
    # Optional client-side filter by contact_id
    if contact_id:
        submissions = [s for s in submissions if s.contact_id == contact_id]
    
    return [FormSubmissionResponse.model_validate(s) for s in submissions]


@router.patch("/submissions/{submission_id}", response_model=FormSubmissionResponse)
def update_submission(
    submission_id: int,
    payload: FormSubmissionUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),  # ← ADMIN ONLY
):
    """[ADMIN ONLY] Update a form submission — e.g., mark as complete."""
    service = FormService(db)
    try:
        submission = service.update_submission(
            submission_id,
            payload,
            business_id=admin.business_id
        )
        return FormSubmissionResponse.model_validate(submission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
