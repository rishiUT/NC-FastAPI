from telnetlib import NOP
from fastapi import FastAPI, Response, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape
import sqlalchemy
import databases
from connectionmanager import ConnectionManager
import json
import datetime

DATABASE_URL = "sqlite:///./dbfolder/users.db"
#DATABASE_URL = "postgresql://nc:Password1@localHost:5432/nc"
database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("role", sqlalchemy.Integer),
    sqlalchemy.Column("conversationid", sqlalchemy.Integer),
    sqlalchemy.Column("messagecount", sqlalchemy.Integer)
)

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

class User(BaseModel):
    id: int
    role: int
    conversationid: int
    messagecount: int

TASK_DESCRIPTIONS = ["Your goal for this task is to sell this item for as close to the listing price as possible. You will negotiate with your assigned buyer using recorded messages. Once the buyer chooses to make an offer, you may either accept or reject the offer.",
                     "Your goal for this task is to convince the seller to sell you the item for as close to your goal price as possible. You will negotiate with the seller using recorded messages. At any point, you may make an offer of any price; however, once the seller accepts or rejects your offer, the negotiation is over."]

with open('static/filtered_train.json') as item_file:
    items = json.load(item_file)

app = FastAPI(title='Test')
app.mount("/static", StaticFiles(directory="static"), name="static")
env = Environment(
    loader=PackageLoader("ncserver"),
    autoescape=select_autoescape()
)

@app.on_event("startup")
async def startup():
    await database.connect()
    

@app.on_event("shutdown")
async def shutdown_event():
    await reset_users()
    await database.disconnect()

pairings = {}

@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
async def home(request: Request, response: Response):
    template = env.get_template("home.html")
    return template.render(title="Home")

@app.get('/start', response_class=HTMLResponse)
async def home(request: Request, response: Response):
    uid = request.cookies.get('id')
    if not uid:    
        pos, conv = await new_user_info()
        query = users.insert().values(role=pos, conversationid=conv, messagecount=0)
        last_record_id = await database.execute(query)
        query = users.select()     
        uid = last_record_id
        response.set_cookie('id', uid)

    paired = False
    while not paired:
        paired = await add_pairing(uid)
    username = "User " + str(uid)
    template = env.get_template("pairing.html")
    return template.render(title="Start", content="Welcome, " + username + "! We're glad you could make it. Click the button below to begin.")

@app.get('/finish', response_class=HTMLResponse)
async def self_reset(request: Request, response: Response):
    uid = request.cookies.get('id')
    if uid:    
        response.delete_cookie('id')
    template = env.get_template("default.html")
    return template.render(title="Thank You!", 
                            content="Thanks for your participation! You have been removed from your group.")

@app.get('/about', response_class=HTMLResponse)
def about():
    template = env.get_template("default.html")
    return template.render(title="About the Negotiation Chat", 
                            content="This website will be used for verbal, turn-based negotiations.")

@app.get('/list', response_model=list[User])
async def list_users():
    query = users.select()
    user_list = await database.fetch_all(query)
    return user_list
    #template = env.get_template("list.html")
    #return template.render(title="User List", rows = rows)

@app.get("/adduser", response_model=list[User])
async def add_user():
    query = users.insert().values(role=0, conversationid=0, messagecount=0)
    last_record_id = await database.execute(query)
    query = users.select()
    user_list = await database.fetch_all(query)
    return user_list

@app.get('/addmessage', response_model=list[User])
async def add_message():
    #con.row_factory = sqlite3.Row
#    uid = session['id']
    uid = 0

    ua = users.alias("alias")
    query = sqlalchemy.select([ua.c.messagecount]).where(ua.c.id==uid)
    num_messages = await database.fetch_all(query)
 
    num_messages = num_messages[0][0]

    query = users.update().where(users.c.id==uid).values(messagecount = (num_messages + 1))
    await database.execute(query)
    query = users.select()
    user_list = await database.fetch_all(query)
    return user_list
    
    template = env.get_template("list.html")
    return template.render(title="Add Message", rows = rows)

@app.get('/resetusers', response_class=HTMLResponse)
async def reset_users():
    query = users.delete()
    await database.execute(query)
    template = env.get_template("default.html")
    return template.render(title="Database Cleared", 
                            content="The database is empty now.")


