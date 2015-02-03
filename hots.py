import requests
import re
import sqlite3 as lite
import yaml
import os
from bs4 import BeautifulSoup
from willie.module import commands, example, event, rule, interval
from willie.formatting import underline
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process, Queue

parameters = yaml.load(open(os.path.expanduser('~') + '/.willie/hots_parameters.yml', 'r'))

filename = parameters['database_file']
bot_commands = parameters['commands']
key = parameters['key']


def set_up_db():
    willie_database = lite.connect(filename)
    c = willie_database.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS BattleTag (irc text, bnet text)')
    willie_database.commit()
    willie_database.close()


def get_command_help_message(command):
    message = underline(bot_commands[command]['example'])
    if 'alias' in bot_commands[command]:
        message += ' — alias !' + bot_commands[command]['alias']
    message += ' — ' + bot_commands[command]['help']
    return message

message_queue = Queue()

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        message_queue.put('I\'m being updated, brb!')

def serve_forever(server):
    server.serve_forever()

def setup(bot):
    server = HTTPServer(("", parameters['http_server']['port']), WebhookHandler)
    Process(target=serve_forever, args=(server,)).start()

@interval(5)
def poll_queue(bot):
    while True:
        try:
            message = message_queue.get()
            for channel in bot.config.core.channels:
                bot.msg(channel, message)
        except Exception as e:
            print(e)
            break

@event('001')
@rule('.*')
def startup(bot, trigger):
    bot.write(['AUTH', bot.nick, key])
    bot.write(['MODE', bot.nick, "+x"])

@commands('commands')
def show_commands(bot, trigger):
    ircname = trigger.nick

    bot.msg(ircname, "Here's a list of my commands:")

    for command, command_options in bot_commands.items():
        message = get_command_help_message(command)
        bot.msg(ircname, message)


@commands('tips')
@example('!tips Wobbley')
def tips(bot, trigger):
    """
    Links the tips section of the HotS GitHub.io page to the username referenced
    """
    url = 'http://heroesofthestorm.github.io/tips'
    if not trigger.group(2):
        bot.say("Tips can be found here: {0}".format(url))
    else:
        user = trigger.group(2).replace(" ", "")
        bot.say("You can find some great tips here, {0}: {1}".format(user, url))


@commands('tierlist', 'tl')
@example('!tierlist')
def tierlist(bot, trigger):
    """
    Replies with the url for Zuna's tierlist
    """
    bot.reply('http://heroesofthestorm.github.io/zuna-tierlist')


@commands('rating')
@example('!rating Wobbley')
def hotslogs_rating(bot, trigger):
    """
    Replies with a list of players with the given BattleTag from HotsLogs in the following format:
    <playername> [<region>] - <division> [<mmr>]
    :param trigger: Expected to contain a player name in trigger.group(2)
    """
    count = 0
    if not trigger.group(2):
        return
    player_name = trigger.group(2).replace(" ", "")
    soup = BeautifulSoup(requests.get("https://www.hotslogs.com/PlayerSearch?NoRedirect=1&Name="+player_name).text)
    players_table = soup.find('tbody')
    if not players_table:
        bot.say("Unable to find any rating for player " + player_name)
        return
    players = players_table.find_all('tr')
    for player in players:
        if count < 5:
            name_cell = player.find('td', text=re.compile(player_name, re.IGNORECASE))
            region = name_cell.previous_sibling
            league = name_cell.next_sibling
            mmr = league.next_sibling
            bot.say("{name} [{region}] - {league} [{mmr}]"
                    .format(name=name_cell.string, region=region.string, league=league.string, mmr=mmr.string))
        count += 1
    if count > 5:
        bot.msg(trigger.nick, 'Here\'s the full list of ' + player_name +
                              'https://www.hotslogs.com/PlayerSearch?NoRedirect=1&Name='+player_name)


@commands('mumble')
@example('!mumble')
def mumble_info(bot, trigger):
    """

    :param bot:
    :param trigger:
    """
    bot.say("[Reddit Mumble]  Host:hotsreddit.no-ip.org  Port:7000  URL:mumble://hotsreddit.no-ip.org:7000/")

@commands('ts3', 'ts')
@example('!ts3')
def ts3_info(bot, trigger):
    """

    :param bot:
    :param trigger:
    """
    bot.say("[Reddit Teamspeak] ts3.oda-h.com")


@commands('addBattleTag', 'addBT')
@example('!addBattleTag Wobbley#2372 EU')
def assign_bnet(bot, trigger):
    """
    Saves the entered BattleTag for the invoking user. A PM is sent to the user with an error message or confirmation
    If the user already has a BattleTag linked to his name, he will be asked to remove it.
    :param trigger: Expected to contain a BattleTag in trigger.group(2)
    """
    user = trigger.nick

    if not trigger.group(2):
        bot.msg(user, 'Here is how you can use the !addbt command: ' + bot_commands['addBattleTag']['example'])
        return

    pattern = re.compile('^[a-zA-Z0-9]+[#]\d{4,5}\s[a-zA-Z]{2}$')
    if not pattern.match(trigger.group(2)):
        bot.msg(user, '[BattleTag]: Wrong format, an example of the correct format: "!addBT Wobbley#2372 EU"')
        return
    nick = trigger.group(3)
    region = trigger.group(4).upper()
    region_nick = '[{0}]{1}'.format(region, nick)
    message = create_BattleTag(user, region_nick)
    bot.msg(user, message)


