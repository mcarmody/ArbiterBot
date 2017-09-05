"""The implementation of the heropoll command.

Based on the "poll" command from the "general" cog.
"""

import discord

from ..utils.dataIO import dataIO

# The default open poll question.
# Args: author
_DEFAULT_OPEN_POLL_QUESTION_TEMPLATE = (
    '@here **Which hero should {} play this game? Suggestions welcome!**')

# The default closed poll question.
# Args: author
_DEFAULT_CLOSED_POLL_QUESTION_TEMPLATE = (
    '@here **Which of the following heroes should {} play this game?**')

# The template for each option in the poll.
# Args: index, option
_OPTION_TEMPLATE = '{}.  {}'

# Open poll instructions.
_OPEN_POLL_INSTRUCTIONS = (
    'Type the number or hero name to vote!\n'
    'Or type the name of another hero to suggest it!\n')

# Closed poll instructions.
_CLOSED_POLL_INSTRUCTIONS = 'Type the number or hero name to vote!'

# The template for whispering users that their vote is acknowledged.
# Args: index, option
_VOTE_ACKNOWLEDGED_TEMPLATE = 'Vote acknowledged: **{}. {}**'

# The template for each winner option in the poll results.
# Args: index, option, vote count
_RESULTS_WINNER_OPTION_TEMPLATE = '**{}.  {} ({} votes)**'

# The template for each loser option in the poll results.
# Args: index, option, vote count
_RESULTS_LOSER_OPTION_TEMPLATE = '{}.  {} ({} votes)'

# The message for poll results when there are no options.
# Args: author
_RESULTS_NO_OPTIONS_MESSAGE_TEMPLATE = (
    'There were **no heroes to vote on** in the poll for {}! Next time try '
    'suggesting heroes by typing their names.')

# The template for poll results with a single winner.
# Args: author, option, vote count
_RESULTS_SINGLE_WINNER_TEMPLATE = (
    'The winner of the poll for {} is **{}** with **{} votes**!')

# The template for poll results with a single winner.
# Args: author, option, vote count
_RESULTS_MULTIPLE_WINNERS_TEMPLATE = (
    'The winners of the poll for {} are **{}** with **{} votes**!')

# The string for joining each option in a multiple-winners poll result.
_RESULTS_MULTIPLE_WINNERS_JOIN = '**, **'

# The template for invalid argument messages.
# Args: command arg, command prefix
_INVALID_ARGUMENTS_TEMPLATE = 'Invalid arguments; see `{}help heropoll`'

# The template for invalid hero name messages.
# Args: invalid hero name
_INVALID_HERO_NAME_TEMPLATE = 'Invalid hero name: {}'

# Message for when a poll already exists.
_POLL_EXISTS_MESSAGE = 'There is already an ongoing hero poll in this channel'

# Start command.
_START_COMMAND = 'start'

# Stop command (to stop the poll and print results).
_STOP_COMMAND = 'stop'

# Abort command (to stop the poll without printing results).
_ABORT_COMMAND = 'abort'

# Delimiter for the list of heroes.
_DELIMITER = ','

# The file containing valid hero names.
# The file should contain a JSON Object:
#   keys: hero name (case-sensitive string)
#   values: nicknames (array of case-insensitive strings)
# Note that the nicknames should contain the hero name itself.
_HEROES_LIST_FILE = 'data/dota/heroes.json'