@app.get('/record', response_class=HTMLResponse)
async def record(request: Request):
    ua = users.alias("alias")
    uid = request.cookies.get('id')
    query = sqlalchemy.select([ua.c.role]).where(ua.c.id==uid)
    is_buyer = await database.fetch_all(query)
    is_buyer = is_buyer[0][0]

    role_txt = "Buyer"
    if is_buyer == 0:
        role_txt = "Seller"

    query = sqlalchemy.select([ua.c.conversationid]).where(ua.c.id==uid)
    convid = await database.fetch_all(query)
    convid = convid[0][0]
    convid = convid % len(items) #Pseudo-randomization; not actually random, but rarely repeats

    item_data = items[convid]

    price_coefficient = 1
    if is_buyer:
        price_coefficient = 0.8
    item_price = item_data['Price'] * price_coefficient

    item_description = item_data['Description'][0]

    image = None 
    if len(item_data['Images']):
        image = "/static/images/" + item_data['Images'][0]
    else:
        image = None

    template = env.get_template("audioinput.html")
    return template.render(title="Record Audio", role=role_txt, task_description=TASK_DESCRIPTIONS[is_buyer], goal_price=item_price,
    item_description=item_description, item_image=image, id=uid)


manager = ConnectionManager()

@app.websocket("/audiowspaired/{uid}")
async def chat_ws_endpoint(websocket: WebSocket, uid:int):
    ua = users.alias("alias")
    query = sqlalchemy.select([ua.c.conversationid]).where(ua.c.id==uid)
    convid = await database.fetch_all(query)
    convid = convid[0][0]

    query = sqlalchemy.select([ua.c.role]).where(ua.c.id==uid)
    is_buyer = await database.fetch_all(query)
    is_buyer = is_buyer[0][0]

    role_txt = "Buyer"
    if is_buyer == 0:
        role_txt = "Seller"

    await manager.connect(websocket, uid)
    pid = -1 #partner ID
    if uid in pairings:
        pid = pairings[uid]
    try:
        while True:
            data = await websocket.receive_bytes()
            print(pid)

            timestamp = datetime.datetime.now()
            temp = "recordings/" + role_txt + "_" + str(uid) + "_" + str(timestamp) + ".mp3"
            file_name = ""
            for c in temp:
                if c == ' ':
                    file_name += "_"
                elif c == ':':
                    file_name += "-"
                else:
                    file_name += c
            print(file_name)
            with open(file_name, "wb") as file1:
                file1.write(data)
                file1.close() 
            
            await manager.send_partner_message(data, pid)
    except WebSocketDisconnect:
        manager.disconnect(uid)

async def new_user_info():
    #No need to create a new id, because the db creates them automatically   
    query = users.select()
    user_list = await database.fetch_all(query)
    # Get all users by conversation id
    convIDs = [user.conversationid for user in user_list]

    maxID = 0
    for convID in convIDs:
        # For each conversation id, search users for two matching conversation ids
        convID = int(convID)
        numIDs = 0
        if maxID < convID:
            maxID = convID
        for otherID in convIDs:
            otherID = int(otherID)
            if otherID == convID:
                numIDs = numIDs + 1
        if numIDs < 2:
            # If you find one without a match, return it along with the "buyer" id
            return (1, convID)

    # If they all have a match, return the next conversation id (largest + 1) along with the "seller" id
    return (0, maxID + 1)

async def add_pairing(uid: int) -> bool:
    ua = users.alias("alias")
    query = sqlalchemy.select([ua.c.conversationid]).where(ua.c.id==uid)
    convid = await database.fetch_all(query)
    convid = convid[0][0]
    query = sqlalchemy.select([ua.c.id]).where(ua.c.conversationid==convid)
    ids = await database.fetch_all(query)
    #print(ids[0][0])
    #print(ids[1][0])
    if len(ids) < 2:
        #Pairing fails, return some error
        return False
    elif ids[0][0] in pairings or ids[1][0] in pairings:
        if ids[0][0] in pairings and ids[1][0] in pairings:
            #Pairing unnecessary, it's already in there
            return True
        else:
            #Something has gone wrong.
            return False
    else:
        #We have two unpaired elements!
        pairings[ids[0][0]] = ids[1][0]
        pairings[ids[1][0]] = ids[0][0]
    print(pairings)
    return True