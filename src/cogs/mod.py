import os
import sys
import time
import asyncio
import aiohttp
import discord
import logging
import humanize
import datetime
import traceback
import coloredlogs
import DiscordUtils
import motor.motor_asyncio
from pytz import timezone
from datetime import date
from datetime import datetime
from discord.ext import commands

# Initializing the logger
log = logging.getLogger("Moderation cog")
coloredlogs.install(logger=log)

# Database Handler class
class dbHandler:
    def __init__(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("CONNECTIONURI"))
        self.db = self.client.erin
        self.col = self.db["warns"]

    async def find_user(self, uid: int, gid: int):
        user = await self.col.find_one({"uid": uid})
        if not user:
            user = await self.register_user(uid, gid)
        try:
            user[f"{gid}"]
        except KeyError:
            user[f"{gid}"] = []
        finally:
            return user

    async def register_user(self, uid: int, gid: int):
        data = {"uid": uid, f"{str(gid)}": []}
        await self.col.insert_one(data)
        return data

    async def update_user_warn(self, uid: int, data):
        await self.col.replace_one({"uid": uid}, data)


class mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dbHandler = dbHandler()

    @commands.command(name="warn", aliases=["strike"])
    @commands.has_permissions(manage_messages=True)
    @commands.guild_only()
    async def warn(self, ctx, user: discord.Member, *, reason: str):
        # sanitizing input
        if user.bot:
            return await ctx.message.reply("Don't even **try** to warn my kind :)")

        if len(reason) > 150:
            return await ctx.send(
                "Reason parameter exceeded 150 characters. Please write a shorter reason to continue"
            )

        if (
            user.top_role.position > ctx.message.author.top_role.position
            or user.top_role.position == ctx.message.author.top_role.position
        ):
            return await ctx.message.reply(
                f"Cannot warn {user.mention} as their highest role is the same as or above your highest role."
            )

        # editing the user object to hold the user data
        entryData = {
            "type": "strike",
            "reason": reason,
            "time": ctx.message.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"),
            "mod": f"{ctx.message.author.id}",
        }
        userData = await self.dbHandler.find_user(user.id, ctx.message.guild.id)
        userData[f"{ctx.message.author.guild.id}"].append(entryData)

        # uodating user entries
        await self.dbHandler.update_user_warn(user.id, userData)

        # building the embed
        channel = discord.Embed(
            description=f"Punishment(s) for {user.display_name}#{user.discriminator} submitted successfully.",
            color=11661816,
            timestamp=ctx.message.created_at,
        )
        channel.set_footer(
            text=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url
        )
        channel.set_author(
            name=self.bot.user.display_name, icon_url=self.bot.user.avatar_url
        )

        dmEmbed = discord.Embed(
            title="Erin Moderation",
            description=f"Your punishments have been updated in {ctx.message.guild.name}.",
            color=11661816,
            timestamp=ctx.message.created_at,
        )

        dmEmbed.add_field(name="Action", value="Strike/Warn", inline=True)

        dmEmbed.add_field(name="Reason", value=f"{reason}", inline=True)

        dmEmbed.set_footer(
            text=ctx.message.author.display_name, icon_url=ctx.message.author.avatar_url
        )
        dmEmbed.set_author(
            name=self.bot.user.display_name, icon_url=self.bot.user.avatar_url
        )
        await ctx.message.reply(embed=channel)
        try:
            await user.send(embed=dmEmbed)
        except:
            pass

    @commands.command(name="search", aliases=["warns"])
    @commands.guild_only()
    async def search(self, ctx, searchUser: discord.Member):
        user = await self.dbHandler.find_user(searchUser.id, ctx.message.guild.id)
        threshold = 5
        reason_chunk = [
            user[f"{ctx.message.guild.id}"][i : i + threshold]
            for i in range(0, len(user[f"{ctx.message.guild.id}"]), threshold)
        ]

        i = 0
        embeds = []
        for chunk in reason_chunk:
            embed = discord.Embed(
                title=f"All punishments for {searchUser.display_name}#{searchUser.discriminator}",
                color=11661816,
                timestamp=ctx.message.created_at,
            )
            embed.set_footer(
                text=ctx.message.author.display_name,
                icon_url=ctx.message.author.avatar_url,
            )
            embed.set_author(
                name=self.bot.user.display_name, icon_url=self.bot.user.avatar_url
            )

            for reason in chunk:
                i = i + 1

                embed.add_field(
                    inline=False,
                    name=f"{i}) {reason['type']}",
                    value=f"Reason: **{reason['reason']}**\nTime: **{reason['time']}**\nResponsible moderator: **<@{reason['mod']}>**",
                )

            embeds.append(embed)
            embed = None

        if len(embeds) == 1:
            return await ctx.message.reply(embed=embeds[0])

        elif len(embeds) == 0:
            emb = discord.Embed(
                description=f"{searchUser.mention} has a clean state",
                color=11661816,
                timestamp=ctx.message.created_at,
            )
            emb.set_footer(
                text=ctx.message.author.display_name,
                icon_url=ctx.message.author.avatar_url,
            )
            emb.set_author(
                name=self.bot.user.display_name, icon_url=self.bot.user.avatar_url
            )
            return await ctx.send(embed=emb)

        else:
            paginator = DiscordUtils.Pagination.CustomEmbedPaginator(
                ctx, remove_reactions=True
            )
            paginator.add_reaction(
                "\N{Black Left-Pointing Double Triangle with Vertical Bar}", "first"
            )
            paginator.add_reaction("\N{Black Left-Pointing Double Triangle}", "back")
            paginator.add_reaction("\N{CROSS MARK}", "lock")
            paginator.add_reaction("\N{Black Right-Pointing Double Triangle}", "next")
            paginator.add_reaction(
                "\N{Black Right-Pointing Double Triangle with Vertical Bar}", "last"
            )
            return await paginator.run(embeds)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def delpunishments(self, ctx, user: discord.Member):
        delUser = await self.dbHandler.find_user(user.id, ctx.message.guild.id)
        request = await ctx.send(
            f"**This will delete ALL punishments that the user has.** Do you want to continue?"
        )
        await request.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await request.add_reaction("\N{CROSS MARK}")

        def check(reaction, user):
            state = (
                user == ctx.message.author
                and str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}"
                or str(reaction.emoji) == "\N{CROSS MARK}"
                and reaction.message.id == request.id
                and user.bot == False
            )
            return state

        try:
            reaction, author = await self.bot.wait_for(
                "reaction_add", timeout=30.0, check=check
            )
        except asyncio.TimeoutError:
            return await ctx.message.channel.send(
                "Woops you didnt react within 30 seconds...."
            )

        if str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}":
            try:
                await request.clear_reaction("\N{WHITE HEAVY CHECK MARK}")
                await request.clear_reaction("\N{CROSS MARK}")
            except:
                pass
            delUser.pop(f"{ctx.message.guild.id}")
            await self.dbHandler.update_user_warn(user.id, delUser)
            try:
                return await request.edit(
                    content=f"All records of {user.mention} have been deleted"
                )
            except:
                return await ctx.send(
                    f"All records of {user.mention} have been deleted"
                )
        elif str(reaction.emoji) == "\N{CROSS MARK}":
            try:
                await request.clear_reaction("\N{WHITE HEAVY CHECK MARK}")
                await request.clear_reaction("\N{CROSS MARK}")
            except:
                pass

            try:
                return await request.edit(
                    content=f"\N{CROSS MARK} reaction recieved ...cancelling process"
                )
            except:
                return await ctx.send(
                    f"\N{CROSS MARK} reaction recieved ...cancelling process"
                )


def setup(bot):
    bot.add_cog(mod(bot))
