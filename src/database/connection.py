from peewee import SqliteDatabase


class Connection():
    DB = None

    @staticmethod
    def _create_connection():
        Connection.DB = SqliteDatabase('getmymanga.db')
        return Connection.DB

    @staticmethod
    def get_db():
        return Connection.DB if Connection.DB else Connection._create_connection()