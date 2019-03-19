from datetime import datetime, timedelta
from typing import List, Type, Union
from weakref import WeakValueDictionary
from uuid import uuid4

from action.db import ActionBackend
from action.emitter import ActionEmitter
from action.event import Event

from gevent import spawn_later, Greenlet


class Action(ActionEmitter):

    WARN_EXTRA_SETUPS = True

    def __init__(self, action_db: str = 'action.db',
                 backend: Type[ActionBackend] = ActionBackend,
                 timeout: Union[int, float] = 0.5):
        self.db = backend(action_db, timeout=timeout)
        self.active_schedules = WeakValueDictionary()
        self._ran_setup = False
        super().__init__()

    @staticmethod
    def generate_event(name: str, sched: datetime, *args, event_id: str = None, **kwargs) -> Event:
        event = Event(
            event_id if event_id is not None else uuid4().hex,
            name,
            sched,
            args,
            kwargs
        )
        return event

    def _schedule(self, event: Event) -> Greenlet:
        if not self.db.has_event(event.id):
            self.db.register_event(event)
        seconds_until = (event.sched - datetime.now()).total_seconds()
        greenlet = spawn_later(seconds_until, self.emit, event.name, *event.args, **event.kwargs)
        greenlet.link(lambda _: self.db.remove_event(event.id))
        self.active_schedules[event.id] = greenlet
        return greenlet

    def setup(self) -> List[Greenlet]:
        if self._ran_setup and self.WARN_EXTRA_SETUPS:
            raise RuntimeWarning("Setup was already called, doing it again will create duplicate events.")
        greenlets = []

        for event in self.db.iter_events():
            greenlets.append(self._schedule(event))
        self._ran_setup = True
        return greenlets

    def trigger_at(self, date: Union[datetime, float], name: str, *args, **kwargs) -> Greenlet:
        date = date if isinstance(date, datetime) else datetime.utcfromtimestamp(date)
        event = self.generate_event(name, date, *args, **kwargs)
        return self._schedule(event)

    def trigger_in(self, seconds: Union[timedelta, int], name: str, *args, **kwargs):
        date_delta = seconds if isinstance(seconds, timedelta) else timedelta(seconds=seconds)
        date = datetime.now() + date_delta
        event = self.generate_event(name, date, *args, **kwargs)
        return self._schedule(event)
