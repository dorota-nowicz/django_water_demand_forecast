#!/usr/bin/env python
#
# Python >= 3.5
import os
import asyncio
import asyncpg
from aiohttp import web, WSCloseCode

def callback_websocket(ws):
    def callback(connection, pid, channel, payload):
        asyncio.ensure_future(ws.send_str(payload))
    return callback

async def websocket_handler(request):
    channel = request.match_info.get('channel', 'postgresql2websocket')
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    request.app['websockets'].append(ws)
    pool = request.app['pool']
    async with pool.acquire() as connection:
        await connection.add_listener(channel, callback_websocket(ws))
        try:
            async for msg in ws:
                pass
        finally:
            request.app['websockets'].remove(ws)
    return ws

async def init_app():
    app = web.Application()
    app['pool'] = await asyncpg.create_pool(
                    database=os.environ["DB_NAME"], 
                    #port =8080,#os.environ["APP_PORT"],
                    user=os.environ["DB_USERNAME"], 
                    password=os.environ["DB_PASSWORD"], 
                    host=os.environ["DB_HOSTNAME"], 
                )
    app.router.add_route('GET', '/{channel}', websocket_handler)
    return app

async def on_shutdown(app):
    for ws in app['websockets']:
        await ws.close(code=WSCloseCode.GOING_AWAY,
            message='Server shutdown')

def main():

    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app())
    app['websockets'] = []
    app.on_shutdown.append(on_shutdown)
    try:
        web.run_app(app,
            host = '0.0.0.0',
            port = os.environ["SOCKET_PORT"],
        )
    except KeyboardInterrupt:
        pass
    finally:
        for task in asyncio.Task.all_tasks():
            task.cancel()
        loop.close()

if __name__ == '__main__':
    main()
