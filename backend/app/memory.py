from collections import defaultdict, deque
from threading import Lock

class SessionMemory:
    def __init__(self, max_turns: int = 6):
        self.max_turns=max_turns
        self._data=defaultdict(lambda: deque(maxlen=max_turns*2))
        self._lock=Lock()

    def history(self, session_id: str):
        with self._lock:
            return list(self._data[session_id])

    def add(self, session_id: str, role: str, content: str):
        with self._lock:
            self._data[session_id].append({'role':role,'content':content})

    def clear(self, session_id: str):
        with self._lock:
            self._data.pop(session_id, None)
