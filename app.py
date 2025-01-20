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

LOGFILEPATH = "./logs/logs.out"

handler = RotatingFileHandler(
    filename=LOGFILEPATH,
    maxBytes=1024 * 1024,
    backupCount=3,
)

formatter = logging.Formatter("%(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("ReceiptLogger")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

receiptsDb = {}

def calculatePoints(receipt: Receipt) -> int:
    """
    Calculate points based on the receipt data according to specific rules.
    Multiplier values are loaded from a config file.

    Args:
        receipt (Receipt): The receipt object containing the data to calculate points.

    Returns:
        int: The total points calculated based on the rules.
    """
    points = 0
    retailerName = receipt.retailer
    for c in retailerName:
        if c.isalnum():
            points += CONFIG["retailerNameMultiplier"]
    logger.debug("After Rule 1 (retailer name): %d points", points)

    total = float(receipt.total)
    if total.is_integer():
        points += CONFIG["roundDollarBonus"]
    logger.debug("After Rule 2 (round dollar): %d points", points)

    if total % 0.25 == 0:
        points += CONFIG["multipleOf025Bonus"]
    logger.debug("After Rule 3 (multiple of 0.25): %d points", points)

    numItems = len(receipt.items)
    points += (numItems // 2) * CONFIG["itemsBonusPerTwo"]
    logger.debug("After Rule 4 (two items): %d points", points)

    for item in receipt.items:
        trimmedDescription = item.shortDescription.strip()
        if len(trimmedDescription) % 3 == 0:
            itemPrice = float(item.price)
            points += math.ceil(itemPrice * CONFIG["itemDescriptionMultiplier"])
    logger.debug("After Rule 5 (item description): %d points", points)

    # Rule 6: Haha, good try!

    purchaseDate = receipt.purchaseDate
    day = purchaseDate.day
    if day % 2 != 0:
        points += CONFIG["oddDayBonus"]
    logger.debug("After Rule 7 (odd day): %d points", points)

    purchaseTime = receipt.purchaseTime
    if 14 <= purchaseTime.hour < 16:
        points += CONFIG["timeBonus"]
    logger.debug("After Rule 8 (time between 2-4pm): %d points", points)

    return points


@app.exception_handler(RequestValidationError)
async def customRequestValidationExceptionHandler(request, exc):
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
async def processReceipt(receipt: Receipt) -> JSONResponse:
    """
    Process a new receipt, generate a unique receipt ID, and store the receipt data.

    Args:
        receipt (Receipt): The receipt data to be processed.

    Returns:
        JSONResponse: A response containing the unique receipt ID.
    """
    receiptId = str(uuid.uuid4())
    receiptDict = receipt.model_dump()
    receiptDict["id"] = receiptId

    receiptsDb[receiptId] = receiptDict

    logger.info("Received receipt: %s", receiptDict)

    logger.info("Receipt processed with ID: %s", receiptId)

    return JSONResponse(status_code=200, content={"id": receiptId})


@app.get("/receipts/{receiptId}/points", response_model=PointsResponse)
async def getPoints(receiptId: str) -> PointsResponse:
    """
    Get the points for a specific receipt based on the receipt ID.

    Args:
        receiptId (str): The unique ID of the receipt.

    Returns:
        PointsResponse: A response model containing the calculated points.

    Raises:
        HTTPException: If the receipt ID does not exist in the database.
    """

    if receiptId not in receiptsDb:
        logger.error("Receipt not found with ID: %s", receiptId)
        return JSONResponse(
            status_code=404,
            content={"detail": f"Receipt with ID {receiptId} not found."},
        )

    receipt = Receipt(**receiptsDb[receiptId])
    totalPoints = calculatePoints(receipt)

    logger.info("Points calculated for receipt ID %s: %d points", receiptId, totalPoints)

    return PointsResponse(points=totalPoints)
