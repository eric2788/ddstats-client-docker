import asyncio
from time import sleep
from typing import List
import aiohttp
import os


BILIGO_HOST = os.getenv("BILIGO_WS_URL", "blive.ericlamm.xyz")
USE_TLS = os.getenv("USE_TLS", "true")
VUP_LIST_URL = 'https://vup-json.bilibili.ooo/vup-room.json'


ID = "dd-stats-sparanoid"


async def get_room_list() -> List[int]:
    async with aiohttp.ClientSession() as session:
        async with session.get(VUP_LIST_URL) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get room list: {resp.status}")
            vups = (await resp.json()).items()
            return [r['room_id'] for _, r in vups if r['room_id'] > 0]


async def get_subscribed():
    headers = {"Authorization": ID}
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{"https" if USE_TLS == "true" else "http"}://{BILIGO_HOST}/subscribe', headers=headers) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get subscribed: {resp.status}")
            return await resp.json()


async def subscribe_forever(room_list: List[int]):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await asyncio.sleep(60)
                print(f'Checking subscribed rooms...')
                resp = await get_subscribed()
                if not resp or len(resp) == 0:
                    print(f'Subscribed is empty, resubscribing...')
                    rooms = room_list
                    try:
                        rooms = await get_room_list()
                        print(f'Successfully fetched latest rooms ({len(rooms)})')
                    except e:
                        print(f'error while fetching latest rooms: {e}, use back old fetched room list ({len(rooms)})')
                        rooms = room_list

                    while True:
                        try:
                            await subscribe(room_list=rooms, session=session)
                            break
                        except Exception as e:
                            print(f'Reconnect after {5} seconds...')
                            sleep(5)
                else:
                    print(f'Subscribing {len(resp)} rooms')
            except Exception as e:
                print(f'Error while checking subscribing rooms: {e}')


async def connect_forever():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                await connect_ws(session=session)
            except Exception as e:
                print(
                    f'Error while subscribing and connecting: {e}')
            finally:
                print(f'Reconnect after {5} seconds...')
                await asyncio.sleep(5)


async def connect_ws(session: aiohttp.ClientSession):
    print(f'connecting to websocket {BILIGO_HOST}...')
    async with session.ws_connect(f'{"wss" if USE_TLS == "true" else "ws"}://{BILIGO_HOST}/ws?id={ID}') as ws:
        print(f'connected to websocket {BILIGO_HOST}')
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.CLOSE or msg.type == aiohttp.WSMsgType.CLOSED:
                print('Websocket closed')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print('Websocket error: ',
                      ws.exception())


async def subscribe(room_list: List[int], session: aiohttp.ClientSession):
    print(f'prepared to subscribe to {len(room_list)} rooms')
    payload = {"subscribes": room_list}
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": ID
    }
    async with session.post(f'{"https" if USE_TLS == "true" else "http"}://{BILIGO_HOST}/subscribe', data=payload, headers=headers) as resp:
        if resp.status != 200:
            raise Exception(f"Failed to subscribe: {resp.status}: {(await resp.json())['error']}")
        result = await resp.json()
        print(f'Subscribed to {len(result)} rooms')


async def main():
    room_list = []
    try:
        room_list = await get_room_list()
    except Exception as e:
        print(f'Failed to get room list: {e}')
        return

    if os.getenv('FORCE_SUBSCRIBE_FIRST') == 'true':
        async with aiohttp.ClientSession() as session:
            try:
                await subscribe(room_list=room_list, session=session)
                print(f'successfully force subscribed on first ({len(room_list)} rooms)')
            except e:
                print(f'force subscribe failed: {e}')

    try:
        await asyncio.gather(
            connect_forever(),
            subscribe_forever(room_list=room_list)
        )
    except Exception as e:
        print(f'Error while connect to biligo-live-ws: {e}')
        return


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
