"""
Form Service — Business logic for form and form submission management.

Multi-tenant isolation ensures all queries filter by business_id.
"""
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List
from app.models.form import Form, FormSubmission
from app.schemas.form_schema import FormCreate, FormUpdate, FormSubmissionCreate, FormSubmissionUpdate
from app.core.logger import log_info


class FormService:
    """Service for managing forms and submissions with multi-tenant isolation."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ─────────────────────────────────────────────────────────────────────────
    # FORM MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_form(self, form_data: FormCreate, business_id: int) -> Form:
        """
        Create a new form template.
        
        Admin-only: business_id is from authenticated admin.
        
        Args:
            form_data: FormCreate schema
            business_id: Tenant ID from authenticated admin
            
        Returns:
            Created Form model
            
        Multi-tenant isolation: form is created with business_id.
        """
        log_info(f"[SERVICE] Creating form: {form_data.title} for business {business_id}")
        
        form = Form(
            business_id=business_id,
            title=form_data.title,
            description=form_data.description,
            fields=[f.model_dump() for f in form_data.fields],
            status=form_data.status,
        )
        self.db.add(form)
        self.db.commit()
        self.db.refresh(form)
        
        log_info(f"[SERVICE] Form created: id={form.id}")
        return form
    
    def get_forms(self, business_id: int, skip: int = 0, limit: int = 100) -> List[Form]:
        """
        Get all forms for a business.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Form).filter(
            Form.business_id == business_id
        ).offset(skip).limit(limit).all()
    
    def get_form(self, form_id: int, business_id: int) -> Form:
        """
        Get a form by ID, scoped to business_id.
        
        Returns None if form doesn't exist or belongs to another tenant.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(Form).filter(
            Form.id == form_id,
            Form.business_id == business_id
        ).first()
    
    def update_form(self, form_id: int, form_data: FormUpdate, business_id: int) -> Form:
        """
        Update a form, scoped to business_id.
        
        Admin-only.
        Raises ValueError if form not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Updating form {form_id} for business {business_id}")
        
        form = self.get_form(form_id, business_id)
        if not form:
            raise ValueError(f"Form {form_id} not found")
        
        if form_data.title is not None:
            form.title = form_data.title
        if form_data.description is not None:
            form.description = form_data.description
        if form_data.fields is not None:
            form.fields = [f.model_dump() for f in form_data.fields]
        if form_data.status is not None:
            form.status = form_data.status
        
        form.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(form)
        
        log_info(f"[SERVICE] Form updated: id={form.id}")
        return form
    
    def delete_form(self, form_id: int, business_id: int) -> bool:
        """
        Delete a form, scoped to business_id.
        
        Admin-only.
        Returns True if deleted, False if not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Deleting form {form_id} for business {business_id}")
        
        form = self.get_form(form_id, business_id)
        if not form:
            return False
        
        self.db.delete(form)
        self.db.commit()
        
        log_info(f"[SERVICE] Form deleted: id={form_id}")
        return True
    
    # ─────────────────────────────────────────────────────────────────────────
    # FORM SUBMISSION MANAGEMENT
    # ─────────────────────────────────────────────────────────────────────────
    
    def create_submission(
        self,
        submission_data: FormSubmissionCreate,
        business_id: int
    ) -> FormSubmission:
        """
        Create a new form submission.
        
        Args:
            submission_data: FormSubmissionCreate schema
            business_id: Tenant ID
            
        Returns:
            Created FormSubmission model
            
        Multi-tenant isolation: submission is created with business_id.
        """
        log_info(f"[SERVICE] Creating form submission for business {business_id}")
        
        submission = FormSubmission(
            **submission_data.model_dump(),
            business_id=business_id
        )
        self.db.add(submission)
        self.db.commit()
        self.db.refresh(submission)
        
        log_info(f"[SERVICE] Submission created: id={submission.id}")
        return submission
    
    def get_submissions(self, business_id: int, skip: int = 0, limit: int = 100) -> List[FormSubmission]:
        """
        Get all submissions for a business.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(FormSubmission).filter(
            FormSubmission.business_id == business_id
        ).order_by(FormSubmission.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_submissions_for_form(
        self,
        form_id: int,
        business_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[FormSubmission]:
        """
        Get all submissions for a specific form.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(FormSubmission).filter(
            FormSubmission.form_id == form_id,
            FormSubmission.business_id == business_id
        ).order_by(FormSubmission.created_at.desc()).offset(skip).limit(limit).all()
    
    def get_submission(self, submission_id: int, business_id: int) -> FormSubmission:
        """
        Get a submission by ID, scoped to business_id.
        
        Returns None if submission doesn't exist or belongs to another tenant.
        
        Multi-tenant isolation: filtered by business_id.
        """
        return self.db.query(FormSubmission).filter(
            FormSubmission.id == submission_id,
            FormSubmission.business_id == business_id
        ).first()
    
    def update_submission(
        self,
        submission_id: int,
        submission_data: FormSubmissionUpdate,
        business_id: int
    ) -> FormSubmission:
        """
        Update a submission, scoped to business_id.
        
        Raises ValueError if submission not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Updating submission {submission_id} for business {business_id}")
        
        submission = self.get_submission(submission_id, business_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        # Update fields that are set
        update_data = submission_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(submission, field, value)
        
        self.db.commit()
        self.db.refresh(submission)
        
        log_info(f"[SERVICE] Submission updated: id={submission.id}")
        return submission
    
    def mark_submission_complete(self, submission_id: int, business_id: int) -> FormSubmission:
        """
        Mark a submission as complete.
        
        Admin-only.
        Raises ValueError if submission not found.
        
        Multi-tenant isolation: filtered by business_id.
        """
        log_info(f"[SERVICE] Marking submission {submission_id} as complete for business {business_id}")
        
        submission = self.get_submission(submission_id, business_id)
        if not submission:
            raise ValueError(f"Submission {submission_id} not found")
        
        submission.status = "completed"
        self.db.commit()
        self.db.refresh(submission)
        
        return submission
