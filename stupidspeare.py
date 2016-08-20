"""A simple example bot.

The known commands are:

    ping -- Pongs the user

    remind -- reminds the user after a given number of seconds/minutes/hours/days

    source -- gives a link to the source code

    leave -- Disconnect the bot.  The bot will try to reconnect after 60 seconds.

    die -- Let the bot cease to exist.
"""

import irc.bot
import irc.strings
import argparse
import time
import threading
import random


class TestBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channels_, nickname, server, port):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channels_ = channels_
        self.connection.add_global_handler('invite', self.on_invite)

    @staticmethod
    def on_invite(connection, event):
        connection.join(event.arguments[0])

    # if the nick is already taken, append an underscore
    @staticmethod
    def on_nicknameinuse(connection, event):
        connection.nick(connection.get_nickname() + "_")

    # whenever we're finished connecting to the server
    def on_welcome(self, connection, event):
        # connect to all the channels we want to
        for chan in self.channels_:
            connection.join(chan)

    def on_privmsg(self, connection, event):
        print('PRIVMSG: ' + event.arguments[0])
        self.do_command(event, event.arguments[0])

    def on_pubmsg(self, connection, e):
        message_text = e.arguments[0]
        a = message_text.split(":", 1)
        # if someone sent a line saying "mynick: command"
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            # split an trim it to get "command"
            self.do_command(e, a[1].strip())
        elif message_text.startswith('!'):
            self.do_command(e, message_text.strip())
        # hiss at buzzfeed/huffpost, characters greater than 128, and on the word 'moist'
        if 'buzzfeed.com' in message_text or 'huffingtonpost.com' in message_text:
            connection.privmsg(e.target, 'hisss fuck off with your huffpost buzzfeed crap')
        elif not all(ord(c) < 128 for c in e.arguments[0]) or 'moist' in message_text:
            connection.privmsg(e.target, 'hisss')
        print('PUBMSG: ' + e.arguments[0])

    def do_command(self, event, cmd_text):
        connection = self.connection

        if cmd_text == "leave" or cmd_text == "!leave":
            connection.part(event.target)
        elif cmd_text == "die" or cmd_text == "!die":
            connection.privmsg(event.target, event.source.nick + ': ' + "disabled until owner privs are implemented")
            # self.die()
        elif cmd_text == "ping" or cmd_text == "!ping":
            connection.privmsg(event.target, event.source.nick + ': ' + "Pong!")
        elif cmd_text == "source" or cmd_text == "!source":
            connection.privmsg(event.target,
                               event.source.nick + ': ' + "https://github.com/raidancampbell/stupidspeare")
        elif cmd_text.startswith("remind") or cmd_text.startswith("!remind"):
            wait_time, reminder_text = self.parse_remind(cmd_text)
            kwargs = {'wait_time_s': wait_time, 'reminder_text': reminder_text, 'connection': connection,
                      'channel': event.target, 'nick': event.source.nick}
            if reminder_text:
                threading.Thread(target=TestBot.wait_then_remind_to, kwargs=kwargs).start()
            else:
                connection.privmsg(event.target, event.source.nick + ': ' +
                                   'Usage is "!remind [in] 5 (second[s]/minute[s]/hour[s]/day[s]) reminder text"')
        else:
            pass  # not understood command

    # send me the entire line, starting with !remind
    # I will give you a tuple of reminder time (in seconds), and reminder text
    @staticmethod
    def parse_remind(text):
        wait_time = 0
        finished_parsing = False
        reminder_text = ''
        text = text[1:] if text.startswith('!') else text
        if text.lower().startswith('remind random'):
            wait_time = random.randint(1, 1000) * 60
            reminder_text = text[text.index('remind random') + len('remind random'):]
        else:
            for word in text.split(' '):
                if word.isnumeric():  # we parse it into a float now, and round it at the end
                    try:  # grab the time
                        wait_time = float(word)
                    except ValueError:
                        print('ERR: failed to parse: ' + word + ' into a float!')
                        return 0, ''
                elif wait_time and not finished_parsing:  # we grabbed the time, but need the units
                    if word.lower() in ['min', 'mins', 'minute', 'minutes']:
                        wait_time *= 60
                    elif word.lower() in ['hr', 'hrs', 'hours', 'hour']:
                        wait_time *= 60 * 60
                    elif word.lower() in ['day', 'days']:
                        wait_time = wait_time * 24 * 60 * 60
                    finished_parsing = True
                elif finished_parsing:
                    reminder_text += word + ' '
        return int(round(wait_time)), reminder_text.strip()  # round the time back from a float into an int

    @staticmethod
    def wait_then_remind_to(**kwargs):
        print('>>reminding about ' + kwargs['reminder_text'] + ' in ' + str(kwargs['wait_time_s'] // 60) + ' minutes')
        kwargs['connection'].privmsg(kwargs['channel'], "Okay, I'll remind you about " + kwargs['reminder_text'])
        time.sleep(kwargs['wait_time_s'])
        kwargs['connection'].privmsg(kwargs['channel'], kwargs['nick'] + ': ' + kwargs['reminder_text'])


def parse_args():
    parser = argparse.ArgumentParser(description="runs a stupider version of the late-great swiggityspeare IRC bot")
    parser.add_argument('--server', type=str, help="Server address", required=True)
    parser.add_argument('--port', type=int, help="Server port", required=True)
    parser.add_argument('--botnick', type=str, help="Nick to use for bot", required=True)
    parser.add_argument('--channel', type=str, help='Channels to join on connect (#chan1[,#chan2,#chan3])',
                        required=True)
    return parser.parse_args()


# Execution begins here, if called via python interpreter
if __name__ == '__main__':
    args = parse_args()
    server_ = args.server
    port_ = args.port
    nick = args.botnick
    channels = args.channel.split(',')
    bot = TestBot(channels_=channels, nickname=nick, server=server_, port=port_)
    bot.start()
