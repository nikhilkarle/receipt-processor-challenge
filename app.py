from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import date, time
from typing import List

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, constr

from model import ErrorResponse, PointsResponse, Receipt


app = FastAPI()

logging.basicConfig(
    filename="receipts.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

receipts_db = {}

def load_config() -> dict:
    """
    Load configuration data from the config.json file.

    Returns:
        dict: The loaded configuration as a dictionary.
    """
    with open("config.json") as config_file:
        return json.load(config_file)


config = load_config()

def calculate_points(receipt: Receipt) -> int:
    """
    Calculate points based on the receipt data according to specific rules.
    Multiplier values are loaded from a config file.

    Args:
        receipt (Receipt): The receipt object containing the data to calculate points.

    Returns:
        int: The total points calculated based on the rules.
    """
    points = 0
    retailer_name = receipt.retailer
    points += (
        sum(c.isalnum() for c in retailer_name) * config["retailer_name_multiplier"]
    )
    logging.debug("After Rule 1 (retailer name): %d points", points)

    total = float(receipt.total)
    if total.is_integer():
        points += config["round_dollar_bonus"]
    logging.debug("After Rule 2 (round dollar): %d points", points)

    if total % 0.25 == 0:
        points += config["multiple_of_025_bonus"]
    logging.debug("After Rule 3 (multiple of 0.25): %d points", points)

    num_items = len(receipt.items)
    points += (num_items // 2) * config["items_bonus_per_two"]
    logging.debug("After Rule 4 (two items): %d points", points)

    for item in receipt.items:
        trimmed_description = item.shortDescription.strip()
        if len(trimmed_description) % 3 == 0:
            item_price = float(item.price)
            points += math.ceil(item_price * config["item_description_multiplier"])
    logging.debug("After Rule 5 (item description): %d points", points)

    #Rule 6: Haha, good try!

    purchase_date = receipt.purchaseDate
    day = purchase_date.day  
    if day % 2 != 0:
        points += config["odd_day_bonus"]
    logging.debug("After Rule 7 (odd day): %d points", points)

    purchase_time = receipt.purchaseTime
    if 14 <= purchase_time.hour < 16:
        points += config["time_bonus"]
    logging.debug("After Rule 8 (time between 2-4pm): %d points", points)

    return points


@app.exception_handler(RequestValidationError)
async def custom_request_validation_exception_handler(request, exc):
    """
    Custom handler for validation errors.

    Args:
        request: The incoming request.
        exc: The exception raised.

    Returns:
        JSONResponse: The error response.
    """
    logging.error("Validation error: %s", exc)
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid structure or missing fields in the input."},
    )


@app.post("/receipts/process", response_model=ErrorResponse)
async def process_receipt(receipt: Receipt) -> JSONResponse:
    """
    Process a new receipt, generate a unique receipt ID, and store the receipt data.

    Args:
        receipt (Receipt): The receipt data to be processed.

    Returns:
        JSONResponse: A response containing the unique receipt ID.
    """
    try:
        receipt_id = str(uuid.uuid4())
        receipt_dict = receipt.dict()
        receipt_dict["id"] = receipt_id

        # Store the receipt in the 'database'
        receipts_db[receipt_id] = receipt_dict

        # Log the receipt processing
        logging.info("Receipt processed with ID: %s", receipt_id)

        # Return the receipt ID
        return JSONResponse(status_code=200, content={"id": receipt_id})

    except Exception as e:
        logging.error("Error processing receipt: %s", e)
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid structure or missing fields in the input."},
        )


@app.get("/receipts/{receipt_id}/points", response_model=PointsResponse)
async def get_points(receipt_id: str) -> PointsResponse:
    """
    Get the points for a specific receipt based on the receipt ID.

    Args:
        receipt_id (str): The unique ID of the receipt.

    Returns:
        PointsResponse: A response model containing the calculated points.

    Raises:
        HTTPException: If the receipt ID does not exist in the database.
    """
    if receipt_id not in receipts_db:
        logging.error("Receipt not found with ID: %s", receipt_id)
        return JSONResponse(
            status_code=404,
            content={"detail": f"Receipt with ID {receipt_id} not found."},
        )

    receipt = Receipt(**receipts_db[receipt_id])
    total_points = calculate_points(receipt)

    logging.info("Points calculated for receipt ID %s: %d points", receipt_id, total_points)

    return PointsResponse(points=total_points)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
