"""A simple example bot.

The known commands are:

    stats -- Prints some channel information.

    leave -- Disconnect the bot.  The bot will try to reconnect after 60 seconds.

    die -- Let the bot cease to exist.
"""

import irc.bot
import irc.strings
import argparse
import time
import _thread
import random


class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channels_ = channels

    # if the nick is already taken, append an underscore
    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    # whenever we're finished connecting to the server
    def on_welcome(self, c, e):
        # connect to all the channels we want to
        for chan in self.channels_:
            c.join(chan)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        # if someone sent a line saying "mynick: command"
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            # split an trim it to get "command"
            self.do_command(e, a[1].strip())
        elif e.arguments[0].startswith('!'):
            self.do_command(e, e.arguments[0].strip())
        return

    def do_command(self, e, cmd):
        nick = e.source.nick
        c = self.connection

        if cmd == "leave":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "!remind" or cmd == "remind":
            wait_time, reminder_text = self.parse_remind(cmd)
        else:
            pass  # not understood command

    # send me the entire line, starting with !remind
    # I will give you a tuple of reminder time (in seconds), and reminder text
    @staticmethod
    def parse_remind(text):
        wait_time = 0
        finished_parsing = False
        reminder_text = ''
        if text.lower().startswith('!remind random'):
            wait_time = random.randint(1, 1000) * 60
            reminder_text = text[text.indexOf('!remind random'):].trim()
        else:
            for word in text.split(' '):
                if word.isnumeric():  # warning: this can pass through '1.2', which will throw an error on int('1.2')
                    try:
                        wait_time = int(word)
                    except ValueError:  # so we catch that if it happens, and round it back into being reasonable
                        wait_time = int(round(float(word)))
                elif wait_time and not finished_parsing:
                    if word.lower() == 'min' or word.lower() == 'mins' or word.lower() == 'minute' or word.lower == 'minutes':
                        wait_time *= 60
                    elif word.lower() == 'hr' or word.lower() == 'hrs' or word.lower() == 'hours' or word.lower == 'hour':
                        wait_time *= 60 * 60
                    elif word.lower() == 'day' or word.lower() == 'days':
                        wait_time = wait_time * 24 * 60 * 60
                    finished_parsing = True
                elif finished_parsing:
                    reminder_text += word + ' '
        return wait_time, reminder_text.trim()

    def wait_then_remind_to(self, reminder_text, reminding_location):
        pass


def parse_args():
    parser = argparse.ArgumentParser(description="runs a stupider version of the late-great swiggityspeare IRC bot")
    parser.add_argument('--server', type=str, help="Server address", required=True)
    parser.add_argument('--port', type=int, help="Server port", required=True)
    parser.add_argument('--ssl', help='[Use SSL to connect to server]', action='store_true')
    parser.add_argument('--botnick', type=str, help="Nick to use for bot", required=True)
    parser.add_argument('--channel', type=str, help='Channels to join on connect (#chan1[,#chan2,#chan3])', required=True)
    return parser.parse_args()

# Execution begins here, if called via python interpreter
if __name__ == '__main__':
    args = parse_args()
    server = args.server
    port = args.port
    ssl = args.ssl
    nick = args.botnick
    channels = args.channel.split(',')
    TestBot(channel=channels, nickname=nick, server=server, port=port)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    bot = TestBot(channel, nickname, server, port)
    bot.start()