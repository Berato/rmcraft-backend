"""Schemas for theme triage workflow"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal


class IssueIdentification(BaseModel):
    """Output schema for triage agent identifying issues"""
    issue_description: str = Field(
        description="Clear description of the visual/layout problem observed in the PDF"
    )
    severity: Literal["critical", "major", "minor"] = Field(
        description="Severity level of the issue"
    )
    code_location: str = Field(
        description="Where in the theme code this issue likely originates (e.g., 'header section of template', 'CSS .summary-text class')"
    )
    suggested_fix: str = Field(
        description="High-level suggestion for how to fix this issue"
    )


class TriageAnalysisOutput(BaseModel):
    """Complete output from a triage agent analyzing a PDF"""
    issues: List[IssueIdentification] = Field(
        description="List of all issues identified in the PDF"
    )
    overall_assessment: str = Field(
        description="2-3 sentence summary of the overall quality and main problems"
    )


class ThemeCodeUpdate(BaseModel):
    """Output schema for engineer agent fixing theme code"""
    template: str = Field(
        description="Complete fixed Jinja2 template code"
    )
    styles: str = Field(
        description="Complete fixed CSS code"
    )
    fixes_applied: List[str] = Field(
        description="List of specific fixes applied to address identified issues"
    )


class VerificationResult(BaseModel):
    """Output schema for verification agent"""
    all_issues_resolved: bool = Field(
        description="True if all original issues appear to be fixed in the new PDF"
    )
    remaining_issues: List[str] = Field(
        description="List of issues that are still present (empty if all resolved)"
    )
    new_issues: List[str] = Field(
        description="List of any new issues introduced by the fixes"
    )
    recommendation: str = Field(
        description="Recommendation: 'approve' if good, 'retry' if fixable, 'manual_review' if complex"
    )


class ThemeTriageRequest(BaseModel):
    """Request schema for theme triage endpoint"""
    theme_id: str
    max_retries: Optional[int] = Field(default=1, ge=0, le=3)
    
    @validator('max_retries')
    def validate_retries(cls, v):
        if v > 3:
            raise ValueError("max_retries cannot exceed 3")
        return v


class ThemeTriageResponse(BaseModel):
    """Response schema for theme triage endpoint"""
    status: int
    message: str
    data: dict
