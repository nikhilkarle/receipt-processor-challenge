import uuid
import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import List
import math

app = FastAPI()

# Set up logging to a file
logging.basicConfig(
    filename='receipts.log', 
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Temporary storage for receipts
receipts_db = {}

class Item(BaseModel):
    shortDescription: str
    price: str

class Receipt(BaseModel):
    retailer: str
    purchaseDate: str
    purchaseTime: str
    items: List[Item]
    total: str

class PointsResponse(BaseModel):
    points: int

class ErrorResponse(BaseModel):
    detail: str


# Helper function for points calculation
def calculate_points(receipt):
    """
    Calculate points based on the receipt data according to specific rules.

    Args:
        receipt (Receipt): The receipt object containing the data to calculate points.

    Returns:
        int: The total points calculated based on the rules.
    """
    points = 0
    retailer_name = receipt.retailer
    points += sum(c.isalnum() for c in retailer_name)
    logging.debug(f"After Rule 1 (retailer name): {points} points")
    
    total = float(receipt.total)
    if total.is_integer():
        points += 50
    logging.debug(f"After Rule 2 (round dollar): {points} points")
    
    if total % 0.25 == 0:
        points += 25
    logging.debug(f"After Rule 3 (multiple of 0.25): {points} points")
    
    num_items = len(receipt.items)
    points += (num_items // 2) * 5
    logging.debug(f"After Rule 4 (two items): {points} points")
    
    for item in receipt.items:
        trimmed_description = item.shortDescription.strip()
        if len(trimmed_description) % 3 == 0:
            item_price = float(item.price)
            points += math.ceil(item_price * 0.2)
    logging.debug(f"After Rule 5 (item description): {points} points")
    
    purchase_date = receipt.purchaseDate
    day = int(purchase_date.split("-")[2])
    if day % 2 != 0:
        points += 6
    logging.debug(f"After Rule 7 (odd day): {points} points")
    
    purchase_time = receipt.purchaseTime
    hours, minutes = map(int, purchase_time.split(":"))
    if 14 <= hours < 16:
        points += 10
    logging.debug(f"After Rule 8 (time between 2-4pm): {points} points")
    
    return points


@app.post("/receipts/process", response_model=ErrorResponse)
async def process_receipt(receipt: Receipt):
    """
    Process a new receipt, generate a unique receipt ID, and store the receipt data.

    Args:
        receipt (Receipt): The receipt data to be processed.

    Returns:
        dict: A dictionary containing the unique receipt ID.
    """
    try:
        receipt_id = str(uuid.uuid4())
        receipt_dict = receipt.model_dump()
        receipt_dict["id"] = receipt_id

        # Store the receipt in the 'database'
        receipts_db[receipt_id] = receipt_dict

        # Log the receipt processing
        logging.info(f"Receipt processed with ID: {receipt_id}")

        # Return the receipt ID
        return JSONResponse(status_code=200, content={"id": receipt_id})

    except ValidationError as e:
        logging.error(f"Invalid receipt data: {e}")
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid structure or missing fields in the input."}
        )


@app.get("/receipts/{receipt_id}/points", response_model=PointsResponse)
async def get_points(receipt_id: str):
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
        logging.error(f"Receipt not found with ID: {receipt_id}")
        return JSONResponse(
            status_code=404,
            content={"detail": f"Receipt with ID {receipt_id} not found."}
        )

    receipt = Receipt(**receipts_db[receipt_id])
    total_points = calculate_points(receipt)

    logging.info(f"Points calculated for receipt ID {receipt_id}: {total_points} points")

    return PointsResponse(points=total_points)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
