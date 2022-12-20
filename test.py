import unittest
import aiohttp
import asyncio
import main


class TestSubscribe(unittest.IsolatedAsyncioTestCase):

    async def test_connect_ws(self):
        async with aiohttp.ClientSession() as session:
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(main.connect_ws(session=session), timeout=10)

    async def test_subscribe(self):
        async with aiohttp.ClientSession() as session:
            await main.subscribe(room_list=[255, 22361593], session=session)
            room = await main.get_subscribed()
            self.assertEqual(len(room), 2)

if __name__ == '__main__':
    unittest.main()