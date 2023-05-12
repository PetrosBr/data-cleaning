# -*- coding: utf-8 -*-
from cleaning import *
from spoofing_detection import *
from visualizations import *


if __name__ == "__main__":

    # cleaning
    line_data = rm_invalid_movements(rm_empty(read_df('a.csv')))
    # storing cleaned data
    line_data.to_csv('cleaned_data.csv', index=False)
    # retrieving cleaned data
    line_data = read_df('cleaned_data.csv')

    # spoofing detection
    mmsi_set = set(line_data['shipid'].unique())
    spoof_data = pd.DataFrame(columns=["MMSI", "hasProblem", "hasLocationSpoofing", "hasIdentitySpoofing", "CountOfClusters"])
    count = 0
    for mmsi in mmsi_set:
        df_temp = line_data.copy()
        df_temp = df_temp[df_temp['shipid'] == mmsi]
        df_temp.rename(columns={'lon': 'x', 'lat': 'y', 't': '# Timestamp'}, inplace=True)
        df_temp['# Timestamp'] = pd.to_datetime(df_temp['# Timestamp'])
        hasProblem, hasLocationSpoofing, hasIdentitySpoofing, numberOfClusters = get_cluster_insights(df_temp, 5, mmsi)
        new_row = {'MMSI': mmsi, 'hasProblem': hasProblem, 'hasLocationSpoofing': hasLocationSpoofing,
                   'hasIdentitySpoofing': hasIdentitySpoofing, 'CountOfClusters': numberOfClusters}
        spoof_data.loc[count] = new_row
        count += 1

    # storing spoof status data
    spoof_data.to_csv('spoof_status.csv', index=False)
    # retrieving spoof status data
    spoof_data = read_df('spoof_status.csv', df_dtypes={'MMSI': str, 'hasProblem': bool, 'hasLocationSpoofing': bool,
                                                        'hasIdentitySpoofing': bool, 'CountOfClusters': int})

    # area of interest selection
    line_data.rename(columns={'shipid': 'MMSI'}, inplace=True)
    constrained_region_df = spoof_data.merge(line_data, on=['MMSI'], how='inner')

    world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
    greece = world[world['name'] == 'Greece']['geometry'].values[0]

    constrained_region_df = areas_of_interest(constrained_region_df, greece, lat_col_name='lat', long_col_name='lon')

    # visualization
    constrained_region_df['t'] = pd.to_datetime(constrained_region_df['t'])

    plot_on_a_map(constrained_region_df)
