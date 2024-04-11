from src.database.connection import Connection

conn = Connection()
conn.get_db().connect()

from src.app import App

app = App()
app.mainloop()
