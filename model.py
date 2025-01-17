from __future__ import annotations

from datetime import date, time
from typing import List

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, RootModel, constr, field_validator


class Item(BaseModel):
    shortDescription: constr() = Field( 
        ...,
        description="The Short Product Description for the item.",
        example="Mountain Dew 12PK",
        pattern=r"^[\w\s\-]+$",  
    )
    price: constr() = Field(
        ...,
        description="The total price paid for this item.",
        example="6.49",
        pattern=r"^\d+\.\d{2}$",
    )


class Receipt(BaseModel):
    retailer: constr() = Field(
        ...,
        description="The name of the retailer or store the receipt is from.",
        example="M&M Corner Market",
        pattern=r"^[\w\s\-&]+$", 
    )
    purchaseDate: date = Field(
        ...,
        description="The date of the purchase printed on the receipt.",
        example="2022-01-01",
    )
    purchaseTime: time = Field(
        ...,
        description="The time of the purchase printed on the receipt. 24-hour time expected.",
        example="13:01",
    )
    items: List[Item] = Field(..., min_items=1)
    total: constr() = Field(
        ...,
        description="The total amount paid on the receipt.",
        example="6.49",
        pattern=r"^\d+\.\d{2}$",
    )


class PointsResponse(BaseModel):
    points: int


class ErrorResponse(BaseModel):
    detail: str
