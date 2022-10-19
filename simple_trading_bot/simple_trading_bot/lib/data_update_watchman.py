

class DataUpdateWatchman:
    """
    Class used to keep track on data updates
    """

    def __init__(self, rofex_proxy, yfinance_md_feed):
        self._rofex_proxy = rofex_proxy
        self._yfinance_md_feed = yfinance_md_feed
        self._last_proc_timestamp = 0.

    def set_last_processed_timestamp(self):
        "This method tracks "
        self._last_proc_timestamp = max(
            self._rofex_proxy.last_update_timestamp(),
            self._yfinance_md_feed.last_update_timestamp())

    def should_update(self):
        "Returns True when data is ahead form last time it was read"
        return (self._last_proc_timestamp < self._rofex_proxy.last_update_timestamp() or
                self._last_proc_timestamp < self._yfinance_md_feed.last_update_timestamp())
