# tg-qq-irc-bridge

在Telegram、QQ、IRC之间转发消息的应用

## 如何安装

1. 准备qq coolq-http-api 服务

    可以参考<https://github.com/RobberPhex/docker-wine-coolq>

2. 申请tele bot

    可以参考<https://core.telegram.org/bots#3-how-do-i-create-a-bot>

3. 配置文件：

    ```python
    # config.py
    config = {
        'irc': {
            # 一些irc的基础连接参数
            'server': 'chat.freenode.net',
            'port': 6697,
            'ssl': True,
            'channel': '#bot-test',
            'blacklist': [
                'another_bot'
            ]
        },
        'Telegram': {
            # tg使用的http代理（可选）
            'http_proxy': 'http://127.0.0.1:8008/',
            # tg bot的token
            'token': '123456:abcdefgABCDEFG',
            # 需要转发的群id
            'chat_id': '-1234567',
            # 不转发的机器人id列表
            'blacklist': [
                '123456'
            ],
            # tg和irc互联时，irc的配置
            'irc': {
                'nick': 'telegram_bot',
                'password': 'password_telegram',
            },
        },
        'QQ': {
            # qq群id
            'group_id': 653148038,
            # coolq-http-api中，websocket的连接地址
            'base_uri': 'ws://127.0.0.1:6700',
            # qq和irc互联时，irc的配置
            'irc': {
                'nick': 'tencent_qq_bot',
                'password': 'password_qq',
            },
            # 不转发的qq号
            'blacklist': [
                '123456789'
            ],
        },
    }
    ```

4. 运行

    ````bash
    python bridge.py
    ````

## 转发逻辑

以上面的配置为例

| 源头     | 目标     | 消息                          | 发送人            |
|:---------|:---------|:------------------------------|:------------------|
| irc      | Telegram | [irc_id] msg                  | tele_bot@Telegram |
| Telegram | irc      | [tele_name] msg               | telegram_bot      |
| irc      | QQ       | [irc_id] msg                  | qq_bot账号        |
| QQ       | irc      | [qq_nick] msg                 | tencent_qq_bot    |
| Telegram | QQ       | [telegram_bot][tele_name] msg | qq_bot账号        |
| QQ       | Telegram | [tencent_qq_bot][qq_nick] msg | tele_bot@Telegram |
