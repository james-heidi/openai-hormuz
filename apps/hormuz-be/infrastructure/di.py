def wire_cross_module_events() -> None:
    """Register cross-module event subscriptions.

    The scaffold has one bounded context today. Keep this hook so future
    contexts can register event listeners from one predictable startup point.
    """

