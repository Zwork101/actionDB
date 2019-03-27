from collections import defaultdict
from typing import Callable, List
from weakref import WeakSet

from gevent import spawn, Greenlet


class ActionEmitter:
    """
    The class that deals with emitting and listening

    This in the class that is used by `action.client.Action` to trigger events. You can use this class by it self if
    you'd like, but if that's the only reason you're using this library I would suggest you re-create this class
    yourself.

    Attributes
    ----------
    listeners : defaultdict[str -> List[Callable]]
        The dict that carries all listeners that were attached.
    only_once : defaultdict[str -> List[Callable]]
        The dict that contains information on listeners that want to be removed the first time they're called.
    active_events : WeakSet[gevent.Greenlet]
        A set of weak refs to greenlets that have been spawned via emits
    """

    def __init__(self):
        self.listeners = defaultdict(list)
        self.only_once = defaultdict(list)  # I wish there was a better way, will update if I can think of something
        self.active_events = WeakSet()

    def listen(self, name: str, func: Callable = None) -> Callable:
        """
        Register the function as a listener

        This method will add the function as a listener, so that it may listen to events emitted with the specified
        name. You should use it like this when you can::

            @emitter.listen("HelloWorld")
            def hello_world():
              ...

        Or like this when you can't::

            def hello_world():
                ...

            emitter.listen("HelloWorld", hello_world)

        But whatever you do, *don't* pass in a function, and use it as a decorator at the same time!

        Parameters
        ----------
        name : str
            The name of the events to listen to
        func : Callable, optional
            Only use this if you are unable to use the listen command as a decorator

        Returns
        -------
        function : Callable
            Either the function you passed in, or a function wrapper if used as a decorator
        """
        def func_wrapper(func):
            self.listeners[name].append(func)
            return func

        if func is not None:
            return func_wrapper(func)
        return func_wrapper

    def listen_once(self, name: str, func: Callable = None) -> Callable:
        """
        Register a function that will be removed when triggered

        This method will behave exactly the same was as `action.emitter.ActionEmitter.listen`, however after the
        first time the listener is triggered, it will also be removed. This is useful when you need something to be
        setup, but only once.

        Parameters
        ----------
        name : str
            The name of the event it will listen for
        func : Callable
            The listener, see `action.emitter.ActionEmitter.listen` for more details.

        Returns
        -------
        function : Callable
            See `action.emitter.ActionEmitter.listen` for more details.
        """
        if func is None:
            def func_wrap(func):
                return self.listen_once(name, func)
            return func_wrap

        self.only_once[name].append(func)
        self.listen(name, func)

        return func

    def emit(self, name: str, *args, **kwargs) -> List[Greenlet]:
        """
        Trigger listeners for a specific event

        This method will instantly trigger all functions that are listening to the provided event. If you actually
        wanted to trigger an event at another time, see `action.client.Action` for help with that. It will spawn the
        listeners are greenlets, so this method is non-blocking.

        Parameters
        ----------
        name : str
            The name of the event that is being emitted
        *args : Any
            Args that will be provided to the listeners
        **kwargs : str, Any
            Kwargs that will be provided to the listeners

        Returns
        -------
        greenlets : List[gevent.Greenlet]
            A list of listeners that have been spawned
        """
        greenlets = []
        for callback in self.listeners[name]:
            if callback in self.only_once[name]:
                self.only_once[name].remove(callback)
                self.remove_listener(name, callback)
            greenlets.append(spawn(callback, *args, **kwargs))
        self.active_events.update(greenlets)
        return greenlets

    def remove_listener(self, name: str, func: Callable = None):
        """
        Remove a listener

        This command is used to remove either one or multiple listeners. If you want to remove all listeners
        connected to a certain event, call this method without a function:

            emitter.remove_listener("join")

        However if you only want to remove a specific listener from an event, provide that function:

            @emitter.listen("join")
            def on_join():
              ...

            emitter.remove_listener("join", on_join)

        Parameters
        ----------
        name : str
            The name of the event you'll be removing (from)
        func : Callable, optional
            The specific listener you're removing

        Raises
        ------
        ValueError
            This error will be raised if you try and remove a specific function that's not a listener
        """
        if func is None:
            self.listeners[name].clear()
        else:
            self.listeners[name].remove(func)

    def remove_all(self):
        """
        Remove all the listeners

        This does exactly what it says. It will remove all listeners, no matter the event it's attached to.
        """
        self.listeners.clear()
