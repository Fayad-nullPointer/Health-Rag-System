from threading import Event, Lock

RAG_READY_EVENT = Event()
RAG_INIT_LOCK = Lock()
