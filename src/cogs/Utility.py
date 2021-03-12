import discord
import asyncio
import os

from discord.ext import commands,tasks
from discord.enums import ActivityType, Status
from typing import Union
from aiohttp import ClientResponseError
from discord.ext import commands, tasks
from discord.ext.commands.view import StringView

class Utility(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"{self.__class__.__name__} Cog has been loaded\n-----")

    @commands.command(aliases=["presence"])
    async def activity(self, ctx, activity_type: str.lower, *, message: str = ""):
        """
        Set an activity status for the bot.
        Possible activity types:
            - `playing`
            - `streaming`
            - `listening`
            - `watching`
            - `competing`
        When activity type is set to `listening`,
        it must be followed by a "to": "listening to..."
        When activity type is set to `competing`,
        it must be followed by a "in": "competing in..."
        When activity type is set to `streaming`, you can set
        the linked twitch page:
        - `{prefix}config set twitch_url https://www.twitch.tv/somechannel/`
        To remove the current activity status:
        - `{prefix}activity clear`
        """
        if activity_type == "clear":
            await self.set_presence()
            embed = discord.Embed(title="Activity Removed", color=ctx.message.author.color)
            return await ctx.send(embed=embed)

        if not message:
            raise commands.MissingRequiredArgument(SimpleNamespace(name="message"))

        try:
            activity_type = ActivityType[activity_type]
        except KeyError:
            raise commands.MissingRequiredArgument(SimpleNamespace(name="activity"))

        activity, _ = await self.set_presence(
            activity_type=activity_type, activity_message=message
        )
        msg = f"Activity set to: {activity.type.name.capitalize()} "
        if activity.type == ActivityType.listening:
            msg += f"to {activity.name}."
        elif activity.type == ActivityType.competing:
            msg += f"in {activity.name}."
        else:
            msg += f"{activity.name}."

        embed = discord.Embed(title="Activity Changed", description=msg, color=ctx.message.author.color)
        return await ctx.send(embed=embed)

    async def set_presence(self, *, status=None, activity_type=None, activity_message=None):
        if status is None:
            pass
        if activity_type is None:
            pass
        url = None
        if activity_type is not None and not activity_message:
            logger.warning(
                'No activity message found whilst activity is provided, defaults to "Modmail".'
            )
            activity_message = "Modmail"

        if activity_type == ActivityType.listening:
            if activity_message.lower().startswith("to "):
                activity_message = activity_message[3:].strip()
        elif activity_type == ActivityType.competing:
            if activity_message.lower().startswith("in "):
                activity_message = activity_message[3:].strip()
        elif activity_type == ActivityType.streaming:
            url = "https://www.twitch.tv/pokimane"
            pass

        if activity_type is not None:
            activity = discord.Activity(type=activity_type, name=activity_message, url=url)
        else:
            activity = None
        await self.bot.change_presence(activity=activity, status=status)
        return activity, status

def setup(bot):
    bot.add_cog(Utility(bot))