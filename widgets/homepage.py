from textual.widgets import Static


class Homepage(Static):
    """A simple label widget for displaying homepage."""
    def __init__(self, parent):
        Static.__init__(self, parent)

    