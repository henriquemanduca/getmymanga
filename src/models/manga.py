from peewee import Model, CharField, IntegerField

from src.database.connection import Connection


class Manga(Model):
    name = CharField()
    last_downloaded = IntegerField()
    available_directories = IntegerField()
    last_directory = IntegerField()

    class Meta:
        database = Connection.get_db()