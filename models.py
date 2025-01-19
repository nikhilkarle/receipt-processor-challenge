from __future__ import annotations

from datetime import date, time
from typing import List

from pydantic import BaseModel, Field, constr


class Item(BaseModel):
    """
    Represents an item in a receipt with a short description and price.

    Attributes:
        shortDescription (str): A short description of the product.
        price (str): The price paid for the item. It should be in the format of a string representing a decimal number.
    """
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
    """
    Represents a receipt that contains details about the purchase including retailer name, 
    purchase date and time, items, and total price.

    Attributes:
        retailer (str): The name of the retailer or store where the receipt is from.
        purchaseDate (date): The date the purchase was made.
        purchaseTime (time): The time the purchase was made (in 24-hour format).
        items (List[Item]): A list of items included in the receipt.
        total (str): The total amount paid, formatted as a string representing a decimal number.
    """
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
    """
    Represents the response for points calculation based on a receipt.

    Attributes:
        points (int): The total points earned for a purchase based on the receipt.
    """
    points: int


class ErrorResponse(BaseModel):
    """
    Represents an error response when a request fails.

    Attributes:
        detail (str): The detail of the error message explaining what went wrong.
    """
    detail: str
