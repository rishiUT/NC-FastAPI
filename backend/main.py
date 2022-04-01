from telnetlib import NOP
from fastapi import FastAPI, Response, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape
import sqlalchemy
import databases

DATABASE_URL = "sqlite:///./dbfolder/users.db"
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
    uid = request.cookies.get('id')
    if not uid:    
        pos, conv = await new_user_info()
        query = users.insert().values(role=pos, conversationid=conv, messagecount=0)
        last_record_id = await database.execute(query)
        query = users.select()     
        uid = last_record_id
        response.set_cookie('id', uid)

    await add_pairing(uid)
    username = "User " + str(uid)
    template = env.get_template("index.html")
    return template.render(title="Home", message="Welcome, " + username + "! ", content="We're glad you could make it.")

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
def record(request: Request):
    template = env.get_template("audioinput.html")
    return template.render(title="Record Audio", id=request.cookies.get('id'))

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket] = {}

    async def connect(self, websocket: WebSocket, id: int):
        await websocket.accept()
        self.active_connections[id] = websocket
        print(self.active_connections.keys())


    def disconnect(self, id: int):
        self.active_connections.pop(id)

    async def send_personal_message(self, message: bytes, websocket: WebSocket):
        await websocket.send_bytes(message)

    async def send_partner_message(self, message: bytes, pid: int):
        print(self.active_connections.keys())
        if pid != -1:
            await self.active_connections.get(pid).send_bytes(message)

    async def broadcast(self, message: bytes):
        for connection in self.active_connections:
            await connection.send_bytes(message)

manager = ConnectionManager()

@app.websocket("/audiowspaired/{uid}")
async def chat_ws_endpoint(websocket: WebSocket, uid:int):
    await manager.connect(websocket, uid)
    pid = -1 #partner ID
    if uid in pairings:
        pid = pairings[uid]
    try:
        while True:
            data = await websocket.receive_bytes()
            print(pid)
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

async def add_pairing(uid: int):
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
        NOP
    elif ids[0][0] in pairings or ids[1][0] in pairings:
        if ids[0][0] in pairings and ids[1][0] in pairings:
            #Pairing unnecessary, it's already in there
            NOP
        else:
            #Something has gone wrong.
            NOP
    else:
        #We have two unpaired elements!
        pairings[ids[0][0]] = ids[1][0]
        pairings[ids[1][0]] = ids[0][0]
    print(pairings)