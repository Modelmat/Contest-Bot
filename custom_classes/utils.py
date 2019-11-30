from discord.ext import commands


async def safe_can_run(command: commands.Command, ctx):
    try:
        return await command.can_run(ctx)
    except commands.CommandError:
        return False
