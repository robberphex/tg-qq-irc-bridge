import asyncio
from bottom import Client


def create_irc_bot(server, port, ssl, nick, channel, blacklist=[], password=None, loop=None):
    if not loop:
        loop = asyncio.get_event_loop()

    bot = Client(server, port, ssl=ssl, loop=loop)
    receive_queue = asyncio.Queue()

    @bot.on('CLIENT_CONNECT')
    async def connect(**kwargs):
        bot.send('NICK', nick=nick)
        bot.send('USER', user=nick, realname=nick)
        if password:
            bot.send(
                'PRIVMSG',
                target='x',
                message='/msg NickServ identify {nick} {password}'.format(nick=nick, password=password)
            )

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

        bot.send('JOIN', channel=channel)

    @bot.on('PING')
    def keepalive(message, **kwargs):
        bot.send('PONG', message=message)

    @bot.on('PRIVMSG')
    async def message(nick, target, message, **kwargs):
        print('recv from irc:')
        print({'nick': nick, 'target': target, 'message': message})
        if target != channel: return
        if nick in blacklist: return
        msg = '[{nick}] {msg}'.format(nick=nick, msg=message)
        await receive_queue.put(msg)

    loop.create_task(bot.connect())

    send_queue = asyncio.Queue()

    async def irc_send(bot):
        while True:
            msg = await send_queue.get()
            bot.send("PRIVMSG", target=channel, message=msg)

    loop.create_task(irc_send(bot))

    return receive_queue, send_queue
