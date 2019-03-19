from unittest import TestCase

from action.emitter import ActionEmitter

from gevent import getcurrent, joinall, sleep
from gevent.monkey import patch_all
patch_all()

from threading import current_thread


class TestEmitter(TestCase):

    @staticmethod
    def help_emit(emitter: ActionEmitter, name: str, *args, **kwargs):
        joinall(emitter.emit(name, *args, **kwargs))
        sleep(0)

    def test_listener(self):
        emitter = ActionEmitter()

        @emitter.listen("test")
        def test_event():
            pass

        self.assertIn(test_event, emitter.listeners["test"])

        def second_test_event():
            pass

        emitter.listen("test", second_test_event)

        self.assertIn(test_event, emitter.listeners["test"])
        self.assertIn(second_test_event, emitter.listeners["test"])

    def test_emit(self):
        emitter = ActionEmitter()
        greenlet_name = None
        ran = None

        @emitter.listen("test")
        def test_case(got_value: bool):
            nonlocal greenlet_name, ran
            greenlet_name = current_thread().name
            ran = True
            self.assertIn(getcurrent(), emitter.active_events)
            self.assertTrue(got_value)

        self.help_emit(emitter, "test", True)
        self.assertEqual(0, len(emitter.active_events))
        self.assertNotEqual(greenlet_name, current_thread().name)
        ran = False
        self.help_emit(emitter, "tests", True)
        self.assertFalse(ran)

    def test_once(self):
        emitter = ActionEmitter()
        was_run = False

        @emitter.listen_once("test")
        def test_once():
            nonlocal was_run
            was_run = True

        self.help_emit(emitter, "test")
        self.assertTrue(was_run)
        was_run = False
        self.help_emit(emitter, "test")
        self.assertFalse(was_run)

    def test_remove(self):
        emitter = ActionEmitter()
        was_run = False

        def test_case():
            nonlocal was_run
            was_run = True

        emitter.listen("test", test_case)
        emitter.remove_listener("test", test_case)
        self.help_emit(emitter, "test")
        self.assertFalse(was_run)
        emitter.listen("test", test_case)
        emitter.listen_once("test", test_case)
        emitter.remove_all()
        self.help_emit(emitter, "test")
        self.assertFalse(was_run)