class HeroPollCommand(object):
  """The implementation of the heropoll command."""

  def __init__(self, bot):
    # Ideally, we would use ctx.bot everywhere, but on_message doesn't seem to
    # have a context, so we'll plumb the bot through here.
    self._bot = bot
    self._channel_poll_map = {}

    # Load the valid heroes.
    # Invert the map and make each name lowercase. For example:
    # JSON: {'Hero': ['Name', 'Other Name']}
    # map: {'name': 'Hero', 'other name': 'Hero'}
    json_map = dataIO.load_json(_HEROES_LIST_FILE)
    self._valid_heroes = {}
    for hero, names in json_map.items():
      for name in names:
        lower_name = name.lower()
        if lower_name in self._valid_heroes:
          raise ValueError(
              '"{}" nickname for "{}" is already used for "{}"'.format(
                  name, hero, self._valid_heroes[lower_name]))
        self._valid_heroes[lower_name] = hero

  async def heropoll(self, ctx):
    """See cogs/dota.py for for the documentation for this method."""
    command_args = [arg.strip() for arg in ctx.message.content.split(None, 2)]
    if len(command_args) <= 1:
      await ctx.bot.say(_INVALID_ARGUMENTS_TEMPLATE.format(ctx.prefix))
      return
    sub_command = command_args[1]
    if sub_command == _START_COMMAND:
      await self._start_poll(ctx)
    elif sub_command == _STOP_COMMAND:
      await self._stop_poll(ctx, say_results=True)
    elif sub_command == _ABORT_COMMAND:
      await self._stop_poll(ctx, say_results=False)
    else:
      await ctx.bot.say(_INVALID_ARGUMENTS_TEMPLATE.format(ctx.prefix))

  async def _start_poll(self, ctx):
    # Check for existing polls.
    poll = self._channel_poll_map.get(ctx.message.channel.id)
    if poll:
      await ctx.bot.say(_POLL_EXISTS_MESSAGE)
      return

    # Parse the start command.
    command_args = ctx.message.content.split(None, 2)
    if len(command_args) <= 2:
      # No options were given, so it's an open poll.
      is_open = True
      options = []
    else:
      # Parse the options.
      is_open = False
      options = [opt.strip() for opt in command_args[2].split(_DELIMITER)]
      # Validate the hero names.
      for i, name in enumerate(options):
        try:
          valid_name = self._parse_string_as_hero_name(name)
        except ValueError:
          # Invalid hero name.
          await ctx.bot.say(_INVALID_HERO_NAME_TEMPLATE.format(name))
          return
        options[i] = valid_name

    # Create the new poll.
    # If len(options) == 0, the poll is implicitly open. Otherwise, it is
    # closed.
    poll = _Poll(ctx.message.author, options, len(options) == 0)
    self._channel_poll_map[ctx.message.channel.id] = poll
    if len(self._channel_poll_map) == 1:
      # Only register the listener when adding the first poll.
      ctx.bot.add_listener(self.on_message)
    await poll.say_poll(ctx)

  async def _stop_poll(self, ctx, say_results):
    """Stops an ongoing poll.

    Args:
      ctx: The Context.
      say_results: A bool, whether to say the results to the channel.
    """
    poll = self._channel_poll_map.get(ctx.message.channel.id)
    if not poll:
      await ctx.bot.say('There is no ongoing hero poll in this channel')
      return
    del self._channel_poll_map[ctx.message.channel.id]
    if len(self._channel_poll_map) == 0:
      # Only remove the listener when removing the last poll.
      ctx.bot.remove_listener(self.on_message)
    if say_results:
      await poll.say_results(ctx)

  async def on_message(self, message):
    """Called when any user posts a message in any channel."""
    # Check for an ongoing poll in this channel.
    poll = self._channel_poll_map.get(message.channel.id)
    if not poll:
      return

    stripped_content = message.content.strip()

    # Try to parse the message as a number.
    try:
      index = int(stripped_content)
    except ValueError:
      pass
    else:
      await poll.cast_vote(self._bot, message, index)
      return

    # Try to parse the message as a hero name.
    try:
      hero_name = self._parse_string_as_hero_name(stripped_content)
    except ValueError:
      pass
    else:
      await poll.cast_vote(self._bot, message, hero_name)

  def _parse_string_as_hero_name(self, string):
    """Returns the message as the name of a hero.

    Args:
      message: The Message.

    Returns:
      A string, the name of a valid hero (which may or may not be in the
      options).

    Throws:
      ValueError: The message was not the name of a valid hero.
    """
    hero_name = self._valid_heroes.get(string.lower(), None)
    if not hero_name:
      raise ValueError('{} is not a valid hero name'.format(string))
    return hero_name


class _VoteTotal(object):
  """A mutable tuple of (option, total)."""

  def __init__(self, option):
    self.option = option
    self.total = 0


