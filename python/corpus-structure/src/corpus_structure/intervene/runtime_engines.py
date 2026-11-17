"""Purpose-owned engines retained only for an active MCP lifespan."""

from contextlib import ExitStack, contextmanager
from threading import RLock


class McpRuntimeEngines:
    def __init__(self, settings, application_name, *, read_engine=None):
        self.settings = settings
        self.application_name = application_name
        self.read_engine = read_engine
        self._resources = None
        self._engines = {}
        self._lock = RLock()

    @contextmanager
    def lifespan(self):
        with self._lock:
            if self._resources is not None:
                raise RuntimeError("MCP engine lifespan is already active")
            self._resources = ExitStack()
        try:
            from corpus_structure.orchestrate.execution_host import execution_host_scope

            with execution_host_scope():
                yield self
        finally:
            with self._lock:
                resources, self._resources = self._resources, None
                self._engines.clear()
                resources.close()

    def engine(self, purpose="read"):
        if purpose not in {"read", "write", "admit"}:
            raise ValueError("unsupported MCP engine purpose")
        if purpose == "read" and self.read_engine is not None:
            return self.read_engine
        with self._lock:
            if self._resources is None:
                raise RuntimeError("MCP engine acquisition requires an active lifespan")
            if purpose not in self._engines:
                from corpus_structure.semantic.runtime import open_runtime_engine

                self._engines[purpose] = self._resources.enter_context(
                    open_runtime_engine(
                        self.settings,
                        self.application_name
                        if purpose == "write"
                        else self.application_name + "-" + purpose,
                        max_size=self.settings.database.pool_max_size,
                        purpose=purpose,
                    )
                )
            return self._engines[purpose]
