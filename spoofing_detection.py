# -*- coding: utf-8 -*-
"""
author: "Omnia Kahla"
date: 2021-09-02
version: 1.0
input: AIS data
output: Spoofing detection
command: python SpoofingDetection.py
this code is provided without any warranty or responsibilty
the author is not responsible for any damage caused by using this code
"""

import math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN

def load_data(file_path):
    """
    this function loads the data from a csv file
    it takes as input the file path
    it returns the dataframe
    :param file_path: file path
    :return: dataframe
    """
    df = pd.read_csv(file_path)
    return df


def get_cluster_insights(df_original, n_neighbors, mmsi):
    """
    this function detects the clusters and returns whether the trajectory has location spoofing or identity spoofing or both or none
    it takes as input the dataframe, the number of neighbors and the mmsi
    it returns the insights
    :param df_original: dataframe
    :param n_neighbors: number of neighbors
    :param mmsi: mmsi
    :return: has problem ,has location spoofing,has identity spoofing, # of clusters
    """

    
    # print(list(df_original.columns.values))
    df = df_original.groupby('speed')['# Timestamp'].size().reset_index(name='count')
    sog_st_dev = np.std(df['speed'])
    sog_mean = np.mean(df['speed'])
    threshold= sog_mean+4*sog_st_dev # threshold in knot should be changed to m/s
    if threshold<=1: # Check if the vessel is anchored the whole day then skip the algorithm. The algorithm works with the moored vessels. 
        return False, False, False, -1
    df = df_original[["x", "y"]]

    if len(df) == 0:
        return False, False, False, -1
    nbrs = NearestNeighbors(n_neighbors=n_neighbors).fit(df)
    try:
        neigh_dist, neigh_ind = nbrs.kneighbors(df)
    except ValueError:
        return False, False, False, -1

    eps = np.quantile(neigh_dist[:, n_neighbors-1], q=0.9) #90% of the data are in the same cluster. 

    if eps == 0.0:  # anchored vessel for the whole day or base station
        return False, False, False, -1
    min_samples = 5  # an arbitrary value based on my experiments
    clusters = DBSCAN(eps=eps, min_samples=min_samples).fit(df)

    unique_clusters = set(clusters.labels_)
    clusters_labels = list(clusters.labels_)
    se = pd.Series(clusters_labels)
    df_original['cluster_label'] = se.values
    grouped = df_original.groupby('cluster_label')  # To avoid the warning message remove the list
    df_groups = pd.DataFrame(columns=["cluster", "length"])
    df_groups.set_index('cluster')
    for name, group in grouped:
        df_temporary = group
        df_temporary.sort_values(by=['# Timestamp'])
        import os
        # Create the "Clusters" folder if it doesn't exist
        folder_name = "Clusters"
        if not os.path.exists(folder_name):
            os.makedirs(folder_name)
        df_groups.loc[str(name)] = {"cluster": name, "length": len(group)}
        df_temporary.to_csv(path_or_buf=os.path.join(folder_name, f"{mmsi}_trajectoryID_{name}.csv"), sep=',', header=True, index=False, index_label=None, mode='w', encoding=None)

    hasLocationSpoofing = False
    hasIdentitySpoofing = False
    has_problem = False
    df_temp = pd.DataFrame(columns=["cluster_label", "t", "x", "y"])
    # count_ofJumps = 0
    calculatedSpeed = 0
    num_of_points_speed_exceeds_1000 = 0
    count_of_outliers = 0
    df_outliers = df_original.iloc[:0, :].copy()
    if len(unique_clusters) <= 1:  # only single trajectory
        return False, False, False, len(unique_clusters)
    current_Label = clusters_labels[0]
    outlier_cluster_name = -2
    outlier_clusters = set()  # creating a set of all outliers clusters
    for i in range(1, len(clusters_labels)):  # adds the 2 consective points that are in different clusters
        if current_Label != clusters_labels[i]:
            current_Label = clusters_labels[i]
            rec_in_cluster = df_original.iloc[i]
            second_point = {'cluster_label': clusters_labels[i], 't': rec_in_cluster["# Timestamp"],
                            'x': rec_in_cluster["x"], 'y': rec_in_cluster["y"]}
            rec_in_cluster = df_original.iloc[i - 1]
            first_point = {'cluster_label': clusters_labels[i - 1], 't': rec_in_cluster["# Timestamp"],
                           'x': rec_in_cluster["x"], 'y': rec_in_cluster["y"]}
            calculatedSpeed = calculate_speed_between_points(first_point, second_point)

            if calculatedSpeed > threshold:
                num_of_points_speed_exceeds_1000 += 1
                outlier_point_index, outlier_cluster_name = compare_cluster_density_return_outlier_index(
                    first_point["cluster_label"], second_point["cluster_label"], i, df_groups)
                outlier_clusters.add(str(outlier_cluster_name))
                count_of_outliers += 1
                df_outliers.loc[count_of_outliers] = df_original.iloc[outlier_point_index]

    df_temp["t"] = pd.to_datetime(df_temp["t"])

    if len(df_outliers) != 0:
        df_outliers.drop_duplicates(subset=['# Timestamp', 'x', 'y'], keep='last', inplace=True)
        df_outliers.to_csv(path_or_buf=f"Clusters/{mmsi}_outlier.csv", sep=',', header=True, index=False,
                           index_label=None, mode='w', encoding=None)
    density_of_points_speed_exceeds_1000 = num_of_points_speed_exceeds_1000 / len(df)
    if density_of_points_speed_exceeds_1000 > 0.1:
        has_problem = True
        for name, group in grouped:
            df_temporary = group
            df_temporary.sort_values(by=['# Timestamp'])
            hasLocationSpoofing = calculated_speed_between_points_in_cluster(df_temporary, threshold)
        if hasLocationSpoofing == False:
            hasIdentitySpoofing = True
    elif density_of_points_speed_exceeds_1000 < 0.1 and density_of_points_speed_exceeds_1000 > 0:
        has_problem = True
        hasLocationSpoofing = True
    
    return has_problem, hasLocationSpoofing, hasIdentitySpoofing, len(unique_clusters)


