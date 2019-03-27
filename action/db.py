from sqlite3 import connect
from typing import Iterator, Union

from action.event import Event

import safepickle as pickle


class ActionBackend:
    """A class that stores events

    ActionBackend is a easy way to add and receive events from an sqlite database. If you want the database to run in
    memory, you can supply ``:memory:`` was the file_path. If you want to create your own backend, you should duplicate
    all methods provided by this class, except the save, that's optional.

    Attributes
    ----------
    file_path : str
        The place where the sqlite3 file is / should be made. Supply ``:memory:`` if you don't want it stored.
    db : sqlite3.Connection
        A connection to the sqlite database
    cursor : sqlite3.Cursor
        A cursor to interact with the database
    """

    def __init__(self, file_path: str = 'action.db', timeout: Union[int, float] = 5.0):
        self.file_path = file_path
        self.db = connect(file_path, timeout=timeout)
        self.cursor = self.db.cursor()

        if ('events',) not in self.cursor.execute("SELECT name FROM sqlite_master "
                                                  "WHERE type ='table' AND name NOT LIKE 'sqlite_%'").fetchall():
            self.cursor.execute("""CREATE TABLE events (
                id TEXT primary key NOT NULL,
                name TEXT NOT NULL,
                sched DATETIME NOT NULL,
                args BLOB,
                kwargs BLOB
                )""")
            self.save()

    def has_event(self, event_id: str) -> bool:
        """
        Check if an event exists inside the database

        Parameters
        ----------
        event_id : str
            The ID of the event that's being looked for.

        Returns
        -------
        exists : bool
            True if the event if in the DB, else False
        """
        query = self.cursor.execute("SELECT * FROM events WHERE id=?", (event_id,))
        if query.fetchone():
            return True
        return False

    def get_event(self, event_id: str) -> Event:
        """
        Retract an event object from the database based on it's ID

        Parameters
        ----------
        event_id : str
            The ID of the event to retract

        Returns
        -------
        event : action.event.Event
            The event that's wanted from the database

        Raises
        ------
        IndexError
            Raised if the event doesn't exist in the database
        """
        event = self.cursor.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if event is None:
            raise IndexError("Database has no event named {}".format(event_id))
        return Event(*event)

    def iter_events(self) -> Iterator[Event]:
        """
        Iterate through each event in the database

        Yields
        ------
        event : action.event.Event
            An event in the database
        """
        events = self.cursor.execute("SELECT * FROM events")
        for event in events.fetchall():
            yield Event(*event)

    def register_event(self, event: Event) -> None:
        """
        Add an event into the database

        Parameters
        ----------
        event : action.event.Event
            The event that'll be added to the database
        """
        items = (event.id, event.name, event.sched,
                 pickle.dumps(event.args), pickle.dumps(event.kwargs))
        self.cursor.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)", items)
        self.db.commit()

    def remove_event(self, event_id: str) -> None:
        """
        Remove an event from the database

        Parameters
        ----------
        event_id : str
            The id of the event that'll be removed
        """
        self.cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.db.commit()

    def save(self) -> None:
        """
        Write the changes to file

        You shouldn't need to use this method, as whenever you remove or add an event, this will be used automaticlly.
        """
        self.db.commit()
