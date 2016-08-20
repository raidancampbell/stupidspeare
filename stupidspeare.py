"""A simple example bot.

The known commands are:

    ping -- Pongs the user

    remind -- reminds the user after a given number of seconds/minutes/hours/days

    source -- gives a link to the source code

    leave -- makes the bot part the channel

    die -- Let the bot cease to exist.
"""

import irc.bot
import irc.strings
import argparse  # parse strings from CLI invocation
import time  # unix timestamp is `int(time.time())`
import threading  # for sleeping during the !remind
import random  # for !remind random
import json


class StupidSpeare(irc.bot.SingleServerIRCBot):
    def __init__(self, json_filename):
        self.json_filename = json_filename
        with open(json_filename, 'r') as infile:
            self.json_data = json.loads(infile.read())
        irc.bot.SingleServerIRCBot.__init__(self, [(self.json_data['serveraddress'], self.json_data['serverport'])],
                                            self.json_data['botnick'], self.json_data['botrealname'])
        self.channels_ = self.json_data['channels']
        self.connection.add_global_handler('invite', self.on_invite)

    def reinstate_reminders(self, reminder_array):
        for reminder_object in reminder_array:
            reminder_object_non_serializable = reminder_object
            reminder_object_non_serializable['connection'] = self.connection
            reminder_object_non_serializable['self'] = self
            threading.Thread(target=StupidSpeare.wait_then_remind_to, kwargs=reminder_object_non_serializable).start()

    # when the bot is invited to a channel, respond by joining the channel
    def on_invite(self, connection, event):
        channel_to_join = event.arguments[0]
        connection.join(channel_to_join)
        if channel_to_join not in self.json_data['channels']:
            self.json_data['channels'].append(channel_to_join)
            self.save_json()

    def save_json(self):
        with open(self.json_filename, 'w') as outfile:
            json.dump(self.json_data, outfile, indent=2)

    # if the nick is already taken, append an underscore
    @staticmethod
    def on_nicknameinuse(connection, event):
        connection.nick(connection.get_nickname() + "_")

    # whenever we're finished connecting to the server, join the channels
    def on_welcome(self, connection, event):
        # connect to all the channels we want to
        for chan in self.channels_:
            connection.join(chan)
        time.sleep(1)
        self.reinstate_reminders(self.json_data['reminders'])

    # log private messages to stdout, and try to parse a command from it
    def on_privmsg(self, connection, event):
        message_text = event.arguments[0]
        print('PRIVMSG: ' + message_text)
        self.do_command(event, message_text)

    # log public messages to stdout, hiss on various conditions, and try to parse a command
    def on_pubmsg(self, connection, event):
        message_text = event.arguments[0]
        a = message_text.split(":", 1)
        # if someone sent a line saying "mynick: command"
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            # split an trim it to get "command"
            self.do_command(event, a[1].strip())
        elif message_text.startswith('!'):
            self.do_command(event, message_text.strip())
        # hiss at buzzfeed/huffpost, characters greater than 128, and on the word 'moist'
        if 'buzzfeed.com' in message_text or 'huffingtonpost.com' in message_text:
            connection.privmsg(event.target, 'hisss fuck off with your huffpost buzzfeed crap')
        elif not all(ord(c) < 128 for c in event.arguments[0]) or 'moist' in message_text:
            connection.privmsg(event.target, 'hisss')
        print('PUBMSG: ' + event.arguments[0])

    # performs the various commands documented at the top of the file
    def do_command(self, event, cmd_text):
        connection = self.connection

        if cmd_text == "leave" or cmd_text == "!leave":  # respond to !leave
            if event.target in self.json_data['channels']:
                self.json_data['channels'].remove(event.target)
                self.save_json()
            connection.part(event.target)
        elif cmd_text == "die" or cmd_text == "!die":  # respond to !die
            if event.source.nick == self.json_data['botownernick']:
                self.die()
            else:
                connection.privmsg(event.target,
                                   event.source.nick + ": you're not " + self.json_data['botownernick'] + '!')
        elif cmd_text == "ping" or cmd_text == "!ping":  # respond to !ping
            connection.privmsg(event.target, event.source.nick + ': ' + "Pong!")
        elif cmd_text == "source" or cmd_text == "!source":  # respond to !source
            connection.privmsg(event.target,
                               event.source.nick + ': ' + "https://github.com/raidancampbell/stupidspeare")
        elif cmd_text.startswith("remind") or cmd_text.startswith("!remind"):  # respond to !remind
            wait_time, reminder_text = self.parse_remind(cmd_text)
            if reminder_text:
                reminder_object = {'channel': event.target, 'remindertext': event.source.nick + ': ' + reminder_text,
                                   'remindertime': int(time.time()) + wait_time}
                self.json_data['reminders'].append(reminder_object)
                self.save_json()
                reminder_object_non_serializable = reminder_object
                reminder_object_non_serializable['connection'] = connection  # add the connection object
                reminder_object_non_serializable['self'] = self
                threading.Thread(target=StupidSpeare.wait_then_remind_to,
                                 kwargs=reminder_object_non_serializable).start()
            else:
                connection.privmsg(event.target, event.source.nick + ': ' +
                                   'Usage is "!remind [in] 5 (second[s]/minute[s]/hour[s]/day[s]) reminder text"')
        else:
            pass  # not understood command

    # send me the entire line, starting with !remind
    # I will give you a tuple of reminder time (in seconds), and reminder text
    # if parsing fails, expect the reminder text to be empty
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

    # waits the given time, then will issue a reminder on the given channel to the given nick with the given text
    # kwargs should contain: 'connection', 'channel', 'remindertime', and 'reminder_text'
    # this function is meant to be forked off into a separate thread: it will sleep until it's ready to respond
    def wait_then_remind_to(**kwargs):
        # how many seconds away are we from the targeted reminding time
        wait_time_s = kwargs['remindertime'] - int(time.time())
        if wait_time_s > 0:  # if we still have time, then log it and let them know
            print('>> sending "' + kwargs['remindertext'] + '" in ' + str(wait_time_s // 60) + ' minutes')
            kwargs['connection'].privmsg(kwargs['channel'], "Okay, I'll remind you about " + kwargs['remindertext'])
        else:  # if we don't, then log it and let them know
            print('>> was supposed to send "' + kwargs['remindertext'] + '" ' + str(wait_time_s // 60) + ' minutes ago')
            kwargs['connection'].privmsg(kwargs['channel'], 'I missed a reminder while offline!')
        if wait_time_s > 0:
            time.sleep(wait_time_s)
        kwargs['connection'].privmsg(kwargs['channel'], kwargs['remindertext'])
        kwargs['self'].json_data['reminders'] = list(
            filter(lambda x: x['remindertime'] != kwargs['remindertime'], kwargs['self'].json_data['reminders']))
        kwargs['self'].save_json()


# parse args from command line invocation
def parse_args():
    parser = argparse.ArgumentParser(description="runs a stupider version of the late-great swiggityspeare IRC bot")
    parser.add_argument('--json_filename', type=str, help="Filename of the json configuration file [stupidspeare.json]",
                        required=False)
    return parser.parse_args()


# Execution begins here, if called via command line
if __name__ == '__main__':
    args = parse_args()
    json_filename_ = args.json_filename or 'stupidspeare.json'
    bot = StupidSpeare(json_filename=json_filename_)
    bot.start()
