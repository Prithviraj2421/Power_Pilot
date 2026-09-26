class EventBus:

    def __init__(self):

        self.handlers = {}

    def subscribe(self, event_name, handler):

        self.handlers.setdefault(
            event_name,
            []
        ).append(handler)

    def publish(self, event):

        for handler in self.handlers.get(
            event.name,
            []
        ):

            handler(event)

