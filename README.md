# Lichess_Grand_Prix
Code for running a Grand Prix Series in Lichess within a team! 
The script takes your weekly tournament data from lichess, adds points for each week's performance (points can be distributed as you see fit), and pushes it to google drive for everyone to see!

## Background
The script was customized to fit the rules of our Annual Grand Prix Series. 
Keeping this information in mind when reading will help you to customize this script for your own lichess league.

The basic structure of our league is as follows:

* Each Grand Prix season has 16 arena tournaments, played weekly.
* The point distribution is as follows for the top 8 players:
  + 1st Place: 100
  + 2nd Place: 72
  + 3rd Place: 60
  + 4th Place: 48
  + 5th Place: 40
  + 6th Place: 32
  + 7th Place: 24
  + 8th Place: 16
  + Also, 5 additional points are given to anyone who shows up and plays at least one game.

* At the end of each tournament, the players vote for an "MVP" as they see fit. This player gains an additional 5 points to their score.
* Everyone's lowest two scores are dropped in their grand total points calculation.

## Workflow

### First Time
Before running the script for the first time, ensure the following:
* Your google drive account is set up for accepting python script inputs. 
  + A great tutorial for this can be found at https://www.analyticsvidhya.com/blog/2020/07/read-and-update-google-spreadsheets-with-python/
* You already have a team established on lichess.org.
* Edit the configs file to establish where the MVP and API files are located. The following configs can be adjusted:
  + Inside the Script
    + `configs_df`: The file path of your config file
    + `point_distribution`: The distribution of points per tournament for your Grand Prix. The amount of points given to the last entry will be given to everyone who finishes below that rank. 
      - Make the last value in your dictionary 0 to give everyone who finishes at that rank or below 0 points. 
  + Inside the Config File
    + `team_website`: your team's website ( https://lichess.org/team/{teamId} )
    + `work_sheet`: Your Google Worksheet Title
    + `API_filepath`: filepath to your API json file
    + `MVP_filepath`: filepath to your MVP list, optional
      - Structure is a single column list with no header. 
    + `use_tourney_filter`: True if you are filtering your tournaments to those whose title contains a substring given by `tourney_filter`
    + `tourney_filter`: pattern to filter the tournament titles used in the Grand Prix
    + `refresh_rate_seconds`: number of seconds to delay until refreshing current tournament standings
      - used only when `live_updates` == True
    + `use_MVP`: Optional. If True, the players would vote on an MVP for a tournament and will be awarded `MVP_points` points on top of his score for the tournament.
    + `MVP_points`: Number of points awarded to MVP
    + `num_scores_dropped`: Determines the number of bottom scores to drop from the standings. Set to 0 to count every score.
    + `min_num_games`: Playing less than this amount of games nullifies your score for a given tournament. Set to 0 to not use a minimum number of games per  tournament.
    + `live_updates`: If True, run this script as a tournament is being played to update scores in Google Drive every `refresh_rate_seconds`
    + `eval_multiple_tournaments`: If True, this will evaluate the scores of multiple tournaments and place the results in Google Drive. This will not work with live updates, as the process would be slow and inefficient.
    + `google_API_delay`: Number of seconds to delay writing to the Google Drive/Sheets API. 
      - Max write calls to API is 60/minute/user, but unlimited per day. (as of May 15, 2022)
    + `reset_crosstable`: Used to clear the Crosstable Sheet from Google Sheet. Useful for testing purposes and for evaluating different subsets of tournaments.

  ### Periodically
  Now, on a weekly basis (or a periodic basis established by your team):

  * Make a tournament for your team on lichess.org
  * Start the tournament
  * Run the script
    + The script fetches the relevant information from the most recent tournament being played via the lichess API
    + See the results in near-real time on the specified google drive location, with a delay as specified in the `refresh_rate_seconds` variable.
      - Updated Grand Prix Standings
      - A Crosstable which how many points each player got on a given tournament's date
      - A Sheet which shows the Name of the tournaments played, a link to their website on lichess, and who won the "MVP" vote for that tournament.
    + Do not use a delay less than 10 seconds, as you may get rate-limited by lichess.org 
    + The script will know whether the tournament has yet to start, is ongoing, or is completed.
       - If the tournament is ongoing, the script will run every `refresh_rate_seconds` seconds until the tournament is over.

Note that this script is built to run weekly as each tournament is running, however you can customize it to run through multiple weeks of tournaments if necessary. This can be a slow process if running through several tournaments at once. 


## What exactly is this script doing?

* Import the proper libraries and define two functions for scoring the final totals for each player.
* Read the configs from the destination specified in the script.
* Uses the configs to setup the google drive scope, API, and which google spreadsheet is being targeted.
  + Opens the google spreadsheet and all its sheets
* Establishes the point distribution
* Finds all the tournaments created by a team and then filters to the relevant ones
  + In my personal use case, we're only interested in the tournaments whose name contains "2022".
* Discovers the tournament status at the time of the script being run
  + status codes are as follows: 10 = created, 20 = started, 30 = finished
  + Calculates the number of necessary iterations to run the for loop based on tournament status, total length of tournament, and refresh rate.
* Reads the current Grand Prix crosstable from Google Drive, to make use of work previously done
* Gather info for latest tournament
  + Get the player ranks, username, number of games played, and calculate their GP score. 
  + If a player doesn't play at least the minimum number of games, their score = 0.
* Update Crosstable
* Use Crosstable to calculate new GP scores
* Factor in MVP vote, if cast. This vote will be placed in a text file, read as a csv.
* Update Standings with MVP vote
* Push results to Google Drive
* Repeats as necessary
