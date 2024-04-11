from peewee import Model, CharField, IntegerField

from src.database.connection import Connection


class Manga(Model):
    name = CharField()
    last_one = IntegerField()

    class Meta:
        database = Connection.get_db() # This model uses the "people.db" database.