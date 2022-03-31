from fastapi import FastAPI, WebSocket
from pydantic import BaseModel, validator
import time
import asyncio
import random

# Create application
app = FastAPI(title='Test')

class Item(BaseModel):
    name: str
    price: float

    @validator("price")
    def price_must_be_positive(cls, value):
        if value < 0:
            raise ValueError(f"Please give a value >= 0; we received {value}")
        return value

@app.get("/")
def root():
    return {"message":"Hello World again"}

@app.get("/users/{user_id}")
def read_user(user_id: int):
    """
    Inputs: integer user_id
    Outputs: JSON block with user_id
    """
    return {"user_id": user_id}

@app.post("/items")
def create_item(item: Item):
    return item

@app.get("/sleep_slow")
def sleep_slow():
    r = time.sleep(1)
    return {"status" : "done"}

@app.get("/sleep_fast")
async def sleep_fast():
    r = await asyncio.sleep(1)
    return {"status" : "done"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print('Accepting client connection...')
    await websocket.accept()
    while True:
        try:
            # Wait for any message from the client
            await websocket.receive_text()
            # Send message to the client
            resp = {'value': random.uniform(0, 1)}
            await websocket.send_json(resp)
        except Exception as e:
            print('error:', e)
            break
    print('Bye!')