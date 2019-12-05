# -*- coding: utf-8 -*-
import datetime

from peewee import (
    CharField, DatabaseProxy, DateTimeField, IntegerField, Model, TextField,
)
from playhouse.db_url import connect

INITIAL_RATING = 700

db_proxy = DatabaseProxy()


class BaseModel(Model):
    created_at = DateTimeField(default=datetime.datetime.now, null=True)
    updated_at = DateTimeField(default=datetime.datetime.now, null=True)

    class Meta:
        database = db_proxy  # см https://clck.ru/Jy4BB

    def save(self, force_insert=False, only=None):
        self.updated_at = datetime.datetime.now()
        super().save(force_insert=force_insert, only=only)


class Player(BaseModel):
    name = CharField(max_length=255)
    rating = IntegerField(default=INITIAL_RATING)
    path = CharField(max_length=255)


class Battle(BaseModel):
    """ для хранения данных об обработанных результатах битв """
    uuid = CharField(max_length=255)
    happened_at = DateTimeField()
    result = TextField()


def init_db(db_url):
    database = connect(db_url)
    db_proxy.initialize(database)
    database.create_tables([Player, Battle])
    return database

