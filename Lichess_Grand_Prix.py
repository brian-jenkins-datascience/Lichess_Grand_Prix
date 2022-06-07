# -*- coding: utf-8 -*-
"""
Created on Fri May  6 23:30:34 2022

@author: Brian
"""
# Team arena tournaments: https://lichess.org/api/team/{teamId}/arena


#%% LIBRARIES
import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import lichess.api as lich
import time
#%% FUNCTIONS
def top_k(score_vector,k):
    
    return int(np.sum(sorted(score_vector)[::-1][:k]))

def drop_k(score_vector,k):
    if k > 0:
        return int(np.sum(sorted(score_vector)[::-1][:-k]))
    else:
        return int(np.sum(score_vector))
    
def update_crosstable(crossTable_df,tourney_id,point_distribution, min_num_games, num_scores_dropped):
    if len(crossTable_df.columns) > 0:
        crossTable_df = crossTable_df.set_index('')

    tourney = lich.tournament_standings(tourney_id)
    tourney_date = lich.tournament(tourney_id)['startsAt'].split('T')[0]
    
    if tourney_date in crossTable_df.columns:
        crossTable_df = crossTable_df.drop(columns=tourney_date)
    
    name_list = []
    rank_list = []
    gp_list = []
    
    
    for player in tourney:
        username = player['name']
        num_games = len(player['sheet']['scores'])
        rank = player['rank']
        gp_score = point_distribution[min(rank, len(point_distribution))]*(num_games >= min_num_games)
        
        # The last value in the pt distribution determines how many points everyone below that rank receives
        # Registering without playing at least min_num_games nullifies your score for that tournament. 
        # Set min_num_games = 0 to not restrict points based on games played
        
        name_list.append(username)
        rank_list.append(rank)
        gp_list.append(gp_score)
    
    tourney_df = pd.DataFrame(gp_list , index = name_list, columns = [tourney_date])
    
    if tourney_df.columns[0] not in crossTable_df.columns:
        crossTable_df = pd.concat([crossTable_df,tourney_df],axis = 1,sort = False)
    else:
        crossTable_df[tourney_df.columns[0]] = tourney_df.T.iloc[0]
    
    crossTable_df = crossTable_df.fillna(0)
    crossTable_df = crossTable_df.sort_index(key=lambda x: x.str.lower()) 
    
    return crossTable_df

#%% CONFIGS (See README for details about configs)

configs_filepath = 'C:/Users/Brian/Documents/VT_Grand_Prix_2022/GP_script_configs.txt'
configs_df = pd.read_csv(configs_filepath, index_col = 'parameter') #Point this to your config file!
point_distribution = {1:105,2:77,3:65,4:53,5:45,6:37,7:29,8:21,9:5}

team_website = configs_df['value'].loc['team_website'] 
work_sheet = configs_df['value'].loc['work_sheet']
API_path = configs_df['value'].loc['API_filepath']
MVP_path = configs_df['value'].loc['MVP_filepath']
use_tourney_filter = eval(configs_df['value'].loc['use_tourney_filter'])
tourney_filter = configs_df['value'].loc['tourney_filter']
refresh_rate_seconds = int(configs_df['value'].loc['refresh_rate_seconds'])
use_MVP = eval(configs_df['value'].loc['use_MVP'])
num_scores_dropped = int(configs_df['value'].loc['num_scores_dropped'])
MVP_points = int(configs_df['value'].loc['MVP_points'])
min_num_games = int(configs_df['value'].loc['min_num_games'])
live_updates = eval(configs_df['value'].loc['live_updates'])
eval_multiple_tournaments = eval(configs_df['value'].loc['eval_multiple_tournaments'])
google_API_delay = int(configs_df['value'].loc['google_API_delay'])
reset_crosstable = eval(configs_df['value'].loc['reset_crosstable'])

#%% GOOGLE & LICHESS API SETUP
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name(API_path, scope)

# authorize the clientsheet 
client = gspread.authorize(creds)

#Before first time run: Ensure your Google Sheets file has 2 sheets, 3 if using MVP feature.
VT_Gsheet = client.open(work_sheet)
GP_instance = VT_Gsheet.get_worksheet(0)
CT_instance = VT_Gsheet.get_worksheet(1)

if reset_crosstable:
    CT_instance.clear()

team_name = team_website.split('/')[-1]
tournaments = pd.read_json('https://lichess.org/api/team/{}/arena'.format(team_name) , lines = True)
tournaments = tournaments[tournaments.status > 10]
if use_tourney_filter:
    tournaments = tournaments[tournaments.fullName.str.contains(tourney_filter)].reset_index() #filters tournaments according to those containing the value of tourney_filter.

if live_updates:
    assert eval_multiple_tournaments == False, "live_updates and eval_multiple_tournaments cannot both be True! The process would be too slow."

#%% PROCESS LICHESS DATA

