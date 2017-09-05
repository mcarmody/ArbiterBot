"""The implementation of the randomplayers command."""

import asyncio
import random

import discord

# TODO(timzwiebel): Allow the duration to be configured (globally and/or per
# server).
_QUESTION_DURATION_SECONDS = 30

# The default question.
# Args: number of players
_DEFAULT_QUESTION_TEMPLATE = (
    '@here **Who wants to play in a game?** We need **{}** players.')

# The instructions.
_INSTRUCTIONS_MESSAGE = (
    '**Click the thumbsup reaction** in the next {} seconds if you want to be '
    'considered!').format(_QUESTION_DURATION_SECONDS)

# The reaction emoji.
_REACTION_EMOJI = '\U0001F44D'  # Thumbs up emoji

# The template for when there were enough players.
# Args: players (user IDs)
_ENOUGH_PLAYERS_TEMPLATE = '**<@{}>, you have been selected to play!**'

# The template for when there were not enough players.
# Args: players (user IDs)
_NOT_ENOUGH_PLAYERS_TEMPLATE = (
    '**<@{}>, you have been selected to play!** Unfortunately, there were not '
    'enough players to select more.')

# The string for joining the selected players.
_PLAYERS_JOIN = '>, <@'

# The template for invalid argument messages.
# Args: command arg, command prefix
_INVALID_ARGUMENTS_TEMPLATE = 'Invalid arguments; see `{}help randomplayers`'

# The template for invalid number of players.
# Args: number of players
_INVALID_NUM_PLAYERS_TEMPLATE = 'Invalid number of players: {}'

# The message for when a selection already exists.
_SELECTION_EXISTS_MESSAGE = (
    'There is already an ongoing random player selection in this channel')

# The message for when too many users reacted to the message.
_TOO_MANY_USERS_MESSAGE = 'Too many users reacted to the message'

# The message for when no users reacted to the message.
_NO_USERS_MESSAGE = '**There were no players to select from!**'

# The maximum number of reaction users that can be handled.
# See Client.get_reaction_users.
_REACTION_LIMIT = 100


class RandomPlayersCommand(object):
  """The implementation of the randomplayers command."""

  def __init__(self):
    self._channel_set = set()

  async def randomplayers(self, ctx):
    # Check if a random player selection is already ongoing.
    if ctx.message.channel.id in self._channel_set:
      await ctx.bot.say(_SELECTION_EXISTS_MESSAGE)
      return

    command_args = [arg.strip() for arg in ctx.message.content.split(None, 1)]

    # Parse the number of players.
    if len(command_args) <= 1:
      await ctx.bot.say(_INVALID_ARGUMENTS_TEMPLATE.format(ctx.prefix))
      return
    try:
      num_players = int(command_args[1])
      if num_players < 1:
        raise ValueError('Invalid number of players: {}'.format(num_players))
    except ValueError:
      await ctx.bot.say(_INVALID_NUM_PLAYERS_TEMPLATE.format(command_args[1]))
      return

    # Run the player selection.
    self._channel_set.add(ctx.message.channel.id)
    try:
      start_message = await self._say_start_message(ctx, num_players)
      await asyncio.sleep(_QUESTION_DURATION_SECONDS)
      await self._say_results(ctx, num_players, start_message)
    finally:
      self._channel_set.remove(ctx.message.channel.id)

  async def _say_start_message(self, ctx, num_players):
    start_message = await ctx.bot.say(
        _DEFAULT_QUESTION_TEMPLATE.format(num_players)
        + '\n\n'
        + _INSTRUCTIONS_MESSAGE)
    await ctx.bot.add_reaction(start_message, _REACTION_EMOJI)
    return start_message

  async def _say_results(self, ctx, num_players, start_message):
    # Get the users who reacted.
    reaction_users = await self._get_reaction_users(ctx, start_message)

    # Check if we hit the limit.
    if len(reaction_users) == _REACTION_LIMIT:
      await ctx.bot.say(_TOO_MANY_USERS_MESSAGE)
      return

    # Filter out bots.
    reaction_users = [u for u in reaction_users if not u.bot]

    # Check if there were no users.
    if len(reaction_users) == 0:
      await ctx.bot.say(_NO_USERS_MESSAGE)
      return

    # Select the players.
    players = self._select_players(reaction_users, num_players)

    # Say the results.
    players_string = _PLAYERS_JOIN.join(players)
    if len(players) < num_players:
      await ctx.bot.say(_NOT_ENOUGH_PLAYERS_TEMPLATE.format(players_string))
    else:
      await ctx.bot.say(_ENOUGH_PLAYERS_TEMPLATE.format(players_string))

  async def _get_reaction_users(self, ctx, start_message):
    # Update the start message to get the reactions.
    start_message = await ctx.bot.get_message(
        start_message.channel, start_message.id)
    reactions = [r for r in start_message.reactions if r.me]
    if len(reactions) != 1:
      raise ValueError('Expected to find exactly 1 reaction from the bot')
    return await ctx.bot.get_reaction_users(reactions[0], _REACTION_LIMIT)

  def _select_players(self, users, num_players):
    """Randomly selects min(num_players, len(users)) players from users.

    Args:
      users: The list of Users.
      num_players: An int, the number of players to select.

    Returns:
      A list containing the user IDs of the selected users.
    """
    # Perform the first num_players steps of a Fisher-Yates shuffle to
    # efficiently select num_players from users without replacement.
    # Make a shallow copy of users so we don't modify the argument.
    users = list(users)
    for i in range(min(num_players, len(users) - 1)):
      selected = random.randint(i, len(users) - 1)
      users[i], users[selected] = users[selected], users[i]
    return [u.id for u in users[:num_players]]
