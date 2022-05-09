# -*- coding: utf-8 -*-
"""
Created on Fri May  6 23:30:34 2022

@author: Brian
"""
# https://lichess.org/api/team/{teamId}/arena


#%%
import gspread
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import lichess.api as lich
import time
#%%
def top_k(score_vector,k):
    
    return int(np.sum(sorted(score_vector)[::-1][:k]))

def drop_k(score_vector,k):
    
    return int(np.sum(sorted(score_vector)[::-1][:-k]))

#%% CONFIGS

configs_df = pd.read_csv('C:/Users/Brian/Documents/VT_Grand_Prix_2022/GP_script_configs.txt', index_col = 'parameter')
teamName = configs_df['value'].loc['teamName']
API_path = configs_df['value'].loc['API_filepath']

#%%
# define the scope #could make function here for "setup gDrive connection"
scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']

# add credentials to the account
creds = ServiceAccountCredentials.from_json_keyfile_name(API_path, scope)

# authorize the clientsheet 
client = gspread.authorize(creds)

#TODO ensure code is pointed to the PROD GP Standings, not TEST
VT_Gsheet = client.open('TEST VT Grand Prix Standings 2022')
GP_instance = VT_Gsheet.get_worksheet(0)
CT_instance = VT_Gsheet.get_worksheet(1)
MVP_instance = VT_Gsheet.get_worksheet(2)

point_distribution = {1:105,2:77,3:65,4:53,5:45,6:37,7:29,8:21,9:5,10:5,11:5,12:5,13:5,14:5,15:5,16:5,17:5,18:5,19:5,20:5}

tournaments = pd.read_json('https://lichess.org/api/team/{}/arena'.format(teamName) , lines = True)
tournaments = tournaments[tournaments.fullName.str.contains('2022')].sort_values('startsAt')
#%%

tournament_status = tournaments.loc[0].status
refresh_rate_seconds = 30

if tournament_status == 20: #10 = created, 20 = started, 30 = finished
    
    tournament_length_minutes = tournaments.loc[0].minutes
    iterations = int(tournament_length_minutes * 60 / refresh_rate_seconds)

else:
    iterations = 0 #for one time runs, such as updating MVP for the week.

for _ in range(iterations + 1):    
    mvp_df = pd.read_csv('C:/Users/Brian/Documents/VT_Grand_Prix_2022/MVPs_2022.txt',header = None, index_col = False)
    #crossTable_df = pd.DataFrame() #CT_instance! Then hopefully eliminate for loop on tournament ID! Only use the top tournament in the tournaments df
    crossTable_df = pd.DataFrame(CT_instance.get_all_records())
    
    if len(crossTable_df.columns) > 0:
        crossTable_df = crossTable_df.set_index('')
    
#for tourney_id in tournaments.id.values:
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
        gp_score = point_distribution[rank]*(num_games > 0)

        name_list.append(username)
        rank_list.append(rank)
        gp_list.append(gp_score)
    
    tourney_df = pd.DataFrame(gp_list , index = name_list, columns = [tourney_date])
    
    if tourney_df.columns[0] not in crossTable_df.columns:
        crossTable_df = pd.concat([crossTable_df,tourney_df],axis = 1,sort = False)
    else:
        crossTable_df[tourney_df.columns[0]] = tourney_df.T.iloc[0]
    
    crossTable_df = crossTable_df.fillna(0)
    
    if tournaments.shape[0] < 3:
        GP_table = crossTable_df.apply(lambda x: top_k(x,tournaments.shape[0]),axis = 1).sort_values(ascending = False)
    else:
        GP_table = crossTable_df.apply(lambda x: drop_k(x,2),axis = 1).sort_values(ascending = False)
    GP_table.name = 'Drop 2'
    mvp_df.columns = ['MVP']
    
    #GP_table
    MVP_scores = mvp_df['MVP'].value_counts()*5    
    
    crossTable_df = crossTable_df.sort_index(key=lambda x: x.str.lower()) #update pandas to 1.1.0
    
    for user in MVP_scores.index:
        if user in GP_table.index:
            GP_table[user] += MVP_scores[user]
    
    GP_table = GP_table.sort_values(ascending = False)
    
    GP_table = GP_table.to_frame()
    GP_table['Num_MVPs'] = mvp_df.MVP.value_counts()
    GP_table = GP_table.fillna(0)

    GP_columns = ['','Grand Prix Score', 'Number of MVPs']
    
    websites = ['https://lichess.org/tournament/' + tid for tid in tournaments.id]
    tournaments['website'] = websites
    
    GP_instance.clear()
    GP_instance.insert_rows([GP_columns] + GP_table.reset_index().values.tolist())
    
    CT_columns = crossTable_df.reset_index().columns.values.tolist()
    CT_columns[0] = ''
    
    
    CT_instance.clear()
    CT_instance.insert_rows([CT_columns] + crossTable_df.reset_index().values.tolist())
    
    MVP_columns = ['Tournament Name', 'Website', 'MVP']
    
    MVP_instance.clear()
    MVP_instance.insert_rows([MVP_columns] + tournaments[['fullName', 'website']].values.tolist())
    
    MVP_instance.update('C2:C', mvp_df.values.tolist())
    
    if tournament_status == 20:
        time.sleep(refresh_rate_seconds)
#%% SCRATCH CODE
#Drop2 = crossTable_df.apply(lambda x: drop_k(x,2),axis = 1)
#Drop2.name = 'Drop 2'
#
#GP_table = pd.concat([GP_table,Drop2],axis = 1)

# GP_table.to_csv('C:/Users/bjenks2011/Desktop/VT_GP_2021/VT_GP_2021_Totals.csv',header = True)
# crossTable_df.to_csv('C:/Users/bjenks2011/Desktop/VT_GP_2021/VT_GP_2021_crosstable.csv',header = True)
