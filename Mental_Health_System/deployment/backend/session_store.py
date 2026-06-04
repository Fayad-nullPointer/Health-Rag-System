import uuid
from datetime import datetime, timezone
from typing   import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SessionMemory:
    """
    Manages everything that must persist across turns in a single conversation.

    - Sliding window of the last 6 turns (12 messages) for conversation history
    - Sticky crisis flag — once raised it never resets within a session
    - Emotion history and topics discussed for session-level context
    """

    def __init__(self, session_id: str, user_id: int, country: str = "Unknown"):
        self.session_id       : str   = session_id
        self.user_id          : int   = user_id
        self.country          : str   = country
        self.history          : list  = []
        self.prior_crisis     : bool  = False
        self.emotion_history  : list  = []
        self.topics_discussed : list  = []
        self.turn_count       : int   = 0
        self.started_at       : datetime = utcnow()
        self.last_active      : datetime = utcnow()



    def add_turn(
        self,
        user_message       : str,
        assistant_response : str,
        emotion            : Optional[str]  = None,
        emotion_conf       : Optional[float] = None,
        language           : Optional[str]  = None,
        intent             : Optional[str]  = None,
        crisis_flag        : bool = False,
        topics             : Optional[list] = None
    ) -> None:
        self.history.append({"role": "user",      "content": user_message})
        self.history.append({"role": "assistant", "content": assistant_response})

        # Keep only the last 6 turns (12 messages) -->  sliding window
        if len(self.history) > 12:
            self.history = self.history[-12:]

        
        if crisis_flag:
            self.prior_crisis = True

        if emotion:
            self.emotion_history.append(emotion)

        if topics:
            for t in topics:
                if t and t not in self.topics_discussed:
                    self.topics_discussed.append(t)

        self.turn_count  += 1
        self.last_active  = utcnow()

    def get_history(self) -> list:
        return self.history

    def summary(self) -> dict:
        return {
            "session_id"      : self.session_id,
            "user_id"         : self.user_id,
            "country"         : self.country,
            "turn_count"      : self.turn_count,
            "prior_crisis"    : self.prior_crisis,
            "emotion_history" : self.emotion_history,
            "topics_discussed": self.topics_discussed,
            "started_at"      : self.started_at.isoformat(),
            "last_active"     : self.last_active.isoformat()
        }





class SessionStore:
    """
    In-memory store that maps session_id to SessionMemory.
    One instance lives for the lifetime of the FastAPI app.
    """

    def __init__(self):
        self._sessions: dict[str, SessionMemory] = {}

    def create(self, user_id: int, country: str = "Unknown") -> SessionMemory:
        session_id = str(uuid.uuid4())
        session    = SessionMemory(
            session_id = session_id,
            user_id    = user_id,
            country    = country
        )
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[SessionMemory]:
        return self._sessions.get(session_id)

    def get_or_create(
        self, session_id: Optional[str], user_id: int, country: str = "Unknown"
    ) -> SessionMemory:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        return self.create(user_id, country)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_user_sessions(self, user_id: int) -> list[SessionMemory]:
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id
        ]

    def active_count(self) -> int:
        return len(self._sessions)


# Single global instance imported by app.py and pipeline.py
session_store = SessionStore()
