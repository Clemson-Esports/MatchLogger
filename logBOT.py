from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import dotenv_values

ENV_VARIABLES = dotenv_values("bot.env")
TOKEN = ENV_VARIABLES["TOKEN"]
CHANNEL = ENV_VARIABLES["CHANNEL"]
DB_NAME = ENV_VARIABLES["DB_NAME"]


class MatchLoggingBot(commands.Bot):

    def __init__(self, *args, db_path: Path, log_channel_id: int, **kwargs):

        super().__init__(*args, **kwargs)
        self.db_path = db_path
        self.log_channel_id = log_channel_id

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
            match_datetime TEXT NOT NULL, -- ISO 8601 format
            match_creator INTEGER NOT NULL
            )"""
        )
        self.connection.commit()

        await self.tree.sync()


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
        description="Log the date in the format of 'month/day/year' and the time in the format of 'hour:minute'"
    )
    async def log_match(
            interaction: discord.Interaction,
            team: discord.Role,
            opponent_name: str,
            date: str,
            time: str
    ):

        try:
            date_time = datetime.strptime(f"{date} {time}", "%m/%d/%Y %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "Bad date or time format. Use the proper formatting, EX: 1/20/2025 and 17:00"
            )
            return

        if "White" not in team.name and "Purple" not in team.name and "Orange" not in team.name:
            await interaction.response.send_message("Invalid role. Please select a team role only")
            return

        iso_8601_date_time = date_time.isoformat()
        bot.cursor.execute("""
            INSERT INTO matches (team_name, opponent_name, match_datetime, match_creator)
            VALUES (?, ?, ?, ?)
        """, (team.name, opponent_name, iso_8601_date_time, interaction.user.id))
        bot.connection.commit()

        await interaction.response.send_message(f"Match logged. Your match is {team.name} against {opponent_name} on {date} at {time}.")

    @bot.tree.command(name="del_match", description="Deletes a logged esports match you created")
    async def del_match(interaction: discord.Interaction, match_id: int):

        bot.cursor.execute("SELECT * from MATCHES where id = ?", (match_id,))
        result = bot.cursor.fetchone()
        if result[4] != interaction.user.id and not interaction.user.guild_permissions.administrator:
            interaction.response.send_message("You cannot delete a match you did not create", ephemeral=True)
            return

        bot.cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))
        bot.connection.commit()
        interaction.response.send_message(f"Match with id {match_id} deleted")

    @bot.tree.command(name="show_match", description="Shows a list of this week's matches")
    async def show_match(interaction: discord.Interaction):
        current_day = datetime.today()
        embed = discord.Embed(
            title=f"Matches for the week of {current_day.strftime('%B %d, %Y')}",
            description="Here's the matches of this week!",
            color=discord.Color.from_rgb(235, 97, 6)
        )

        one_week_from_now = current_day + timedelta(weeks=1)

        bot.cursor.execute(
            """
            SELECT *
            FROM matches
            where match_datetime <= ? and match_datetime >= ?
            """,
            (one_week_from_now.isoformat(), current_day.isoformat())
        )
        for match in bot.cursor.fetchall():
            date_and_time = datetime.fromisoformat(match[3]).strftime('%m/%d/%Y on %H:%M')
            embed.add_field(name="", value=f"{match[1]} vs. {match[2]} at {date_and_time}", inline=False)

        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="clear_matches", description="Clears all matches")
    @commands.has_permissions(administrator=True)
    async def clear_matches(interaction: discord.Interaction):
        bot.cursor.execute("DELETE FROM matches")
        bot.connection.commit()
        await interaction.response.send_message("Matches cleared", ephemeral=True)
        await bot.log_channel.send(f"Match DB cleared by <@{interaction.user.id}> on {datetime.now().isoformat()}")

    bot.run(TOKEN)


if __name__ == "__main__":

    main()
