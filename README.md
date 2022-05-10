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
* Edit the configs file to establish where the MVP and API files are located. The following configs should be adjusted:
  + team_name: The name of your team on lichess. Spaces get replaced with dashes, and all characters are lowercase.
  + work_sheet: The name of your Google Sheet in Google Drive. Open an empty google spreadsheet in your drive if you do not currently have one.
  + API_filepath: File path of your downloaded API json key from google's developer console
  + MVP_filepath: File path of MVP text file

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
  + In our case, we're only interested in the tournaments whose name contains "2022".
* Discovers the tournament status at the time of the script being run
  + status codes are as follows: 10 = created, 20 = started, 30 = finished
  + Calculates the number of necessary iterations to run the for loop based on tournament status, total length of tournament, and refresh rate.
* Reads the current Grand Prix crosstable
* Gather info for latest tournament
  + Get the player ranks, username, number of games played, and calculate their GP score. 
  + If a player doesn't play at least one game, their score = 0.
* Update Crosstable
* Use Crosstable to calculate new GP scores
* Factor in MVP vote, if cast. This vote will be placed in a text file, read as a csv.
* Update Standings with MVP vote
* Push results to Google Drive
