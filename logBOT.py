import discord
from discord.ext import commands
import datetime
from datetime import datetime as DT
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger('my_logger')
handler = RotatingFileHandler('Desktop/my_log.log', maxBytes=2000, backupCount=10)
logger.addHandler(handler)

token = 'token'

def main():

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!",intents=intents)

    @bot.tree.command(name="log_match", description="Log the date in the format of 'month/day/year' and the time in the format of 'hour:minute'")
    async def log_match(interaction: discord.Interaction, team_name: str, opponent_name: str, date: str, time:str):
            
        with open('Desktop/my_log.log', 'r') as f:
            lines = f.readlines()
        with open('Desktop/my_log.log', "w") as f:
            for line in lines:
                match = line.split(';')
                matchDate = DT.strptime(match[2], '%m/%d/%Y')
                if(matchDate.date() >= DT.now().date()):
                    f.write(line)

        if(("[a-zA-Z]+") in date or len(date) != 10):
            await interaction.response.send_message("MATCH DATE FORMATTED INCORRECTLY. PLEASE INCLUDE ONLY NUMBERS AND A SLASH. EX: 1/20/2025".format(team_name, opponent_name, date, time))
        else:
            logger.warning("{};{};{};{}".format(team_name, opponent_name, date, time))
            await interaction.response.send_message("Match logged. Your match is {} against {} on {} at {}.".format(team_name, opponent_name, date, time))

    @bot.tree.command(name="del_match", description="Deletes a logged esports match.")
    async def del_match(interaction: discord.Interaction, team_name: str, opponent_name: str, date: str, time:str):
        deletes = 0
        with open('Desktop/my_log.log', 'r') as f:
                lines = f.readlines()
        with open('Desktop/my_log.log', "w") as f:
            for line in lines:
                if line.strip("\n") != "{};{};{};{}".format(team_name, opponent_name, date, time):
                    f.write(line)
                else:
                    deletes += 1
        
        if(deletes == 1):
            await interaction.response.send_message("Match deleted. Your match was {} against {} on {} at {}.".format(team_name, opponent_name, date, time))
        elif(deletes == 0):
            await interaction.response.send_message("Match not found. Please try again.")

    @bot.tree.command(name="show_match", description="Shows a list of this week's matches.")
    async def show_match(ctx: commands.Context):
        currentDay = DT.today().strftime('%B %d, %Y')
        embed = discord.Embed(title="Matches for the week of {}.".format(currentDay), description="Here's the matches of this week.", color=discord.Color.from_rgb(235,97,6))

        with open('Desktop/my_log.log', 'r') as f:
            lines = f.readlines()
            for line in lines:
                match = line.split(';')
                matchDate = DT.strptime(match[2], '%m/%d/%Y')
                weekFromNow = DT.now().date() + datetime.timedelta(days=7)
                if(matchDate.date() > DT.now().date() and matchDate.date() < weekFromNow):
                    embed.add_field(name="", value="{} {} {} {}".format(match[0], match[1], match[2], match[3]), inline=False)

        await ctx.response.send_message(embed=embed)

    @bot.tree.command(name="clear_matches", description="Clears all matches.")
    async def clear_matches(interaction: discord.Interaction):
        if(interaction.user.guild_permissions.administrator == True):
            open('Desktop/my_log.log', 'w').close()
            await interaction.response.send_message("Matches Cleared.")
        else:
            await interaction.response.send_message("Lacking Permissions.")

    # bot.tree.copy_global_to(guild=discord.Object(id=))

    @bot.event
    async def on_ready():
        await bot.get_channel(channel).send("Ready and raring.")
        await bot.tree.sync()

    bot.run(token)

main()

def test():
    logger.warning("{};{};{};{}".format("Overwatch Orange", "UTK White", "1/19/2025", "6:00"))

    with open('Desktop/my_log.log', 'r') as f:
        lines = f.readlines()
        print(lines)

    # with open('Desktop/my_log.log', "w") as f:
    #     for line in lines:
    #         if line.strip("\n") != "{};{};{};{}".format("Overwatch Orange", "UTK White", "12/16/2005", "6:00"):
    #             f.write(line)

    with open('Desktop/my_log.log', 'r') as f:
        lines = f.readlines()

    with open('Desktop/my_log.log', 'r') as f:
        for line in lines:
            match = line.split(';')
            today = DT.today()
            matchDate = DT.strptime(match[2], '%m/%d/%Y')
            print(matchDate)
            if(matchDate.year == today.year and matchDate.month == today.month and matchDate.day <= today.day + 5 and matchDate.day > today.day):
                print("Match is within this week.")
            else:
                print("not in this week.")

    with open('Desktop/my_log.log', "w") as f:
        for line in lines:
            match = line.split(';')
            today = DT.today()
            matchDate = DT.strptime(match[2], '%m/%d/%Y')
            if(matchDate.year < today.year and matchDate.month < today.month and matchDate.day < today.day):
                f.write(line)
#test()