#Determines tournament status for latest tournament 
tournament_status = tournaments.loc[0].status

if tournament_status == 20 and live_updates: #10 = created, 20 = started, 30 = finished
    tournament_length_minutes = tournaments.loc[0].minutes
    iterations = int(tournament_length_minutes * 60 / refresh_rate_seconds)
else:
    iterations = 0 #for one time runs, such as updating MVP for the week.

if eval_multiple_tournaments:
    num_tourneys = tournaments.shape[0]
else:
    num_tourneys = 1

for tourn_index in reversed(range(num_tourneys)):
    
    tourn_name = tournaments.loc[tourn_index]['fullName']
    tourn_variant = tournaments.loc[tourn_index]['perf']['name']
    tourn_clock = int(tournaments.loc[tourn_index]['clock']['limit'] / 60)
    tourn_inc = tournaments.loc[tourn_index]['clock']['increment']
    print("Processing {}: {} {} + {}".format(tourn_name, tourn_variant, tourn_clock, tourn_inc))
    
    for _ in range(iterations + 1):  
        #reads in previous crosstable information and updates with current tournament stats
        crossTable_df = pd.DataFrame(CT_instance.get_all_records())
        num_CT_cols = crossTable_df.shape[1]
        
        tourney_id = tournaments.id.loc[tourn_index]        
        crossTable_df = update_crosstable(crossTable_df,tourney_id,point_distribution, min_num_games, num_scores_dropped)
        #tie breaker data
        tb_df = pd.DataFrame(np.sort(crossTable_df.values,axis = 1)[:,::-1],index = crossTable_df.index)
        tb_df = tb_df.sort_values(by = list(np.arange(crossTable_df.shape[1])), ascending = False)
        tb_dict = {}
        for enum, idx in enumerate(tb_df.index):
            tb_dict[idx] = enum + 1
        tb_series = pd.Series(tb_dict,name='Tie Breaker Rank')
        
        if tournaments.shape[0] <= num_scores_dropped: 
            GP_table = crossTable_df.apply(lambda x: top_k(x,tournaments.shape[0]),axis = 1).sort_values(ascending = False)
        else:
            GP_table = crossTable_df.apply(lambda x: drop_k(x,num_scores_dropped),axis = 1).sort_values(ascending = False)
        GP_table.name = 'Grand Prix Score'
        
        #if using MVP feature, counts number of MVPs each user has won and adjusts points accordingly
        if use_MVP:
            mvp_df = pd.read_csv(MVP_path,header = None, index_col = False)
            mvp_df.columns = ['MVP'] 
            MVP_scores = mvp_df['MVP'].value_counts() * MVP_points
        
        GP_table = GP_table.sort_values(ascending = False)
        GP_table = GP_table.to_frame()
        
        if use_MVP:
            for user in MVP_scores.index: 
                if user in GP_table.index:
                    GP_table.loc[user] += MVP_scores[user] 
        
            GP_table['Num_MVPs'] = mvp_df.MVP.value_counts()
            GP_columns = ['Rank','Username','Grand Prix Score', 'Number of MVPs', 'Tie Breaker Rank']
        else:
            GP_columns = ['Rank','Username','Grand Prix Score', 'Tie Breaker Rank']
        
        #TODO concat tie breaker series into GP table
        GP_table = pd.concat([GP_table,pd.Series(tb_dict,name='Tie Breaker Rank')], axis = 1)
        GP_table = GP_table.sort_values(by = ['Grand Prix Score', 'Tie Breaker Rank'], ascending = [False, True])
        
        #preps output of Grand Prix Standings 
        GP_table = GP_table.fillna(0).sort_values('Grand Prix Score', ascending = False)
        GP_table_out = GP_table.reset_index().reset_index()
        GP_table_out = GP_table_out.rename(columns={'index':'Username', 'level_0':'Rank'})
        GP_table_out['Rank'] += 1
          
        websites = ['https://lichess.org/tournament/' + tid for tid in tournaments.id]
        tournaments['website'] = websites
        
        GP_instance.clear()
        GP_instance.insert_rows([GP_columns] + GP_table_out.values.tolist())
        
        CT_columns = crossTable_df.reset_index().columns.values.tolist()
        CT_columns[0] = ''
        CT_instance.clear()
        CT_instance.insert_rows([CT_columns] + crossTable_df.reset_index().values.tolist())
        
        if use_MVP:
            MVP_columns = ['Tournament Name', 'Website', 'MVP']
            MVP_instance = VT_Gsheet.get_worksheet(2)
            MVP_instance.clear()
            MVP_instance.insert_rows([MVP_columns] + tournaments.sort_values('startsAt')[['fullName', 'website']].values.tolist())
            MVP_instance.update('C2:C', mvp_df.values.tolist())
        
        if tournament_status == 20:
            time.sleep(refresh_rate_seconds)

        time.sleep(google_API_delay)
