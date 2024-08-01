from peewee import Model, CharField, IntegerField

from src.database.connection import Connection


class Manga(Model):
    name = CharField()
    directory = IntegerField()
    last_downloaded = IntegerField()

    class Meta:
        database = Connection.get_db()