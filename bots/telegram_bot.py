import asyncio
import json

import aiohttp


def create_telegram_bot(token, chat_id, blacklist=[], http_proxy=None, loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    receive_queue = asyncio.Queue()
    send_queue = asyncio.Queue()

    session = aiohttp.ClientSession()

    async def recv_msg():
        url = 'https://api.telegram.org/bot{0}'.format(token)
        message_id = None
        while True:
            if message_id:
                act_url = url + '/getUpdates?timeout=10&offset=' + str(message_id)
            else:
                act_url = url + '/getUpdates?timeout=10'
            resp = await session.get(act_url, proxy=http_proxy)
            resp = await resp.read()
            resp = json.loads(resp.decode())
            for message in resp['result']:
                message = message['message']
                print('recv from telegram:')
                print(message)
                if message['from']['id'] in blacklist:
                    continue
                if 'username' in message['from']:
                    author = message['from']['username']
                elif 'last_name' in message['from']:
                    author = '{first_name} {last_name}'.format(
                        first_name=message['from']['first_name'],
                        last_name=message['from']['last_name'],
                    )
                else:
                    author = message['from']['first_name']
                final_msg = '[{author}] {msg}'.format(
                    author=author,
                    msg=message['text'],
                )
                await receive_queue.put(final_msg)
            if len(resp['result']) > 0:
                message_id = resp['result'][-1]['update_id'] + 1

    async def send_msg():
        url = 'https://api.telegram.org/bot{0}'.format(token)
        resp = await session.get(url + '/getMe', proxy=http_proxy)
        resp = await resp.read()
        resp = resp.decode()  # type: str
        resp = resp.strip()

        while True:
            message = await send_queue.get()
            resp = await session.get(
                url + '/sendMessage?chat_id=' + chat_id + "&text=" + message,
                proxy=http_proxy
            )
            resp = await resp.read()
            resp = json.loads(resp.decode())
            print(resp)

    loop.create_task(recv_msg())
    loop.create_task(send_msg())

    return receive_queue, send_queue
