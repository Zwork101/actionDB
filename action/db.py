from sqlite3 import connect
from typing import Iterator, NoReturn, Union

from action.event import Event

import safepickle as pickle


class ActionBackend:

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
        query = self.cursor.execute("SELECT * FROM events WHERE id=?", (event_id,))
        if query.fetchone():
            return True
        return False

    def get_event(self, event_id: str) -> Event:
        event = self.cursor.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        return Event(*event)

    def iter_events(self) -> Iterator[Event]:
        events = self.cursor.execute("SELECT * FROM events")
        for event in events.fetchall():
            yield Event(*event)

    def register_event(self, event: Event):
        items = (event.id, event.name, event.sched,
                 pickle.dumps(event.args), pickle.dumps(event.kwargs))
        self.cursor.execute("INSERT INTO events VALUES (?, ?, ?, ?, ?)", items)
        self.db.commit()

    def remove_event(self, event_id: str) -> NoReturn:
        self.cursor.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.db.commit()

    def save(self):
        self.db.commit()
