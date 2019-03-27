from datetime import datetime
from typing import Any, Dict, Tuple, Optional, Union
from weakref import ref

from gevent import Greenlet
import safepickle as pickle


class Event:
    """
    The event dataclass

    This class doesn't do much but hold information, and you should almost never initiate it yourself. If you need to,
    use `action.client.Action.generate_event` instead.

    .. note:: You can compare events are the same or different with ``==`` or ``!=``

    Attributes
    ----------
    id : str
        A unique event identifier
    name : str
        The name of the event that will be triggered
    sched : datetime.datetime
        The date + time of when the event will be triggered
    args : Tuple[Any]
        A tuple of args that will be passed into listeners
    kwargs : Dict[str, Any]
        A dict of kwargs that will be passed into listeners
    active_greenlet : gevent.Greenlet or None
        A weakref to a greenlet that is currently being run, or None if not applicable.
    """

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

    def __eq__(self, other: object):
        if not isinstance(other, Event):
            raise NotImplementedError
        return self.id == other.id

    def __ne__(self, other: object):
        if not isinstance(other, Event):
            raise NotImplementedError
        return self.id != other.id

    @property
    def active_greenlet(self) -> Optional[Greenlet]:
        return self._greenlet()

    @active_greenlet.setter
    def active_greenlet(self, value: Greenlet):
        if not isinstance(value, Greenlet):
            raise ValueError("active_greenlet can only be set to a Greenlet.")
        self._greenlet = ref(value)
