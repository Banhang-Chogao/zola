"""Pydantic models for Paywall API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class AccessRequestIn(BaseModel):
    post_id: str = Field(min_length=1, max_length=120)
    post_title: str = Field(min_length=1, max_length=300)
    post_url: str = Field(min_length=1, max_length=500)
    email: EmailStr
    payment_note: str = Field(default="", max_length=500)


class AccessRequestOut(BaseModel):
    request_id: str
    status: Literal["pending", "approved", "rejected"]


class UnlockIn(BaseModel):
    post_id: str = Field(min_length=1, max_length=120)
    email: EmailStr
    approve_code: str = Field(min_length=4, max_length=64)


class UnlockOut(BaseModel):
    access_token: str
    expires_at: str
    trace_code: str
    reader_email_hash: str


class GenerateCodeIn(BaseModel):
    post_id: str = Field(min_length=1, max_length=120)
    post_url: str = Field(min_length=1, max_length=500)
    post_title: str = Field(default="", max_length=300)
    email: EmailStr
    expires_days: int = Field(default=7, ge=1, le=3650)
    max_usage: int = Field(default=5, ge=1, le=1000)
    approve_code: str | None = Field(default=None, max_length=64)
    request_id: str | None = None


class GenerateCodeOut(BaseModel):
    code_id: str
    approve_code: str
    expires_at: str


class SendEmailIn(BaseModel):
    code_id: str
    post_title: str = Field(min_length=1, max_length=300)
    post_url: str = Field(min_length=1, max_length=500)


class ContentOut(BaseModel):
    post_id: str
    html: str
    trace_code: str
    reader_email_hash: str