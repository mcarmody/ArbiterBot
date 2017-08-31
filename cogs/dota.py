"""A cog for Dota 2 commands."""

from discord.ext import commands

from .dotacog import heropoll


class Dota(object):
  """Commands for Dota 2 stuff."""

  def __init__(self, bot):
    self._heropoll_command = heropoll.HeroPollCommand(bot)

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
    await self._heropoll_command.heropoll(ctx)


def setup(bot):
  bot.add_cog(Dota(bot))
  # TODO(timzwiebel): Ensure that commands are protected by a role so that not
  # just anyone can execute them.
