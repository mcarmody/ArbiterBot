"""A cog for Dota 2 commands."""

from discord.ext import commands

from .dotacog import heropoll
from .dotacog import randomplayers


class Dota(object):
  """Commands for Dota 2 stuff."""

  def __init__(self, bot):
    self._heropoll_command = heropoll.HeroPollCommand(bot)
    self._randomplayers_command = randomplayers.RandomPlayersCommand()

  @commands.command(pass_context=True, no_pm=True)
  async def heropoll(self, ctx):
    """Starts/stops a poll to choose a hero to play.

    Polls can be "open" or "closed":
     - Open polls allow anyone to suggest any hero. In addition, the poll author can make as many suggestions as they like by sending messages with hero names.
     - Closed polls only allow the hero options they were created with.

    Only one ongoing poll is allowed per text channel.

    Hero names are not case-sensitive. Nicknames (e.g., AM for Anti-Mage, PL for Phantom Lancer, etc.) may also be used. The bot will do its best to understand suggested hero names.

    If the bot has the "Manage Messages" permission, it will delete vote messages from users (after counting them).

    Usage:
      Start an open poll:
        heropoll start
        Viper
        Lina
      Start a closed poll:
        heropoll start <comma-separated list of hero names>
        (E.g., heropoll start Brewmaster, Lone Druid, Meepo)
      Stop the poll and print the results:
        heropoll stop
      Stop the poll without printing the results:
        heropoll abort
    """
    await self._heropoll_command.heropoll(ctx)

  @commands.command(pass_context=True, no_pm=True)
  async def randomplayers(self, ctx):
    """Randomly selects players in a channel.

    Sends a message to @here requesting that players react. After 30 seconds, the specified number of players are chosen at random from those that reacted.

    Note that the count next to the reaction will be off by one due to the bot's initial reaction. This has no effect on player selection.

    Usage:
      Select 3 random players who react within to the message within 30 seconds:
        randomplayers 3
    """
    await self._randomplayers_command.randomplayers(ctx)


def setup(bot):
  bot.add_cog(Dota(bot))
  # TODO(timzwiebel): Ensure that commands are protected by a role so that not
  # just anyone can execute them.