class _Poll(object):
  """A class to manage a hero poll."""

  def __init__(self, author, options, is_open):
    self._author = author
    self._options = options
    self._is_open = is_open
    # TODO(timzwiebel): Allow customizing the question (ideally non-globally)?
    if self._is_open:
      self._question = _DEFAULT_OPEN_POLL_QUESTION_TEMPLATE.format(author.name)
      self._instructions = _OPEN_POLL_INSTRUCTIONS
    else:
      self._question = _DEFAULT_CLOSED_POLL_QUESTION_TEMPLATE.format(
          author.name)
      self._instructions = _CLOSED_POLL_INSTRUCTIONS
    self._user_vote_map = {}
    self._message = None  # Also used as an indicator that the poll is ongoing.

  def get_author_id(self):
    return self._author.id

  async def say_poll(self, ctx):
    if self._message:
      raise ValueError('Poll message has already been said')
    msg = self._build_message()
    self._message = await ctx.bot.say(msg)

  async def say_results(self, ctx):
    # Tally up the totals and build a message with all of the options.
    totals = [_VoteTotal(opt) for opt in self._options]
    winner_value = 0
    for index in self._user_vote_map.values():
      totals[index].total += 1
      winner_value = max(winner_value, totals[index].total)
    winners = []
    msg = ''
    for i, vt in enumerate(totals):
      if vt.total == winner_value:
        template = _RESULTS_WINNER_OPTION_TEMPLATE
        winners.append(vt.option)
      else:
        template = _RESULTS_LOSER_OPTION_TEMPLATE
      msg += template.format(i + 1, vt.option, vt.total) + '\n'

    # Prepend the message with the winners.
    if len(winners) == 0:
      # Only happens if there were no options.
      msg = (
          _RESULTS_NO_OPTIONS_MESSAGE_TEMPLATE.format(self._author.name)
          + '\n\n' + msg)
    elif len(winners) == 1:
      msg = (
          _RESULTS_SINGLE_WINNER_TEMPLATE.format(
              self._author.name, winners[0], winner_value)
          + '\n\n' + msg)
    else:
      msg = (
          _RESULTS_MULTIPLE_WINNERS_TEMPLATE.format(
              self._author.name,
              _RESULTS_MULTIPLE_WINNERS_JOIN.join(winners),
              winner_value)
          + '\n\n' + msg)
    await ctx.bot.say(msg)
    self._message = None  # No more voting.

  def _build_message(self):
    msg = self._question
    msg += '\n' if len(self._options) == 0 else '\n\n'
    for i, opt in enumerate(self._options):
      msg += _OPTION_TEMPLATE.format(i + 1, opt) + '\n'
    msg += '\n' + self._instructions
    return msg

  async def cast_vote(self, bot, message, vote):
    """Casts a vote (if the vote is valid).

    Note that this method can be called from outside a context, so convenience
    methods like bot.say will not work.

    Args:
      bot: The Bot.
      author_id: A string, the ID of the author of the message.
      vote: A number or a string, the index or the hero name.
    """
    # Check that the poll has been said.
    if not self._message:
      return

    # Check that the user hasn't voted.
    if message.author.id in self._user_vote_map:
      return

    # Determine the index of the option.
    is_poll_author = (message.author.id == self._author.id)
    if type(vote) is int:
      if vote <= 0 or vote > len(self._options):
        # Invalid index.
        return
      index = vote - 1
    else:
      # Search for the index of the option.
      try:
        index = self._options.index(vote)
      except ValueError:
        # The hero name isn't in the options.
        if self._is_open:
          # Add the hero to the options.
          self._options.append(vote)
          index = len(self._options) - 1
          self._message = await bot.edit_message(
              self._message, self._build_message())
          # If it's the poll author, delete the message now since it won't count
          # as a vote.
          if is_poll_author:
            await self._try_delete_message(bot, message)
        else:
          # Invalid option.
          return

    # Cast the vote. The author doesn't get a vote.
    if is_poll_author:
      return
    self._user_vote_map[message.author.id] = index

    # Delete the message and whisper the user so that they know that their vote
    # was counted.
    await self._try_delete_message(bot, message)
    if not is_poll_author:
      await bot.send_message(
          message.author,
          _VOTE_ACKNOWLEDGED_TEMPLATE.format(index + 1, self._options[index]))

  async def _try_delete_message(self, bot, message):
    # If the bot has "Manage Messages" permissions, it will delete vote messages
    # after counting them to avoid clutter.
    try:
      await bot.delete_message(message)
    except discord.errors.Forbidden:
      pass
