from collections import defaultdict
from typing import Callable, List
from weakref import WeakSet

from gevent import spawn, Greenlet


class ActionEmitter:

    def __init__(self):
        self.listeners = defaultdict(list)
        self.only_once = defaultdict(list)  # I wish there was a better way, will update if I can think of something
        self.active_events = WeakSet()

    def listen(self, name: str, func: Callable = None) -> Callable:
        def func_wrapper(func):
            self.listeners[name].append(func)
            return func

        if func is not None:
            return func_wrapper(func)
        return func_wrapper

    def listen_once(self, name: str, func: Callable = None) -> Callable:
        if func is None:
            def func_wrap(func):
                return self.listen_once(name, func)
            return func_wrap

        self.only_once[name].append(func)
        self.listen(name, func)

        return func

    def emit(self, name: str, *args, **kwargs) -> List[Greenlet]:
        greenlets = []
        for callback in self.listeners[name]:
            if callback in self.only_once[name]:
                self.only_once[name].remove(callback)
                self.remove_listener(name, callback)
            greenlets.append(spawn(callback, *args, **kwargs))
        self.active_events.update(greenlets)
        return greenlets

    def remove_listener(self, name: str, func: Callable = None):
        if func is None:
            self.listeners[name].clear()
        else:
            self.listeners[name].remove(func)

    def remove_all(self):
        self.listeners.clear()
