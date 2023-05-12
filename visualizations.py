# -*- coding: utf-8 -*-
import pandas as pd
import folium


def plot_on_a_map(data:pd.DataFrame, mmsi_col_name:str='MMSI', time_col_name:str='t',
                  attr_col_line:str='hasProblem', long_col_name:str='lon', lat_col_name:str='lat') -> None:
    """
    Based on a dataframe containing both coordinate data and spoofing status, outputs a map
    :param data: dataframe containing both coordinate data and spoofing status
    :param mmsi_col_name: dataframe column name for mmsi
    :param time_col_name: dataframe column name for time (column must be datetime)
    :param attr_col_line: dataframe column name for detail of interest (column must be boolean)
    :param long_col_name: dataframe column name for longitude
    :param lat_col_name: dataframe column name for latitude
    """
    data = data.copy()
    data = data.sort_values([mmsi_col_name, time_col_name], ascending=False)
    data = data[[mmsi_col_name, time_col_name, attr_col_line, long_col_name, lat_col_name]]

    c = 0
    for mmsi, vals in data.groupby(mmsi_col_name):
        coordinates = [list(i) for i in list(zip(vals[lat_col_name].tolist(), vals[long_col_name].tolist()))]
        if not len(coordinates) > 1:
            continue
        if c == 0:
            m = folium.Map(location=coordinates[0], zoom_start=10, tiles='Stamen Toner')
            c += 1
        haspr = vals[attr_col_line].values[0]
        my_PolyLine = folium.PolyLine(coordinates, color='#FF2D00' if haspr else '#003AFF', line_weight=500)
        m.add_child(my_PolyLine)
    m.show_in_browser()
