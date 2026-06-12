import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404

from .models import Session, SessionStatus
from .serializers import SessionDetailSerializer


class SessionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket acessado em: ws://<host>/ws/session/<public_token>/
    - Operador e responsável se conectam ao mesmo grupo.
    - A cada segundo, envia o estado atualizado (remaining_seconds, status).
    - Quando o servidor chama broadcast_session(), todos recebem também.
    """

    async def connect(self):
        self.public_token = self.scope["url_route"]["kwargs"]["public_token"]
        self.group_name = f"session_{self.public_token}"

        # Verifica se a sessão existe
        session = await self.get_session()
        if session is None:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Inicia loop de tick a cada segundo
        self.tick_task = asyncio.ensure_future(self.tick_loop())

    async def disconnect(self, close_code):
        if hasattr(self, "tick_task"):
            self.tick_task.cancel()
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def tick_loop(self):
        """Envia estado da sessão a cada segundo enquanto estiver running."""
        try:
            while True:
                await asyncio.sleep(1)
                session = await self.get_session()
                if session is None:
                    break
                data = await self.serialize_session(session)
                await self.send(text_data=json.dumps({"type": "tick", "data": data}))

                # Encerra o loop se acabou o tempo
                if session.status in [SessionStatus.FINISHED, SessionStatus.EXPIRED]:
                    break
                if session.status == SessionStatus.RUNNING and session.remaining_seconds <= 0:
                    await self.expire_session(session)
                    break
        except asyncio.CancelledError:
            pass

    # ── Recebe broadcasts do servidor (via broadcast_session) ────────────────
    async def session_update(self, event):
        await self.send(text_data=json.dumps({"type": "update", "data": event["data"]}))

    # ── Helpers DB ───────────────────────────────────────────────────────────
    @database_sync_to_async
    def get_session(self):
        try:
            return Session.objects.select_related("child").get(public_token=self.public_token)
        except Session.DoesNotExist:
            return None

    @database_sync_to_async
    def serialize_session(self, session):
        # Re-fetch para pegar valores calculados frescos
        session.refresh_from_db()
        return SessionDetailSerializer(session).data

    @database_sync_to_async
    def expire_session(self, session):
        session.status = SessionStatus.EXPIRED
        session.save(update_fields=["status"])
