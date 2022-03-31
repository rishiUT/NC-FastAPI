import sqlalchemy
import databases
#from sqlalchemy.orm import Session
#from sqlalchemy_db import crud, models, schemas
#from sqlalchemy_db.database import SessionLocal, engine 

DATABASE_URL = "sqlite:///./users.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
notes = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id"),
    sqlalchemy.Column("role"),
    sqlalchemy.Column("conversationid"),
    sqlalchemy.Column("messagecount")
)
engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

# Dependency
#def get_db():
#    db = SessionLocal()
#    try:
#        yield db
#    finally:
#        db.close()
    
@app.get('/resetdb', response_class=HTMLResponse)
def resetdb():
    con = get_db()
    con.execute("DROP TABLE users")
    con.execute("CREATE TABLE users (id INTEGER unique, role TEXT, conversation INTEGER, messagecount INTEGER)")
    template = env.get_template("default.html")
    return template.render(title="Database Reset", 
                            content="The database now has a 'users' table.")

@app.get('/list', response_class=HTMLResponse)
def list():
    con = get_db()
    #con.row_factory = sqlite3.Row
   
    cur = con.cursor()
    cur.execute("select * from users")
    rows = cur.fetchall()
    template = env.get_template("list.html")
    return template.render(title="User List", rows = rows)
