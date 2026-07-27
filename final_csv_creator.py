import pandas as pd

roll_list = (
    pd.read_csv('New PDT Students List.csv')['EO ID']
    .dropna()
    .astype(str)
    .str.strip()
)


df_graded = pd.read_csv('assignment 7/scipy/results.csv')


df_graded['id'] = df_graded['id'].astype(str).str.strip()
df_graded['_id_lc'] = df_graded['id'].str.lower()


graded_rolls = df_graded['_id_lc'].dropna()


ungraded_roll_list = roll_list[~roll_list.str.lower().isin(graded_rolls)]


df_master = pd.DataFrame({'id': roll_list.astype(str).str.strip()})
df_master['_id_lc'] = df_master['id'].str.lower()


final_df = df_master.merge(df_graded.drop(columns=['id']), how='left', left_on='_id_lc', right_on='_id_lc')




# Fill numeric score-like columns with 0 and feedback-like columns with a default message
for col in final_df.columns:    
    lname = col.lower()
    if 'score' in lname or lname == 'total' or lname == 'marks':
        final_df[col] = final_df[col].fillna(0)
    if 'feedback' in lname or 'remark' in lname or 'remarks' in lname or lname == 'comment':
        final_df[col] = final_df[col].fillna('No submission found')

final_df = final_df.sort_values('_id_lc')
final_df = final_df.drop(columns=['_id_lc'])

final_df.to_csv('final.csv', index=False)

