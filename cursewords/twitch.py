import asyncio
import logging
import os
import re
import threading
import time
import websockets


# Twitch bot secure web socket URL
TWITCH_URI = 'wss://irc-ws.chat.twitch.tv:443'

# Minimum number of seconds between posts to the chat, to avoid Twitch
# dropping messages
MESSAGE_COOLDOWN_SECS = 1


class TwitchBot(threading.Thread):
    def __init__(
            self,
            grid,
            nickname,
            channel,
            oauth_token,
            enable_guessing,
            enable_clue,
            clue_cooldown_per_person,
            log_to_file):
        self.grid = grid
        self.nickname = nickname
        self.channel = channel
        self.oauth_token = oauth_token
        self.enable_guessing = enable_guessing
        self.enable_clue = enable_clue
        self.clue_cooldown_per_person = clue_cooldown_per_person

        super().__init__(daemon=True)

        self.websocket = None
        self.running = None

        self.message_handlers = [
            (re.compile(r'PING (.*)\r\n'), self.handle_ping),
            (re.compile(r'.* PRIVMSG #(\S+) :(.*)\r\n'), self.handle_chat_msg),
            (re.compile(r'.* WHISPER (\S+) :(.*)\r\n'), self.handle_whisper),
            (re.compile(r'.* JOIN #(.*)\r\n'), self.handle_join),
            (re.compile(r'.* NOTICE #(\S*) (.*)\r\n'), self.handle_notice)
        ]

        self._outgoing_message_queue = []
        self._outgoing_message_last_time = time.monotonic()

        self.successful_guessing_users = set()

        if log_to_file:
            logging.basicConfig(
                filename='cursewords.log',
                encoding='utf-8',
                level=logging.INFO)
        else:
            logging.basicConfig(stream=os.devnull)

    def run(self):
        # If no Twitch features are enabled, don't bother connecting to Twitch.
        if (not self.enable_guessing and
                not self.enable_clue):
            return

        self.running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.connect())

    async def join_channel(self):
        assert self.websocket
        await self.websocket.send(f'PASS {self.oauth_token}\n')
        await self.websocket.send(f'NICK {self.nickname}\n')
        await self.websocket.send(f'JOIN #{self.channel}\n')
        await self.websocket.send(
            'CAP REQ :twitch.tv/tags twitch.tv/commands\n')

    async def _post_next_message(self):
        assert self.websocket
        txt = self._outgoing_message_queue.pop()
        await self.websocket.send(f'PRIVMSG #{self.channel} :{txt}\n')
        self._outgoing_message_last_time = time.monotonic()

    async def post_message(self, txt):
        self._outgoing_message_queue.insert(0, txt)

    async def send_whisper(self, user, msg):
        assert self.websocket
        # Note: Untested! This probably requires that a bot be verified.
        # Without a verified bot account, this returns an error.
        await self.post_message(f'.w {user} {msg}')

    async def connect(self):
        async with websockets.connect(TWITCH_URI, ssl=True) as websocket:
            logging.info(
                f'TwitchBot connected to #{self.channel} as {self.nickname}')
            self.websocket = websocket
            await self.join_channel()
            await self.event_loop()

    async def event_loop(self):
        try:
            await self.startup()

            while self.running:
                # Listen for incoming messages, timing out once a second to
                # process outgoing messages.
                try:
                    resp = await asyncio.wait_for(
                        self.websocket.recv(), timeout=1)
                    for (pat, func) in self.message_handlers:
                        m = pat.search(resp)
                        if m:
                            await func(*m.groups())
                except asyncio.exceptions.TimeoutError:
                    pass

                # Post an outgoing message at most every MESSAGE_COOLDOWN_SECS.
                # (Twitch does its own throttling of bots that drops messages.)
                if (self._outgoing_message_queue and
                        (time.monotonic() - self._outgoing_message_last_time >
                         MESSAGE_COOLDOWN_SECS)):
                    await self._post_next_message()

            await self.shutdown()

        except websockets.exceptions.WebSocketException:
            self.grid.send_notification(
                'Twitch connection lost, sorry')

    async def handle_ping(self, unused_domain):
        await self.websocket.send('PONG :tmi.twitch.tv\n')

    async def startup(self):
        # TODO: better start-up message announcing enabled features
        await self.post_message('Hello I\'m the bot!')

    async def handle_join(self, unused_channel_name):
        self.grid.send_notification(
            f'Connected to Twitch #{self.channel} as {self.nickname}')

    async def handle_notice(self, unused_channel_name, msg):
        logging.info(f'Twitch NOTICE: {msg}')

    async def handle_chat_msg(self, user, msg):
        cmd_m = re.match(r'\s*!(\w+)(\s+.*)?', msg)
        cmd = (None, None)
        if cmd_m:
            cmd = (cmd_m.group(1).lower(), cmd_m.group(2))

        if self.enable_clue and cmd[0] == 'clue':
            await self.do_clue(user, cmd[1])

        if self.enable_guessing and cmd[0] is None:
            await self.do_guesses(user, msg)

    async def do_clue(self, user, msg):
        m = re.match(r'\s*(?P<num>\d+)\s*(?P<dir>[aAdD])', msg)
        if not m:
            m = re.match(r'\s*(?P<dir>[aAdD])\D*\s*(?P<num>\d+)', msg)
        if m:
            num = m.group('num')
            cluedir = m.group('dir').upper()
            clue = self.grid.get_clue_by_number(
                int(num), is_across=(cluedir == 'A'))
            if clue:
                await self.post_message(f'{user} {num}{cluedir}: {clue}')
            else:
                await self.post_message(f'{user} No clue for {num}{cluedir}')

            # TODO: honor self.clue_cooldown_per_person
        else:
            await self.post_message(
                f'{user} I didn\'t understand. Try something like: !clue 22d')

    def _itemize_guesses(self, msg):
        # Search a chat message for guesses.
        #
        # A guess is one or more words that may or may not be separated by
        # spaces, case ignored. A guess begins and ends at a word boundary, and
        # does not span across punctuation.
        #
        # For example, if someone posts:
        #   DOUBLE RAINBOW, maybe?
        #
        # These words are considered guesses:
        #   double
        #   doublerainbow
        #   rainbow
        #   maybe
        phrases = re.split(r'[^\w\s]+', msg)
        for phrase in phrases:
            words = re.split(r'\W+', phrase.strip())
            for start_i in range(len(words)):
                for end_i in range(start_i + 1, len(words) + 1):
                    guess = (''.join(words[start_i:end_i])
                             .lower())
                    if guess:
                        yield guess

    async def do_guesses(self, user, msg):
        for guess in self._itemize_guesses(msg):
            if guess in self.grid.word_index:
                result = self.grid.twinkle_unsolved_word(guess)
                if result:
                    self.successful_guessing_users.add(user)

    async def handle_whisper(self, user, msg):
        # We have no whisper-based features.
        pass

    async def shutdown(self):
        if self.enable_guessing and self.successful_guessing_users:
            print('\n\n\n\n\n### Thanks to these successful solvers:\n')
            for user in sorted(self.successful_guessing_users):
                print('  ' + user)
            print('\n\n')
