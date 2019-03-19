from datetime import datetime
from functools import wraps
from tempfile import NamedTemporaryFile
from unittest import TestCase
import random

from action.db import ActionBackend
from action.event import Event


def setup_db(func):
    @wraps(func)
    def wrapper(self):
        with NamedTemporaryFile() as temp_file:
            temp_file.close()
            action_db = ActionBackend(temp_file.name)
            return func(self, action_db)
    return wrapper


class TestDatabase(TestCase):

    @staticmethod
    def gen_event() -> Event:
        return Event(
            random._urandom(64).hex(),
            random._urandom(16).hex(),
            datetime.now(),
            (random.randint(-10, 50),),
            {"test": random._urandom(8).hex()}
        )

    @setup_db
    def test_setup(self, action_db: ActionBackend):
        self.assertIn('events',
                      action_db.cursor.execute("SELECT name FROM sqlite_master "
                                               "WHERE type ='table' AND name NOT LIKE 'sqlite_%'").fetchone())

    @setup_db
    def test_insert_has(self, action_db: ActionBackend):
        rand_event = self.gen_event()
        action_db.register_event(rand_event)
        self.assertTrue(action_db.has_event(rand_event.id))
        self.assertFalse(action_db.has_event(rand_event.id + '-non-exist'))

    @setup_db
    def test_remove(self, action_db: ActionBackend):
        rand_event = self.gen_event()
        action_db.register_event(rand_event)
        action_db.remove_event(rand_event.id)
        self.assertFalse(action_db.has_event(rand_event.id))

    @setup_db
    def test_get(self, action_db: ActionBackend):
        rand_event = self.gen_event()
        action_db.register_event(rand_event)
        db_event = action_db.get_event(rand_event.id)
        self.assertTrue(rand_event == db_event)
        self.assertEqual(rand_event.name, db_event.name)
        self.assertEqual(rand_event.sched, db_event.sched)
        self.assertEqual(rand_event.args, db_event.args)
        self.assertEqual(rand_event.kwargs, db_event.kwargs)
