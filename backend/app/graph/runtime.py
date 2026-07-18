import logging
from contextlib import AbstractAsyncContextManager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.core.config import settings
from app.graph.builder import build_graph

logger = logging.getLogger(__name__)


class GraphRuntime:
    def __init__(self) -> None:
        self.graph = build_graph()
        self._postgres_context: AbstractAsyncContextManager[AsyncPostgresSaver] | None = (
            None
        )

    async def initialize(self) -> None:
        if not settings.langgraph_postgres_checkpointer:
            return
        connection_string = settings.sqlalchemy_database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        context = AsyncPostgresSaver.from_conn_string(connection_string)
        try:
            saver = await context.__aenter__()
            await saver.setup()
        except Exception as exc:
            logger.warning("Postgres checkpointer unavailable; using memory: %s", exc)
            try:
                await context.__aexit__(type(exc), exc, exc.__traceback__)
            except Exception:
                pass
            return
        self._postgres_context = context
        self.graph = build_graph(saver)

    async def close(self) -> None:
        if self._postgres_context is not None:
            await self._postgres_context.__aexit__(None, None, None)
            self._postgres_context = None


graph_runtime = GraphRuntime()
