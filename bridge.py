import asyncio
import json

import aiohttp

from bots.irc_bot import create_irc_bot
from bots.qq_bot import create_qq_bot
from bots.telegram_bot import create_telegram_bot
from config import config


def qq(config, loop):
    irc_conf = config.get('irc', {})
    irc_conf = {**irc_conf, **config['QQ'].get('irc')}

    qq_recv, qq_send = create_qq_bot(config['QQ']['base_uri'], config['QQ']['group_id'])
    irc_recv, irc_send = create_irc_bot(
        irc_conf['server'],
        irc_conf['port'],
        irc_conf.get('ssl', False),
        irc_conf['nick'],
        irc_conf['channel'],
        irc_conf['blacklist'],
        irc_conf.get('password')
    )

    async def qq_irc():
        while True:
            msg = await qq_recv.get()
            await irc_send.put(msg)

    async def irc_qq():
        while True:
            msg = await irc_recv.get()
            await qq_send.put(msg)

    loop.create_task(qq_irc())
    loop.create_task(irc_qq())


def telegram(config, loop):
    irc_conf = config.get('irc', {})
    irc_conf = {**irc_conf, **config['Telegram'].get('irc')}

    tele_recv, tele_send = create_telegram_bot(
        config['Telegram']['token'],
        config['Telegram']['chat_id'],
        config['Telegram'].get('blacklist', []),
        http_proxy=config['Telegram'].get('http_proxy'),
    )
    irc_recv, irc_send = create_irc_bot(
        irc_conf['server'],
        irc_conf['port'],
        irc_conf.get('ssl', False),
        irc_conf['nick'],
        irc_conf['channel'],
        irc_conf['blacklist'],
        irc_conf.get('password')
    )

    async def tele_irc():
        while True:
            msg = await tele_recv.get()
            await irc_send.put(msg)

    async def irc_tele():
        while True:
            msg = await irc_recv.get()
            await tele_send.put(msg)

    loop.create_task(tele_irc())
    loop.create_task(irc_tele())


def main():
    loop = asyncio.get_event_loop()
    qq(config, loop)
    telegram(config, loop)
    loop.run_forever()


if __name__ == '__main__':
    main()
