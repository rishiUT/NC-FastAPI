async def new_user_info():
    con = get_db()
    cur = con.cursor()

    cur.execute("select count(id) from users")
    new_id = cur.fetchall()
    new_id = new_id[0][0]
    
    query = users.select()
    user_list = await database.fetch_all(query)
    #cur.execute("select * from users")
    #users = cur.fetchall()
    convIDs = [user.convid for user in user_list]

    maxID = 0
    for convID in convIDs:
        convID = int(convID)
        numIDs = 0
        if maxID < convID:
            maxID = convID
        for otherID in convIDs:
            otherID = int(otherID)
            if otherID == convID:
                numIDs = numIDs + 1
        if numIDs < 2:
            return (new_id, 1, convID)

    return (new_id, 0, maxID + 1)
    # Get all users by conversation id
    # For each conversation id, search users for two matching conversation ids
    # If you find one without a match, return it along with the "buyer" id
    # If they all have a match, return the next conversation id (largest + 1) along with the "seller" id

@app.get('/', response_class=HTMLResponse)
@app.get('/home', response_class=HTMLResponse)
async def home():
#    if 'id' not in session:
#        uid, pos, conv = new_user_info()
#
#        con = get_db()
#        cur = con.cursor()
#        cur.execute("INSERT INTO users (id, role, conversation, messagecount) VALUES (?,?,?,0)", (uid, pos, conv))
#        con.commit()
#
#        session['id'] = uid
#
#    username = "User " + str(session['id'])
    template = env.get_template("index.html")
    return template.render(title="Home", message="Welcome, user!", content="We're glad you could make it.")

@app.get('/resetusers', response_class=HTMLResponse)
def resetusers():
    con = get_db()
    con.execute("DELETE FROM users")
    con.commit()
    template = env.get_template("default.html")
    return template.render(title="Database Cleared", 
                            content="The database is empty now.")

@app.get('/adduser', response_class=HTMLResponse)
def adduser():
    con = get_db()
    #con.row_factory = sqlite3.Row
   
    cur = con.cursor()
    uid, pos, conv = new_user_info()
    cur.execute("INSERT INTO users (id, role, conversation, messagecount) VALUES (?,?,?,0)", (uid, pos, conv))
    con.commit()
    cur.execute("select * from users")
   
    rows = cur.fetchall()

    template = env.get_template("list.html")
    return template.render(title="Add User", rows = rows)

@app.get('/addmessage', response_class=HTMLResponse)
def addmessage():
    con = get_db()
    #con.row_factory = sqlite3.Row
   
    cur = con.cursor()
#    uid = session['id']
    
    cur.execute("select messagecount from users WHERE id = ?", (uid,))
    num_messages = cur.fetchall()
    num_messages = num_messages[0][0]


    cur.execute("UPDATE users SET messagecount = ? WHERE id = ?", (num_messages + 1, uid))
    con.commit()
    cur.execute("select * from users")
   
    rows = cur.fetchall()
    
    template = env.get_template("list.html")
    return template.render(title="Add Message", rows = rows)



class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


            
html2 = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = Date.now()
            document.querySelector("#ws-id").textContent = client_id;
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/wstest2")
async def wstest():
    return HTMLResponse(html2)