from datetime import datetime, timedelta
from functools import wraps
from tempfile import NamedTemporaryFile
from unittest import TestCase
from uuid import UUID
import random

from action.client import Action
from action.db import ActionBackend
from action.event import Event

from gevent.timeout import Timeout
from gevent import joinall


def setup_db(func):
    @wraps(func)
    def wrapper(self):
        with NamedTemporaryFile() as temp_file:
            temp_file.close()
            action_db = ActionBackend(temp_file.name)
            return func(self, action_db)
    return wrapper


class TestClient(TestCase):

    @staticmethod
    def gen_event() -> Event:
        return Event(
            random._urandom(64).hex(),
            random._urandom(16).hex(),
            datetime.now(),
            tuple(),
            {}
        )

    def test_generate(self):
        event = Action.generate_event(
            "Event Name",
            datetime.now(),
        )
        self.assertEqual(event.id, UUID(event.id).hex)

    @setup_db
    def test_startup(self, action_db: ActionBackend):
        action_db.register_event(Action.generate_event("test", datetime.now(), "test-1"))
        action_db.register_event(Action.generate_event("test", datetime.now(), "test-2"))

        emitter = Action(action_db.file_path)
        call_results = set()

        @emitter.listen("test")
        def test_setup(event_name: str):
            call_results.add(event_name)

        joinall([event.active_greenlet for event in emitter.setup()])
        self.assertEqual(call_results, {"test-1", "test-2"})

    def test_at(self):
        action = Action(":memory:")
        was_run = False

        @action.listen("test")
        def test_case():
            nonlocal was_run
            was_run = True

        event = action.trigger_at(datetime.now(), "test")
        event.active_greenlet.join()
        self.assertTrue(was_run)
        was_run = False
        event = action.trigger_at(datetime.now() + timedelta(seconds=30), "test")
        self.assertIn(event.active_greenlet, action.active_schedules.values())
        try:
            with Timeout(1, TimeoutError):
                event.active_greenlet.join()
        except TimeoutError:
            pass
        else:
            self.fail("Greenlet did not timeout")
        self.assertFalse(was_run)

    def test_in(self):
        action = Action(":memory:")
        was_run = False

        @action.listen("test")
        def test_case():
            nonlocal was_run
            was_run = True

        event = action.trigger_in(0, "test")
        event.active_greenlet.join()
        self.assertTrue(was_run)
        was_run = False
        event = action.trigger_in(60, "test")
        self.assertIn(event.active_greenlet, action.active_schedules.values())
        try:
            with Timeout(1, TimeoutError):
                event.active_greenlet.join()
        except TimeoutError:
            pass
        else:
            self.fail("Greenlet did not timeout")
        self.assertFalse(was_run)
