from datetime import datetime, timedelta
from typing import List, Type, Union
from weakref import WeakValueDictionary
from uuid import uuid4

from action.db import ActionBackend
from action.emitter import ActionEmitter
from action.event import Event

from gevent import spawn_later, Greenlet


class Action(ActionEmitter):
    """
    The client to manage events and storing them.

    This class is the only thing you'll need to use to fully utilize the action library. It's important to note that
    this inherits from `action.emitter.ActionEmitter`, because many of the methods you'll be using come from that
    class. Also, in future major versions, the client will be separated from the db, and the database will act as a
    server. This way people can use trio, threading, asyncio whatever, and not be forced to use gevent.

    Properties
    ----------
    db: action.db.ActionBackend
        This is what the client will use to store the events in
    active_schedules : weakref.WeakValueDictionary
        This is a dictionary with event ids to the corresponding greenlets, created by _schedule
    """

    WARN_EXTRA_SETUPS = True
    """See action.Action.setup for information"""
    WARN_ALREADY_SCHEDULED = True
    """See action.Action._schedule for information"""

    def __init__(self, action_db: str = 'action.db',
                 backend: Type[ActionBackend] = ActionBackend,
                 timeout: Union[int, float] = 0.5):
        self.db = backend(action_db, timeout=timeout)
        self.active_schedules = WeakValueDictionary()  # type: WeakValueDictionary['str', Greenlet]
        self._ran_setup = False
        super().__init__()

    @staticmethod
    def generate_event(name: str, sched: datetime, *args, event_id: str = None, **kwargs) -> Event:
        """
        A shortcut for generating event objects

        There's not much need to use this yourself unless you want to create your own event ids. Also quick pitfall,
        you can't create an event with a kwarg called event_id, this effects trigger_at and trigger_in too.

        Parameters
        ----------
        name : str
            The name of the listener that'll be triggered
        sched : datetime.datetime
            The time that the event will trigger
        *args : Any
            Args that will passed into all triggered functions
        event_id : str
            If not supplied, a uuid4 hex will be used instead
        **kwargs : str, Any
            Kwargs that will passed into all the triggered functions

        Returns
        -------
        event : action.event.Event
            The newly created event
        """
        event = Event(  # type: ignore
            event_id if event_id is not None else uuid4().hex,
            name,
            sched,
            args,
            kwargs
        )
        return event  # I'd rather not ignore it, but I've fairly certain it's an issue with mypy

    def schedule(self, event: Event) -> Greenlet:
        """
        This method will schedule the event based on it's information

        There's not much need to call this method directly, hence why it's protected. You'll only need this if you're
        making your own event objects, which may be the case. This method spawns a greenlet that'll wait till the
        specified time to trigger listeners. It will also save the event in the database if it isn't in it already.

        .. warning:: This greenlet is already linked
                     If you need to link a call back, make sure to also call the command that's been linked, thanks!

        Parameters
        ----------
        event : action.event.Event
            The event that will be scheduled

        Returns
        -------
        greenlet : gevent.Greenlet
            The greenlet that has the scheduled event

        Raises
        ------
        ResourceWarning
            If you're scheduling an event that has already been scheduled, it will raise this error. You can disable
            this by setting the class variable ``WARN_EXTRA_SCHEDULED`` to ``False``
        """
        if event.active_greenlet is not None and self.WARN_ALREADY_SCHEDULED:
            raise ResourceWarning("Scheduling an event that already has already been spawned.")

        if not self.db.has_event(event.id):
            self.db.register_event(event)
        seconds_until = (event.sched - datetime.now()).total_seconds()
        greenlet = spawn_later(seconds_until, self.emit, event.name, *event.args, **event.kwargs)
        event.active_greenlet = greenlet
        greenlet.link(lambda _: self.db.remove_event(event.id))
        self.active_schedules[event.id] = greenlet
        return greenlet

    def setup(self) -> List[Event]:
        """
        This will read an spawn all events in the database

        It's absolutely necessary that you call this command, as it readies events that have been stored. The reason it
        isn't called in ``__init__`` was because you need to add listeners first. It will then return a list of all the
        events it spawned.

        Returns
        -------
        events : List[action.event.Event]
            A list of events that were spawned from the database

        Raises
        ------
        RuntimeWarning
            If you run this command more then once, it will raise this warning. You can disable it by setting the class
            variable ``WARN_EXTRA_SETUPS`` to ``False``.
        """
        if self._ran_setup and self.WARN_EXTRA_SETUPS:
            raise RuntimeWarning("Setup was already called, doing it again will create duplicate events.")
        events = []

        for event in self.db.iter_events():
            self.schedule(event)
            events.append(event)
        self._ran_setup = True
        return events

    def trigger_at(self, date: Union[datetime, float], name: str, *args, **kwargs) -> Event:
        """
        Trigger an event at a certain time

        This method is used to spawn an event at a specific point in time, if the time is in the past, it will trigger
        immediately.

        Parameters
        ----------
        date : datime.datetime or float
            The time the event will trigger. If it's a float, it must be a timestamp
        name : str
            The name of the event that will be triggered
        *args : Any
            Args that will be passed into the listeners
        **kwargs : str -> Any
            Kwargs that will be passed into the listeners

        Returns
        -------
        event : action.event.Event
            The event that has been spawned
        """
        date = date if isinstance(date, datetime) else datetime.utcfromtimestamp(date)
        event = self.generate_event(name, date, *args, **kwargs)
        self.schedule(event)
        return event

    def trigger_in(self, seconds: Union[timedelta, int], name: str, *args, **kwargs) -> Event:
        """
        Trigger an event relative to the current time

        This method will trigger an event in a certain amount of time. If the time is negative it will instantly spawn.

        Parameters
        ----------
        seconds : datetime.timedelta or int
            Time after now, if it's an int it will be in seconds
        name : str
            The name of the event that will be triggered
        *args: Any
            Args that will be passed into the listeners
        **kwargs : str -> Any
            Kwargs that will be passed into the listeners

        """
        date_delta = seconds if isinstance(seconds, timedelta) else timedelta(seconds=seconds)
        date = datetime.now() + date_delta
        event = self.generate_event(name, date, *args, **kwargs)
        self.schedule(event)
        return event
