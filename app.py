from __future__ import annotations

import logging
import math
import uuid
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from config import CONFIG
from models import ErrorResponse, PointsResponse, Receipt

app = FastAPI()

handler = RotatingFileHandler(
    filename="logs.out",  
    maxBytes=1024*1024,  
    backupCount=3,
)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("ReceiptLogger")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

receipts_db = {}

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
    for c in retailer_name:
        if c.isalnum():
            points += CONFIG["retailer_name_multiplier"]
    # points += sum(c.isalnum() for c in retailer_name) * CONFIG["retailer_name_multiplier"]
    logger.debug("After Rule 1 (retailer name): %d points", points)

    total = float(receipt.total)
    if total.is_integer():
        points += CONFIG["round_dollar_bonus"]
    logger.debug("After Rule 2 (round dollar): %d points", points)

    if total % 0.25 == 0:
        points += CONFIG["multiple_of_025_bonus"]
    logger.debug("After Rule 3 (multiple of 0.25): %d points", points)

    num_items = len(receipt.items)
    points += (num_items // 2) * CONFIG["items_bonus_per_two"]
    logger.debug("After Rule 4 (two items): %d points", points)

    for item in receipt.items:
        trimmed_description = item.shortDescription.strip()
        if len(trimmed_description) % 3 == 0:
            item_price = float(item.price)
            points += math.ceil(item_price * CONFIG["item_description_multiplier"])
    logger.debug("After Rule 5 (item description): %d points", points)

    #Rule 6: Haha, good try!

    purchase_date = receipt.purchaseDate
    day = purchase_date.day
    if day % 2 != 0:
        points += CONFIG["odd_day_bonus"]
    logger.debug("After Rule 7 (odd day): %d points", points)

    purchase_time = receipt.purchaseTime
    if 14 <= purchase_time.hour < 16:
        points += CONFIG["time_bonus"]
    logger.debug("After Rule 8 (time between 2-4pm): %d points", points)

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
    logger.error("Validation error: %s", exc)
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
    # try:
    receipt_id = str(uuid.uuid4())
    receipt_dict = receipt.model_dump()
    receipt_dict["id"] = receipt_id

    receipts_db[receipt_id] = receipt_dict

    logger.info("Received receipt: %s", receipt_dict)

    logger.info("Receipt processed with ID: %s", receipt_id)

    return JSONResponse(status_code=200, content={"id": receipt_id})

    # except ValidationError as e:
    #     # Catch Pydantic validation errors and return a 400 response
    #     logger.error("Validation error: %s", e)
    #     raise HTTPException(
    #         status_code=400,
    #         detail="Invalid receipt structure or missing fields."
    #     )


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
        logger.error("Receipt not found with ID: %s", receipt_id)
        return JSONResponse(
            status_code=404,
            content={"detail": f"Receipt with ID {receipt_id} not found."},
        )

    receipt = Receipt(**receipts_db[receipt_id])
    total_points = calculate_points(receipt)

    logger.info("Points calculated for receipt ID %s: %d points", receipt_id, total_points)

    return PointsResponse(points=total_points)