import rf_processtree._rf_processtree_base


class rf_processtree_child(rf_processtree._rf_processtree_base._rf_processtree_base):
    _readQueue = None
    _writeQueue = None
    def __init__(self):
        assert self._writeQueue is not None, "Parent did not provide a write queue"
        assert self._readQueue is not None, "Parent did not provide a read queue"
        super().__init__(self._writeQueue, self._readQueue)
