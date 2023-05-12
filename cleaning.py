# -*- coding: utf-8 -*-
import pandas as pd
import shapely
import geopandas


def read_df(df_path:str='a.csv', df_dtypes:dict or None=None) -> pd.DataFrame:
    """
    reads data from a csv and creates a dataframe object
    :param df_dtypes: column name data types
    :param df_path: path of csv file
    :return: AIS dataframe
    """
    if df_dtypes is None:
        df_dtypes = {'t': str,'shipid': str,'lon': float,'lat':float,'heading': float,'course': float,
                     'speed': float,'status': float,'shiptype': float,'draught': float,'destination': str}
    data = pd.read_csv(df_path, dtype=df_dtypes, encoding = 'utf8')
    return data


def rm_empty(data:pd.DataFrame, lof:list or None=None) -> pd.DataFrame:
    """
    removes entries where at least one field from the ones defined are missing
    :param data: input dataframe
    :param lof: column names for fields to check missing values
    :return: dataframe with removed missing values
    """
    if lof is None:
        lof = ['lat', 'lon', 't', 'speed', 'course']
    data = data.copy()
    return data.dropna(subset=lof, how='any')


def rm_invalid_movements(data:pd.DataFrame, sog_col_name:str='speed', cog_col_name:str='course',
                         lat_col_name:str='lat', long_col_name:str='lon') -> pd.DataFrame:
    """
    Validates a given dataframe against value criteria
    :param data: dataframe to be checked
    :param sog_col_name: dataframe column name for speed over ground
    :param cog_col_name: dataframe column name for course over ground
    :param lat_col_name: dataframe column name for latitude
    :param long_col_name: dataframe column name for longitude
    :return: validated dataframe
    """
    data = data.copy()
    data = data[(data[sog_col_name].between(0.0, 80.0, inclusive='both')) &
                (data[cog_col_name].between(0.0, 360.0, inclusive='left')) &
                (data[lat_col_name].between(-90.0, 90.0, inclusive='both')) &
                (data[long_col_name].between(-180.0, 180.0, inclusive='both'))]
    return data


def rm_invalid_vessel_id(data:pd.DataFrame, mmsi_col_name:str='shipid') -> pd.DataFrame:
    """
    discards records with invalid mmsi value
    :param data: dataframe to be checked
    :param mmsi_col_name: dataframe column name for mmsi
    :return: validated dataframe
    """
    data = data.copy()
    invalid = [str(i) * 9 for i in range(10)] + ['123456789']
    data = data[(~data[mmsi_col_name].isin(invalid)) & (data[mmsi_col_name].str.len() == 9)]
    return data


def areas_of_interest(data:pd.DataFrame, multipolygon:shapely.geometry.multipolygon.MultiPolygon,
                      lat_col_name:str='lat', long_col_name:str='lon'):
    """
    Given a geo-multipolygon, returns dataframe entries that are contained within said multipolygon
    :param data: the dataframe to be filtered based on location of data points
    :param multipolygon: the multipolygon that defines the area of interest
    :param lat_col_name: dataframe column name for latitude
    :param long_col_name: dataframe column name for longitude
    :return: dataframe with constrained data points

    sample multipolygon:
        world = geopandas.read_file(geopandas.datasets.get_path('naturalearth_lowres'))
        greece = world[world['name'] == 'Greece']['geometry'].values[0]
    """
    data = data.copy()
    data = geopandas.GeoDataFrame(data, geometry=geopandas.points_from_xy(data[long_col_name], data[lat_col_name]), crs="EPSG:4326")
    data = data[data['geometry'].within(multipolygon)]
    data = pd.DataFrame(data.drop(columns='geometry'))
    return data


