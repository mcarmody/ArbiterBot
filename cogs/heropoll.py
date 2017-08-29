"""A cog for polling which heroes to play.

Based on the "poll" command from the "general" cog.

If the bot has permission to "Manage Messages", it will delete votes from users
after they are counted (to avoid clutter).
"""

import collections

import discord
from discord.ext import commands

# TODO(timzwiebel): Allow customizing the global default poll question?
_DEFAULT_POLL_QUESTION = '**Which hero should I play?**'


class HeroPoll(object):
  """Commands for polling which heroes to play."""

  def __init__(self, bot):
    # Ideally, we would use ctx.bot everywhere, but on_message doesn't seem to
    # have a context, so we'll plumb the bot through here.
    self._bot = bot
    self._channel_poll_map = {}

  @commands.command(pass_context=True, no_pm=True)
  async def heropoll(self, ctx):
    """Starts/stops a poll.

    Usage:
      Start a poll:
        heropoll <comma-separated list of options>
      Stop a poll and print the results:
        heropoll stop
      Stop a poll without printing the results:
        heropoll abort

    Examples:
      heropoll Brewmaster, Lone Druid, Meepo
      heropoll abort
      heropoll Viper, Hero that gets dumpstered by Viper in lane
      heropoll stop
    """
    # TODO(timzwiebel): Add additional controls for heroes in the poll?
    # For example,
    #   - we could maintain a list of all heroes and allow polls for "all", or
    #     "all except X,Y,Z"
    #   - we could allow configuring custom sets of heroes
    command = ctx.message.content.split()
    if len(command) <= 1:
      await ctx.bot.say(
          'Invalid arguments; see **{}help heropoll**'.format(ctx.prefix))
      return
    if command[1].lower() == 'stop':
      # TODO(timzwiebel): stop? end? finish? What's the best subcommand?
      await self._stop_poll(ctx, say_results=True)
      return
    if command[1].lower() == 'abort':
      await self._stop_poll(ctx, say_results=False)
      return
    poll = self._channel_poll_map.get(ctx.message.channel.id)
    if poll:
      await ctx.bot.say(
          'There is already an ongoing hero poll in this channel')
      return
    await self._start_poll(ctx)

  async def _start_poll(self, ctx):
    poll = _Poll(ctx.message, ',')
    self._channel_poll_map[ctx.message.channel.id] = poll
    if len(self._channel_poll_map) == 1:
      # Only register the listener when adding the first poll.
      ctx.bot.add_listener(self.on_message)
    await poll.say_poll(ctx)

  async def _stop_poll(self, ctx, say_results):
    poll = self._channel_poll_map.get(ctx.message.channel.id)
    if not poll:
      await ctx.bot.say('There is no ongoing hero poll in this channel')
      return
    if ctx.message.author.id != poll.get_author_id():
      await ctx.bot.say('Only the author can stop the poll')
      return
    del self._channel_poll_map[ctx.message.channel.id]
    if len(self._channel_poll_map) == 0:
      # Only remove the listener when removing the last poll.
      ctx.bot.remove_listener(self.on_message)
    if say_results:
      await poll.say_results(ctx)

  async def on_message(self, message):
    """Called when any user posts a message in any channel."""
    poll = self._channel_poll_map.get(message.channel.id)
    if poll:
      await poll.cast_vote(self._bot, message)


class _VoteTotal(object):
  """A mutable tuple of (option, total)."""

  def __init__(self, option):
    self.option = option
    self.total = 0


class _Poll(object):
  """A class to manage a hero poll."""

  def __init__(self, message, delimiter):
    # TODO(timzwiebel): Do we need to check for mentions in the message? Users
    # with permission to create hero polls might be able to circumvent mention
    # permissions by creating a poll with, for example "@everyone", which would
    # cause the bot to mention @everyone.
    self._author_id = message.author.id
    # TODO(timzwiebel): Allow customizing the question (non-globally)?
    self._question = _DEFAULT_POLL_QUESTION
    options = message.content.split(None, 1)[1].split(delimiter)
    self._options = [opt.strip() for opt in options]
    self._user_vote_map = {}

  def get_author_id(self):
    return self._author_id

  async def say_poll(self, ctx):
    message = self._question + '\n\n'
    for i, opt in enumerate(self._options):
      message += '{}.  {}\n'.format(i + 1, opt)
    message += '\nType the number to vote!'
    await ctx.bot.say(message)

  async def say_results(self, ctx):
    message = self._question + '\n\n'
    totals = [_VoteTotal(opt) for opt in self._options]
    winner_value = 0
    for vote in self._user_vote_map.values():
      totals[vote - 1].total += 1
      winner_value = max(winner_value, totals[vote - 1].total)
    winners = []
    for i, vt in enumerate(totals):
      if vt.total == winner_value:
        template = '**{}.  {} ({} votes)**\n'
        winners.append(vt.option)
      else:
        template = '{}.  {} ({} votes)\n'
      message += template.format(i + 1, vt.option, vt.total)
    if len(winners) == 1:
      message += '\nThe winner is **{}** with **{} votes**!'.format(
          winners[0], winner_value)
    else:
      message += '\nThe winners are **{}** with **{} votes**!'.format(
          '**, **'.join(winners), winner_value)
    await ctx.bot.say(message)

  async def cast_vote(self, bot, message):
    """Parses a message and casts a vote (if the message is valid).

    Note that this method can be called from outside a context, so convenience
    methods like bot.say will not work.
    """
    # TODO(timzwiebel): Use reactions or something better than typing a message
    # into the channel?
    if self._user_vote_map.get(message.author.id):
      # The user already voted, so ignore the message.
      return
    try:
      # Parse the message.
      vote = int(message.content)
    except ValueError:
      # The message is not a number.
      return
    if vote <= 0 or vote > len(self._options):
      # This isn't a valid vote, so ignore it.
      return
    self._user_vote_map[message.author.id] = vote
    try:
      await bot.delete_message(message)
    except discord.errors.Forbidden:
      # TODO(timzwiebel): Require permissions for the bot? Or do a better job of
      # indicating that if you give the bot permissions, it will delete vote
      # messages after counting them to avoid clutter.
      pass
    # TODO(timzwiebel): Which is worse, not knowing if your vote is counted, or
    # getting a whisper every time it is? Real users probably don't vote that
    # often, so we'll start by whispering every time.
    await bot.send_message(
        message.author,
        'Vote acknowledged: **{}. {}**'.format(vote, self._options[vote - 1]))


def setup(bot):
  bot.add_cog(HeroPoll(bot))
  # TODO(timzwiebel): Ensure that these commands are protected by a role so that
  # not just anyone can create polls.
