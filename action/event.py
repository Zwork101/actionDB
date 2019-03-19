from datetime import datetime
from typing import Any, Dict, Tuple, Optional, Union
from weakref import ref

from gevent import Greenlet
import safepickle as pickle


class Event:

    def __init__(self, event_id: str,
                 event_name: str,
                 event_sched: datetime,
                 args: Union[Tuple[Any], bytes] = None,
                 kwargs: Union[Dict[str, Any], bytes] = None):
        self.id = event_id
        self.name = event_name
        self.sched = event_sched
        self.args = args or tuple()
        self.kwargs = kwargs or {}
        self._greenlet = lambda: None

        if isinstance(self.sched, str):
            self.sched = datetime.strptime(self.sched, "%Y-%m-%d %H:%M:%S.%f")
        if isinstance(self.args, bytes):
            self.args = pickle.loads(self.args)
        if isinstance(self.kwargs, bytes):
            self.kwargs = pickle.loads(self.kwargs)

    def __eq__(self, other: 'Event'):
        if not isinstance(other, Event):
            raise NotImplementedError
        return self.id == other.id

    @property
    def active_greenlet(self) -> Optional[Greenlet]:
        return self._greenlet()

    @active_greenlet.setter
    def active_greenlet(self, value: Greenlet):
        self._greenlet = ref(value)