@commands('getBattleTag', 'getBT')
@example('!getBattleTag Wobbley')
def get_bnet(bot, trigger):
    """
    Print the BattleTag entered for the given user, if no BattleTag exists it will return an error message.
    :param trigger: Expected to contain a IRC username in trigger.group(2)
    """
    nick = trigger.group(2)
    if not nick:
        bot.reply('A irc username is required, example: "getBT Wobbley"')
        return
    data = select_BattleTag(nick.replace(" ", ""))
    if not data:
        bot.reply("No BattleTag found for {0} ".format(nick))
    else:
        if data[0].endswith('s'):
            bot.reply("{0}' BattleTag is {1} ".format(data[0], data[1]))
        else:
            bot.reply("{0}'s BattleTag is {1} ".format(data[0], data[1]))


@commands('removeBattleTag', 'removeBT')
@example('!removeBattleTag')
def remove_bnet(bot, trigger):
    """
    Removes the entered BattleTag for the username that invoked the command. A PM with confirmation is sent to the user.
    """
    nick = trigger.nick
    delete_BattleTag(nick)
    bot.msg(nick, "[BattleTag]: Removed")


@commands('rotation')
@example('!rotation')
def free_rotation(bot, trigger):
    """
    Prints the name of the current free heroes as a comma separated list.
    Datasource: http://heroesofthestorm.github.io/free-hero-rotation
    """
    rotation_list = free_rotation_list()
    if rotation_list:
        bot.say("Free rotation: " + ', '.join(rotation_list))
    else:
        bot.say("Free rotation list: http://heroesofthestorm.github.io/free-hero-rotation")


@commands('help')
@example(bot_commands['help']['example'])
def get_command_help(bot, trigger):
    """
    Prints help for the given command name
    """
    command = trigger.group(2)

    if not command:
        bot.msg(trigger.nick, "Hey " + trigger.nick + "! Check out my !commands to see what I can do")
        return

    if command in bot_commands:
        bot.msg(trigger.nick, get_command_help_message(command))
        return
    else:
        for command_name, command_options in bot_commands.items():
            if 'alias' in command_options and command_options['alias'].lower() == command:
                bot.msg(trigger.nick, get_command_help_message(command_name))
                return

    bot.msg(trigger.nick, 'I don\'t know this command')


@commands('bug')
@example(bot_commands['bug']['example'])
def report_bug(bot, trigger):
    """
    Print bug tracker URL
    """
    url = "https://github.com/Wobbley/HotS-Willie-Module/issues/new"
    bot.say("You can submit a bug here: " + url)

def free_rotation_list():
    """
    Scrapes the name of the current free heroes from www.heroesfire.com, and returns it as a list object.
    :return: A list object with hero names
    """
    soup = BeautifulSoup(requests.get("http://heroesofthestorm.github.io/free-hero-rotation").text)
    free_hero_elements = soup.select("button.btn")
    rotation_list = []
    hero_name_regex = '<button.+>(.+)</button>'
    rotation_limit = 7
    for hero_element in free_hero_elements:
        if re.match(hero_name_regex, str(hero_element)):
            hero_name = re.search(hero_name_regex, str(hero_element)).group(1)
            hero_name = hero_name.replace("-", " ").title()
            rotation_list.append(hero_name)
            if len(rotation_list) >= rotation_limit:
                break
    return rotation_list


# noinspection PyPep8Naming
def create_BattleTag(irc_username, battleTag):
    """
    Creates a new row in the battletag database.
    :param irc_username: The irc username.
    :param battleTag: The BattleTag value
    :return: A string with either a success message, or an error message.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('SELECT * FROM BattleTag WHERE irc=?', (irc_username,))
    data = c.fetchone()
    if not data:
        c.execute('INSERT INTO BattleTag VALUES (?,?)', (irc_username, battleTag,))
        dbz.commit()
        dbz.close()
        return "[BattleTag]: Added"
    else:
        c.execute('UPDATE BattleTag SET bnet=? WHERE irc=?', (battleTag, irc_username,))
        dbz.commit()
        dbz.close()
        return "[BattleTag]: Replaced {0} with {1}".format(data[1], battleTag)


# noinspection PyPep8Naming
def select_BattleTag(irc_username):
    """
    Retrieves the battleTag linked the the given IRC username.
    :param irc_username: The user for which you want a BattleTag retrieved.
    :return: The first row in the database matching the given username.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('SELECT * FROM BattleTag WHERE irc=? COLLATE NOCASE', (irc_username,))
    data = c.fetchone()
    dbz.close()
    return data


# noinspection PyPep8Naming
def delete_BattleTag(irc_username):
    """
    Deletes rows from the table with the given irc name.
    :param irc_username: Which username the battletag shall be removed for.
    """
    dbz = lite.connect(filename)
    c = dbz.cursor()
    c.execute('DELETE FROM BattleTag WHERE irc=?', (irc_username,))
    dbz.commit()
    dbz.close()

set_up_db()
