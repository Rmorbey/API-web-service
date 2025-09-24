#!/usr/bin/env python3
"""
Pydantic models for Fundraising API
Defines request and response models for type safety and validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class Donation(BaseModel):
    """Individual donation data"""
    donor_name: str = Field(..., description="Name of the donor")
    amount: float = Field(..., ge=0, description="Donation amount in pounds")
    message: str = Field(default="", description="Donor message")
    date: str = Field(..., description="When the donation was made")
    scraped_at: datetime = Field(..., description="When this data was scraped")


class FundraisingDataResponse(BaseModel):
    """Response model for fundraising data endpoint"""
    timestamp: datetime = Field(..., description="When the data was last updated")
    total_raised: float = Field(..., ge=0, description="Total amount raised in pounds")
    target_amount: float = Field(..., ge=0, description="Fundraising target in pounds")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage")
    donations: List[Donation] = Field(..., description="List of individual donations")
    total_donations: int = Field(..., ge=0, description="Total number of donations")
    last_updated: datetime = Field(..., description="Last update timestamp")
    justgiving_url: str = Field(..., description="JustGiving page URL")


class DonationsResponse(BaseModel):
    """Response model for donations-only endpoint"""
    donations: List[Donation] = Field(..., description="List of individual donations")
    total_donations: int = Field(..., ge=0, description="Total number of donations")
    last_updated: datetime = Field(..., description="Last update timestamp")


class HealthResponse(BaseModel):
    """Response model for health check endpoint"""
    project: str = Field(..., description="Project name")
    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    scraper_running: bool = Field(..., description="Whether scraper is running")
    last_scrape: Optional[datetime] = Field(None, description="Last scrape timestamp")
    cache_status: str = Field(..., description="Cache status")


class RefreshResponse(BaseModel):
    """Response model for refresh endpoint"""
    success: bool = Field(..., description="Whether refresh was successful")
    message: str = Field(..., description="Refresh result message")
    timestamp: datetime = Field(..., description="Refresh timestamp")
    total_raised: Optional[float] = Field(None, description="Total raised after refresh")
    donations_count: Optional[int] = Field(None, description="Number of donations after refresh")


class CleanupResponse(BaseModel):
    """Response model for cleanup endpoint"""
    success: bool = Field(..., description="Whether cleanup was successful")
    message: str = Field(..., description="Cleanup result message")
    timestamp: datetime = Field(..., description="Cleanup timestamp")
    backups_removed: Optional[int] = Field(None, description="Number of old backups removed")


class ProjectInfoResponse(BaseModel):
    """Response model for project root endpoint"""
    project: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    version: str = Field(..., description="Project version")
    endpoints: Dict[str, str] = Field(..., description="Available endpoints")
    source: str = Field(..., description="Data source")
    scrape_interval: str = Field(..., description="Scraping interval")
