from typing import Set
from io import BytesIO

import datetime
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands, tasks
from dotenv import dotenv_values
import polars

ENV_VARIABLES = dotenv_values("bot.env")
TOKEN = ENV_VARIABLES["TOKEN"]
CHANNEL = ENV_VARIABLES["CHANNEL"]
DB_NAME = ENV_VARIABLES["DB_NAME"]


class MatchLoggingBot(commands.Bot):

    def __init__(self, *args, db_path: Path, log_channel_id: int, **kwargs):

        super().__init__(*args, **kwargs)
        self.db_path = db_path
        self.log_channel_id = log_channel_id

    @property
    def clear_dates(self) -> Set[datetime.date]:

        now = datetime.datetime.now()
        return {datetime.date(day=31, month=12, year=now.year), datetime.date(day=31, month=6, year=now.year)}

    async def on_ready(self):

        self.log_channel = self.get_channel(self.log_channel_id)
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            opponent_name TEXT NOT NULL,
            league_name TEXT NOT NULL,
            match_datetime TEXT NOT NULL, -- ISO 8601 format
            match_creator INTEGER NOT NULL
            )"""
        )
        self.connection.commit()

        await self.tree.sync()

    @tasks.loop(hours=12)
    async def clear_database(self):
        now = datetime.datetime.now()
        if now.date() not in self.clear_dates:
            return
        roughly_six_months_ago = now - datetime.timedelta(days=180)
        self.cursor.execute(
            """
            DELETE *
            FROM matches
            where match_datetime <= ?
            """,
            (roughly_six_months_ago.isoformat(),)
        )
        self.connection.commit()
        backup = sqlite3.connect("matches_backup.db")
        with backup:
            self.connection.backup(backup)
        backup.close()


def main():

    intents = discord.Intents.default()
    intents.message_content = True
    bot = MatchLoggingBot(
        command_prefix="!",
        intents=intents,
        db_path=Path(DB_NAME),
        log_channel_id=CHANNEL
    )

    @bot.tree.command(
        name="log_match",
        description="Date in format of 'month/day/year' and the time in format of 'hour:minute' (24 hour time)"
    )
    async def log_match(
            interaction: discord.Interaction,
            team: discord.Role,
            opponent_name: str,
            date: str,
            time: str,
            league_name: str
    ):

        if "," in opponent_name or "," in league_name:
            await interaction.response.send_message(
                "Please remove all commas from the opponent and league names", ephemeral=True
            )

        try:
            date_time = datetime.datetime.strptime(f"{date} {time}", "%m/%d/%Y %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "Bad date or time format. Use the proper formatting, EX: 1/20/2025 and 17:00", ephemeral=True
            )
            return

        if "White" not in team.name and "Purple" not in team.name and "Orange" not in team.name:
            await interaction.response.send_message("Invalid role. Please select a team role only", ephemeral=True)
            return

        iso_8601_date_time = date_time.isoformat()
        bot.cursor.execute("""
            INSERT INTO matches (team_name, opponent_name, league_name, match_datetime, match_creator)
            VALUES (?, ?, ?, ?, ?)
        """, (team.name, opponent_name, league_name, iso_8601_date_time, interaction.user.id))
        bot.connection.commit()

        await interaction.response.send_message(
            f"Match logged. Your match is {team.name} against {opponent_name} on {date} at {time}.", ephemeral=True
        )

    @bot.tree.command(name="del_match", description="Deletes a logged esports match you created")
    async def del_match(interaction: discord.Interaction, match_id: int):

        bot.cursor.execute("SELECT * from MATCHES where id = ?", (match_id,))
        result = bot.cursor.fetchone()
        if result[-1] != interaction.user.id and not interaction.user.guild_permissions.administrator:
            interaction.response.send_message("You cannot delete a match you did not create", ephemeral=True)
            return

        bot.cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        bot.connection.commit()
        await interaction.response.send_message(f"Match with id {match_id} deleted", ephemeral=True)

    @bot.tree.command(name="show_match", description="Shows a list of this week's matches")
    async def show_match(interaction: discord.Interaction):
        current_day = datetime.datetime.today()
        embed = discord.Embed(
            title=f"Matches for the week of {current_day.strftime('%B %d, %Y')}",
            description="Here's the matches of this week!",
            color=discord.Color.from_rgb(235, 97, 6)
        )

        one_week_from_now = current_day + datetime.timedelta(weeks=1)

        bot.cursor.execute(
            """
            SELECT id, team_name, opponent_name, match_datetime
            FROM matches
            where match_datetime <= ? and match_datetime >= ?
            """,
            (one_week_from_now.isoformat(), current_day.isoformat())
        )
        for id_, team_name, opponent_name, match_datetime in bot.cursor.fetchall():
            date_and_time = datetime.datetime.fromisoformat(match_datetime).strftime('%m/%d/%Y at %H:%M')
            embed.add_field(name="", value=f"({id_}) {team_name} vs. {opponent_name} on {date_and_time}", inline=False)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="clear_matches", description="Clears all matches")
    @commands.has_permissions(administrator=True)
    async def clear_matches(interaction: discord.Interaction):
        bot.cursor.execute("DELETE FROM matches")
        bot.connection.commit()
        await interaction.response.send_message("Matches cleared", ephemeral=True)
        await bot.log_channel.send(
            f"Match DB cleared by <@{interaction.user.id}> on {datetime.datetime.now().isoformat()}"
        )

    @bot.tree.command(name="to_csv", description="Converts to CSV")
    async def to_csv(interaction: discord.Interaction):

        with BytesIO() as buffer:
            polars.read_database(
                query="SELECT * FROM matches",
                connection=bot.connection
            ).write_csv(buffer)
            buffer.seek(0)
            file = discord.File(fp=buffer, filename="matches.csv")
        await interaction.response.send_message(file=file, ephemeral=True)

    @bot.tree.command(name="force_sync")
    @commands.has_permissions(administrator=True)
    async def force_sync(interaction: discord.Interaction):
        await bot.tree.sync()
        await interaction.response.send_message("Sync forced", ephemeral=True)

    bot.run(TOKEN)


if __name__ == "__main__":

    main()
