import asyncio
import json, logging
from django.contrib.auth import get_user_model


from .models import Thread, ChatMessage

class ChatConsumer(AsnycConsumer):
    async def websocket_connect(self, event):
        logging.debug("connected", event)

    async def websocket_recive(self, event):
        # when the message is recived from socket
        logging.debug("recive", event)

    async def websocket_disconnect(self,event):
        # when the socket connects
        logging.debug("disconnected", event)