def compare_cluster_density_return_outlier_index(cluster1, cluster2, index, df_groups):
    if df_groups.loc[str(cluster1)]["length"] > df_groups.loc[str(cluster2)]["length"]:
        return index, cluster2
    else:
        return index - 1, cluster1
    


def calculate_speed_between_points(point1, point2):
    """
    this function calculates the speed between 2 points
    it takes as input the 2 points
    it returns the speed
    :param point1: point1
    :param point2: point2
    :return: speed
    """

    calculated_Distance= calculate_speed_Haversin_distance(point1,point2)
    time_diff = abs(pd.to_datetime(point2["t"]) - pd.to_datetime(point1["t"]))

    if time_diff.total_seconds() == 0:  # division over zero exception
        calculatedSpeed = 0
    else:
        calculatedSpeed = calculated_Distance / time_diff.total_seconds()


    return calculatedSpeed


def calculated_speed_between_points_in_cluster(df_temp,threshold):
    """
    this function calculates speed between points in a Cluster
    it takes as input the dataframe that contains the points where the cluster changes
    it returns whether it has location spoofing or identity spoofing
    :param df_temp: dataframe
    :return: hasLocationSpoofing,hasIdentitySpoofing
    """
    hasLocationSpoofing = False
    hasIdentitySpoofing=False
    for i in range(1, len(df_temp)):
        first_point = {'t': df_temp.iloc[i - 1]["# Timestamp"],
                            'x': df_temp.iloc[i - 1]["x"], 'y': df_temp.iloc[i - 1]["y"]}
        second_point = { 't': df_temp.iloc[i]["# Timestamp"],
                            'x': df_temp.iloc[i]["x"], 'y': df_temp.iloc[i]["y"]}
        calculatedSpeed = calculate_speed_between_points(first_point, second_point)
        if calculatedSpeed > threshold:
            hasLocationSpoofing = True
            break

    return hasLocationSpoofing


def find_eps(sort_neigh_dist, leng):
    """
    this function finds the eps
    it takes as input the sorted neighbor distances and the length
    it returns the eps
    :param sort_neigh_dist: sorted neighbor distances
    :param leng: length
    :return: eps
    """
    k_dist = sort_neigh_dist[:, leng]
    i = 0
    while i < len(k_dist) - 1:
        diff = k_dist[i + 1] - k_dist[i]
        if (diff > 700):
            break
        i += 1
        
    plt.axhline(y=k_dist[i], color='r', linestyle='-')
    plt.plot(k_dist,  marker="o", markersize=1, markeredgecolor="red", markerfacecolor="green")
    plt.ylabel("k-NN distance")
    plt.xlabel("Sorted observations (4th NN)")
    #plt.show()
    return k_dist[i]


def rad2deg(radians):
    degrees = radians * 180 / np.pi
    return degrees

def deg2rad(degrees):
    radians = degrees * np.pi / 180
    return radians

def calculate_distance_based_on_latlon(point1, point2):
    earth_radius = 6371000

    # Convert degrees to radians
    lat1_rad = math.radians(point1["x"])
    lon1_rad = math.radians(point1["y"])
    lat2_rad = math.radians(point2["x"])
    lon2_rad = math.radians(point2["y"])

    # Calculate the differences between the coordinates
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad

    # Haversine formula
    a = math.sin(d_lat/2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon/2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    # Calculate the distance
    distance = earth_radius * c
    return distance


def calculate_speed_Haversin_distance(point1, point2, unit='kilometers'):
    
    theta = point1["y"] - point2["y"]    
    distance = 60 * 1.1515 * rad2deg(
        np.arccos(
            (np.sin(deg2rad(point1["x"])) * np.sin(deg2rad(point2["x"]))) + 
            (np.cos(deg2rad(point1["x"])) * np.cos(deg2rad(point2["x"])) * np.cos(deg2rad(theta)))
        )
    )
    
    return round(distance * 1.609344, 2)*1000 # distance in meters

