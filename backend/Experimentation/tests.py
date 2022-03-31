from starlette.testclient import TestClient
from run import app

client = TestClient(app)

def test_root_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message" : "Hello World again"}

def test_correct_item():
    json_blob = {"name": "shampoo", "price": 1.5}
    resp = client.post("/items", json=json_blob)
    assert resp.status_code == 200

def test_wrong_item():
    json_blob = {"name": "shampoo", "price": -1.5}
    resp = client.post("/items", json=json_blob)
    assert resp.status_code != 200