import asyncio
from time import sleep
from typing import List
import aiohttp
import os


BILIGO_HOST = os.getenv("BILIGO_WS_URL", default="blive.ericlamm.xyz")
USE_TLS = os.getenv("USE_TLS", default="true")
VUP_LIST_URL = 'https://vup-json.laplace.live/vup-slim.json'


ID = "dd-stats-sparanoid"


async def get_room_list() -> List[int]:
    async with aiohttp.ClientSession() as session:
        async with session.get(VUP_LIST_URL) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to get room list: {resp.status}")
            vups = (await resp.json()).items()
            return [r['room'] for _, r in vups if r['room'] > 0]


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
                resp = await get_subscribed()
                if not resp or len(resp) == 0:
                    print('Subscribed is empty, resubscribing...')
                    while True:
                        try:
                            await subscribe(room_list=room_list, session=session)
                            break
                        except Exception as ex:
                            print(f'Error while subscribing: {ex}, reconnect after {5} seconds...')
                            sleep(5)
            except Exception as ex:
                print(f'Error while checking subscribing rooms: {ex}')

async def subscribe_latest_rooms(old_room_list: List[int] = []):
    async with aiohttp.ClientSession() as session:
        last_rooms = old_room_list
        while True:
            try:
                await asyncio.sleep(86400)
                print('refetching latest rooms...')
                latest_rooms = await get_room_list()
                # changed to only bigger than will resub
                if latest_rooms <= last_rooms:
                    print('no changes detected, skipped.')
                    continue
                print(f'a new change has been detected ({len(last_rooms)} -> {len(latest_rooms)}), resubscribing...')
                last_rooms = latest_rooms
                while True:
                    try:
                        await subscribe(room_list=latest_rooms, session=session)
                        break
                    except Exception as ex:
                        print(f'Error while subscribing: {ex}, reconnect after {5} seconds...')
                        sleep(5)
            except Exception as ex:
                print(f'error while fetching latest rooms: {ex}')


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
        "Authorization": ID,
        "Accept": "application/json"
    }
    async with session.post(f'{"https" if USE_TLS == "true" else "http"}://{BILIGO_HOST}/subscribe', data=payload, headers=headers) as resp:
        try:
            result = await resp.json()
            if resp.status != 200:
                raise Exception(f"Failed to subscribe: {resp.status}: {result['error']}")
            print(f'Subscribed to {len(result)} rooms')
        except Exception as ex:
            print(f'Subscribe Failed: {ex}')
            print(f'original response: {await resp.text()}')
            raise ex


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
            except Exception as ex:
                print(f'force subscribe failed: {ex}')

    try:
        await asyncio.gather(
            connect_forever(),
            subscribe_forever(room_list=room_list),
            subscribe_latest_rooms(old_room_list=room_list)
        )
    except Exception as ex:
        print(f'Error while connect to biligo-live-ws: {ex}')
        return


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
