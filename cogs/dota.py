"""A cog for Dota 2 commands."""

from discord.ext import commands

from .dotacog import heropoll


class Dota(object):
  """Commands for Dota 2 stuff."""

  def __init__(self, bot):
    self._heropoll_command = heropoll.HeroPollCommand(bot)

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


def setup(bot):
  bot.add_cog(Dota(bot))
  # TODO(timzwiebel): Ensure that commands are protected by a role so that not
  # just anyone can execute them.
