"""Domain errors raised while inspecting RSS projects."""


class RSSInventoryError(RuntimeError):
    """An RSS project could not be inventoried safely."""
