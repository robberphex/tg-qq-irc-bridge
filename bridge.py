import asyncio
import json

import aiohttp
from aiohttp import ClientWebSocketResponse

from bottom import Client

loop = asyncio.get_event_loop()

session = aiohttp.ClientSession()

from config import config

tele_queue = asyncio.Queue()
qq_queue = asyncio.Queue()
irc_queue = asyncio.Queue()


async def event(base_uri):
    async with session.ws_connect(base_uri + '/event/') as ws:  # type: ClientWebSocketResponse
        api_ws = await session.ws_connect(base_uri + '/api/')
        while True:
            message = await ws.receive_json()
            if message['post_type'] == "message" and message['message_type'] == "group" \
                    and 'group_id' in message and message['group_id'] == config['QQ']['group_id']:
                call = {
                    "action": "get_group_member_info",
                    "params": {
                        "group_id": config['QQ']['group_id'],
                        "user_id": message['user_id'],
                        "no_cache": "true"
                    }
                }
                await api_ws.send_json(call)
                resp = await api_ws.receive_json()
                author = resp['data']['card']
                if not author:
                    author = resp['data']['nickname']
                final_msg = '[QQ- ' + author + '] ' + message['message']
            elif message['post_type'] == "event":
                if message['event'] == "group_decrease":
                    if message['sub_type'] == "leave":
                        final_msg = '<-- QQ: ' + str(message['user_id']) + ' 离开群聊'
                    elif message['sub_type'] in ["kick", "kick_me"]:
                        final_msg = '<-- QQ: ' + str(message['user_id']) + ' 被踢出群聊'
                elif message['event'] == "group_increase":
                    call = {
                        "action": "get_group_member_info",
                        "params": {
                            "group_id": config['QQ']['group_id'],
                            "user_id": message['user_id'],
                            "no_cache": "true"
                        }
                    }
                    await api_ws.send_json(call)
                    resp = await api_ws.receive_json()
                    author = resp['data']['card']
                    if not author:
                        author = resp['data']['nickname']
                    final_msg = '<-- QQ: ' + author + '(' + str(message['user_id']) + ') 已加入群聊'
            else:
                continue
            await tele_queue.put(final_msg)
            await irc_queue.put(final_msg)


async def api(base_uri):
    async with session.ws_connect(base_uri + '/api/') as ws:  # type: ClientWebSocketResponse
        while True:
            raw_msg = await qq_queue.get()
            data = {
                "action": "send_group_msg",
                "params": {
                    "group_id": config['QQ']['group_id'],
                    "message": raw_msg,
                    "auto_escape": "false"
                }
            }
            await ws.send_json(data)
            resp = await ws.receive_json()
            print(resp)


async def telebot_recv():
    url = 'https://api.telegram.org/bot{0}'.format(config['telegram']['token'])
    message_id = None
    while True:
        if message_id:
            act_url = url + '/getUpdates?timeout=5&offset=' + str(message_id)
        else:
            act_url = url + '/getUpdates?timeout=5'
        resp = await session.get(act_url, proxy=config['http_proxy'])
        resp = await resp.read()
        resp = json.loads(resp.decode())
        for message in resp['result']:
            message = message['message']
            from_user = '[Tele- ' + message['from']['first_name'] + ' ' + message['from']['last_name'] + ']'
            final_msg = from_user + ': ' + message['text']
            await qq_queue.put(final_msg)
            await irc_queue.put(final_msg)
        if len(resp['result']) > 0:
            message_id = resp['result'][-1]['update_id'] + 1


async def telebot():
    url = 'https://api.telegram.org/bot{0}'.format(config['telegram']['token'])
    resp = await session.get(url + '/getMe', proxy=config['http_proxy'])
    resp = await resp.read()
    resp = resp.decode()  # type: str
    resp = resp.strip()

    while True:
        message = await tele_queue.get()
        resp = await session.get(
            url + '/sendMessage?chat_id=' + config['telegram']['chat_id'] + "&text=" + message,
            proxy=config['http_proxy']
        )
        resp = await resp.read()
        resp = json.loads(resp.decode())
        print(resp)


bot = Client(config['irc']['server'], 6667, ssl=False)


@bot.on('CLIENT_CONNECT')
async def connect(**kwargs):
    bot.send('NICK', nick=config['irc']['nick'])
    bot.send('USER', user=config['irc']['nick'], realname=config['irc']['nick'])
    bot.send('PRIVMSG',target='x', message='/msg NickServ identify fedora_zh_bot ' + config['irc']['password'])

    # Don't try to join channels until the server has
    # sent the MOTD, or signaled that there's no MOTD.
    done, pending = await asyncio.wait(
        [bot.wait("RPL_ENDOFMOTD"),
         bot.wait("ERR_NOMOTD")],
        loop=bot.loop,
        return_when=asyncio.FIRST_COMPLETED
    )

    # Cancel whichever waiter's event didn't come in.
    for future in pending:
        future.cancel()

    bot.send('JOIN', channel=config['irc']['channel'])


@bot.on('PING')
def keepalive(message, **kwargs):
    bot.send('PONG', message=message)


@bot.on('PRIVMSG')
async def message(nick, target, message, **kwargs):
    """ Echo all messages """
    # don't echo self
    if nick == config['irc']['nick']: return
    msg = '[IRC- {0}] {1}'.format(nick, message)
    await qq_queue.put(msg)
    await tele_queue.put(msg)


bot.loop.create_task(bot.connect())


async def irc_send(bot):
    while True:
        msg = await irc_queue.get()
        print(msg)
        bot.send("PRIVMSG", target=config['irc']['channel'], message=msg)


tasks = [
    asyncio.async(api(config['QQ']['base_uri'])),
    asyncio.async(event(config['QQ']['base_uri'])),
    asyncio.async(telebot_recv()),
    asyncio.async(telebot()),
    asyncio.async(irc_send(bot)),
]

loop.run_until_complete(asyncio.wait(tasks))
