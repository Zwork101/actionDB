"""
Welcome to ActionDB's docs!
===========================

Introduction
------------

Welcome to actionDB, the DB that comes to you. ActionDB is designed to keep events that need to be summoned at a later
date persistent. Personally, this will be used when I make discord bots via
https://github.com/b1naryth1ef/disco. However this doesn't mean you
can't use this with anything else, you can, and I highly encourage that you do. While this library was designed so that
you could easily create and use your own backend, you're welcome to use the sqlite3 backend that comes with it. Lastly,
I was to talk about what's planned. At some point, I want to do some major refactoring, and separate the client and
server. This would allow you connect to a remote database, something that's not essential but nice, but mainly use
whatever concurrency library you want. The backend will still be gevent, however the client can be asyncio, trio,
threading, etc.

Quick Start
-----------

To get started, we'll need to create our client, this will also create a action.db file, however the name can be
changed when initializing:

    from action import Action

    action = Action()

After this, you should add listeners to your heart's content:

    @action.listen("new_msg")
    def new_message(name: str, content: str, id: str=None)
        print(name + "\\n\\n" + content + "\\n" + "(" + id + ")")

And if you want to do something, such as send a message in 5 minutes, you can do:

    action.trigger_in(5 * 60, "new_msg", "Hello World!", "My name is sam, and I live in a can", id="2323445")

Then presuming you're also doing other things, or have utilized ``gevent.joinall``, in 5 minutes you'll see:

    Hello World!

    My name is sam, and I live in a can
    (2323445)

And that's all there is! If you want to see how you can trigger events at an exact time, or other fun stuff, see the
documentation graciously provided below!

.. note::
    You can import the main classes from action like so:

        from action import Action, ActionBackend, ActionEmitter, Event

Happy Coding!
-------------
"""
from action.client import Action
from action.db import ActionBackend
from action.emitter import ActionEmitter
from action.event import Event
