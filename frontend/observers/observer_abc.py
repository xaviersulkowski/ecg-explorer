import abc
from enum import Enum


class Observer(abc.ABC):
    @abc.abstractmethod
    def update_on_notification(self, event: Enum, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the update method.")


class Subject(abc.ABC):
    def __init__(self):
        self._subscribers: list[Observer] = []

    def add_subscriber(self, subscriber: Observer):
        self._subscribers.append(subscriber)

    def remove_subscriber(self, subscriber: Observer):
        self._subscribers.remove(subscriber)

    def notify_subscribers(self, event: Enum, *args, **kwargs):
        for subscriber in self._subscribers:
            subscriber.update_on_notification(event, *args, **kwargs)
