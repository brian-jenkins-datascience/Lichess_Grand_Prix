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

#%% CONFIGS

configs_df = pd.read_csv('C:/Users/Brian/Documents/VT_Grand_Prix_2022/GP_script_configs.txt', index_col = 'parameter') #Point this to your config file!

team_website = configs_df['value'].loc['team_website'] 
work_sheet = configs_df['value'].loc['work_sheet']
API_path = configs_df['value'].loc['API_filepath']
MVP_path = configs_df['value'].loc['MVP_filepath']
point_distribution = eval(configs_df['value'].loc['point_distribution'])
tourney_filter = configs_df['value'].loc['tourney_filter']
refresh_rate_seconds = int(configs_df['value'].loc['refresh_rate_seconds'])
use_MVP = eval(configs_df['value'].loc['use_MVP'])
num_scores_dropped = int(configs_df['value'].loc['num_scores_dropped'])
MVP_points = int(configs_df['value'].loc['MVP_points'])
min_num_games = int(configs_df['value'].loc['min_num_games'])
#%% GOOGLE & LICHESS API SETUP
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name(API_path, scope)

# authorize the clientsheet 
client = gspread.authorize(creds)

VT_Gsheet = client.open(work_sheet)
GP_instance = VT_Gsheet.get_worksheet(0)
CT_instance = VT_Gsheet.get_worksheet(1)

team_name = team_website.split('/')[-1]
tournaments = pd.read_json('https://lichess.org/api/team/{}/arena'.format(team_name) , lines = True)
if tourney_filter != '':
    tournaments = tournaments[tournaments.fullName.str.contains(tourney_filter)] #filters tournaments to those taking place in 2022


#%% PROCESS LICHESS DATA

#TODO Make simultaneous evaluation of all tournaments or periodic updates an option in config file
#TODO make a function to run either simul or periodic updates

#Determines tournament status for latest tournament 
tournament_status = tournaments.loc[0].status

if tournament_status == 20: #10 = created, 20 = started, 30 = finished
    tournament_length_minutes = tournaments.loc[0].minutes
    iterations = int(tournament_length_minutes * 60 / refresh_rate_seconds)
else:
    iterations = 0 #for one time runs, such as updating MVP for the week.


for _ in range(iterations + 1):  
    crossTable_df = pd.DataFrame(CT_instance.get_all_records())
    
    if len(crossTable_df.columns) > 0:
        crossTable_df = crossTable_df.set_index('')
    
    tourney_id = tournaments.id.loc[0]
    tourney = lich.tournament_standings(tourney_id)
    tourney_date = lich.tournament(tourney_id)['startsAt'].split('T')[0]

    name_list = []
    rank_list = []
    gp_list = []
    
    
    for player in tourney:
        username = player['name']
        num_games = len(player['sheet']['scores'])
        rank = player['rank']
        gp_score = point_distribution[min(rank, len(point_distribution))]*(num_games > min_num_games) # the last value in the pt distribution determines how many points everyone below that rank receives
        # registering without playing at least min_num_games nullifies your score for that tournament. set min_num_games = -1 to not restrict points based on games played

        name_list.append(username)
        rank_list.append(rank)
        gp_list.append(gp_score)
    
    tourney_df = pd.DataFrame(gp_list , index = name_list, columns = [tourney_date])
    
    if tourney_df.columns[0] not in crossTable_df.columns:
        crossTable_df = pd.concat([crossTable_df,tourney_df],axis = 1,sort = False)
    else:
        crossTable_df[tourney_df.columns[0]] = tourney_df.T.iloc[0]
    
    crossTable_df = crossTable_df.fillna(0)
    
    if tournaments.shape[0] <= num_scores_dropped: 
        GP_table = crossTable_df.apply(lambda x: top_k(x,tournaments.shape[0]),axis = 1).sort_values(ascending = False)
    else:
        GP_table = crossTable_df.apply(lambda x: drop_k(x,num_scores_dropped),axis = 1).sort_values(ascending = False)
    GP_table.name = 'Grand Prix Score'

    crossTable_df = crossTable_df.sort_index(key=lambda x: x.str.lower()) #update pandas to 1.1.0
    
    if use_MVP:
        mvp_df = pd.read_csv(MVP_path,header = None, index_col = False)
        mvp_df.columns = ['MVP'] 
        MVP_scores = mvp_df['MVP'].value_counts() * MVP_points
        for user in MVP_scores.index: 
            if user in GP_table.index:
                GP_table[user] += MVP_scores[user] 
    
        GP_table['Num_MVPs'] = mvp_df.MVP.value_counts()
        GP_columns = ['','Grand Prix Score', 'Number of MVPs']
    else:
        GP_columns = ['','Grand Prix Score']
    GP_table = GP_table.sort_values(ascending = False)
    GP_table = GP_table.to_frame()
    GP_table = GP_table.fillna(0)

    websites = ['https://lichess.org/tournament/' + tid for tid in tournaments.id]
    tournaments['website'] = websites
    
    GP_instance.clear()
    GP_instance.insert_rows([GP_columns] + GP_table.reset_index().values.tolist())
    
    CT_columns = crossTable_df.reset_index().columns.values.tolist()
    CT_columns[0] = ''
    
    
    CT_instance.clear()
    CT_instance.insert_rows([CT_columns] + crossTable_df.reset_index().values.tolist())
    
    MVP_columns = ['Tournament Name', 'Website', 'MVP']
    
    if use_MVP:
        
        MVP_instance = VT_Gsheet.get_worksheet(2)
        MVP_instance.clear()
        MVP_instance.insert_rows([MVP_columns] + tournaments[['fullName', 'website']].values.tolist())
        MVP_instance.update('C2:C', mvp_df.values.tolist())
    
    if tournament_status == 20:
        time.sleep(refresh_rate_seconds)
