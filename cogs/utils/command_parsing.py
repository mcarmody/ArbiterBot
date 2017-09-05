"""Utilities for parsing commands."""


def get_stripped_command(ctx):
  """Returns ctx.message.content, but with the ctx.prefix stripped."""
  if not ctx.message.content.startswith(ctx.prefix):
    raise RuntimeError(
        'Received command message that didn\'t start with command prefix')
  return ctx.message.content[len(ctx.prefix):]
