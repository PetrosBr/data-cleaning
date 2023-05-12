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
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.neighbors import NearestNeighbors
from sklearn.cluster import DBSCAN
from sklearn.cluster import KMeans
from sklearn import preprocessing
from shapely.geometry import Point
from shapely import wkt
import os


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
    df = df_original[["x", "y"]]
    if len(df) == 0:
        return False, False, False, -1
    nbrs = NearestNeighbors(n_neighbors=n_neighbors).fit(df)
    try:
        neigh_dist, neigh_ind = nbrs.kneighbors(df)
    except ValueError:
        return False, False, False, -1
    sort_neigh_dist = np.sort(neigh_dist, axis=0)
    eps = find_eps(sort_neigh_dist, n_neighbors - 1)
    # print("eps",eps)
    if eps == 0.0:  # anchored vessel for the whole day or base station
        return False, False, False, -1
    min_samples = 5  # an arbitrary value based on my experiments
    clusters = DBSCAN(eps=eps, min_samples=min_samples).fit(df)
    unique_clusters = set(clusters.labels_)
    clusters_labels = list(clusters.labels_)
    hasLocationSpoofing = False
    hasIdentitySpoofing = False
    has_problem = False
    df_temp = pd.DataFrame(columns=["cluster_label", "t", "x", "y"])
    count_ofJumps = 0
    calculatedSpeed = 0
    num_of_points_speed_exceeds_1000 = 0
    if len(unique_clusters) <= 1:  # only single trajectory
        return False, False, False, len(unique_clusters)
    current_Label = clusters_labels[0]
    for i in range(1, len(clusters_labels)):  # adds the 2 consective points that are in different clusters
        if current_Label != clusters_labels[i]:
            current_Label = clusters_labels[i]
            rec_in_cluster = df_original.iloc[i]
            second_point = {'cluster_label': clusters_labels[i], 't': rec_in_cluster["# Timestamp"],
                            'x': rec_in_cluster["x"], 'y': rec_in_cluster["y"]}
            rec_in_cluster = df_original.iloc[i - 1]
            first_point = {'cluster_label': clusters_labels[i - 1], 't': rec_in_cluster["# Timestamp"],
                           'x': rec_in_cluster["x"], 'y': rec_in_cluster["y"]}
            calculatedSpeed, in_same_cluster = calculate_speed_between_points(first_point, second_point, eps)
            if in_same_cluster:
                continue
            if calculatedSpeed > 1000:
                num_of_points_speed_exceeds_1000 += 1
            df_temp.loc[count_ofJumps] = first_point
            df_temp.loc[count_ofJumps + 1] = second_point
            count_ofJumps += 2
    df_temp["t"] = pd.to_datetime(df_temp["t"])

    desityOfHops = count_ofJumps / len(df)
    density_of_points_speed_exceeds_1000 = num_of_points_speed_exceeds_1000 / len(df)
    # for i in range(0,len(df_temp),2):#checks if the #jumps between 2 clusters >10% of the points and speed>1000 then its identitySpoofing, else if the speed>1000 & # points<10% then LocationSpoofing
    #     calculatedSpeed,in_same_cluster=calculate_speed_between_points(df_temp.loc[i],df_temp.loc[i+1],eps)
    #     #print(f"calculatedSpeed = {calculatedSpeed}")
    #     if calculatedSpeed >1000:
    #         num_of_points_speed_exceeds_1000+=1
    #     # if(calculatedSpeed>1000):
    #     #     print(f"calculatedSpeed = {calculatedSpeed}, hasLocationSpoofing={hasLocationSpoofing},hasIdentitySpoofing={hasIdentitySpoofing} ")
    # density_of_points_speed_exceeds_1000 = num_of_points_speed_exceeds_1000/len(df)
    for i in range(0, len(clusters_labels)):
        if density_of_points_speed_exceeds_1000 > 0.1 and desityOfHops > 0.1:  # densityOffirstCluster>0.1 and densityOfSecondCluster>0.1:
            hasIdentitySpoofing, hasLocationSpoofing = calculated_speed_between_points_in_cluster(df_temp, eps,
                                                                                                  clusters_labels)
            has_problem = True
            # hasIdentitySpoofing=True
        elif density_of_points_speed_exceeds_1000 < 0.1:
            has_problem = True
            hasLocationSpoofing = True
    return has_problem, hasLocationSpoofing, hasIdentitySpoofing, len(unique_clusters)


def calculate_speed_between_points(point1, point2, eps):
    """
    this function calculates the speed between 2 points
    it takes as input the 2 points
    it returns the speed
    :param point1: point1
    :param point2: point2
    :return: speed
    """
    calculatedSpeed = 0
    calculated_Distance = math.sqrt(math.pow(
        (point1["x"] - point2["x"]), 2) + math.pow((point1["y"] - point2["y"]), 2))

    time_diff = abs(pd.to_datetime(point2["t"]) - pd.to_datetime(point1["t"]))
    in_same_cluster = False
    if time_diff.total_seconds() == 0:  # division over zero exception
        calculatedSpeed = 0
    else:
        calculatedSpeed = calculated_Distance / time_diff.total_seconds()
    if calculated_Distance <= eps:
        in_same_cluster = True
    return calculatedSpeed, in_same_cluster


def calculated_speed_between_points_in_cluster(df_temp, eps, clusters_labels):
    """
    this function calculates speed between points in a Cluster
    it takes as input the dataframe that contains the points where the cluster changes
    it returns whether it has location spoofing or identity spoofing 
    :param df_temp: dataframe
    :return: hasLocationSpoofing,hasIdentitySpoofing
    """
    hasLocationSpoofing = False
    hasIdentitySpoofing = False
    df_temp = df_temp.sort_values(by=['cluster_label', 't'])
    cluster = df_temp.iloc[0]["cluster_label"]
    for i in range(1, len(df_temp)):
        if cluster == df_temp.iloc[i]["cluster_label"]:
            calculatedSpeed, in_same_cluster = calculate_speed_between_points(df_temp.iloc[i - 1], df_temp.iloc[i], eps)
            if in_same_cluster:
                hasLocationSpoofing = True
                continue
            elif calculatedSpeed > 1000:
                hasIdentitySpoofing = True
                continue
            else:
                hasLocationSpoofing = True
                continue
        else:
            cluster = df_temp.iloc[i]["cluster_label"]

    return hasLocationSpoofing, hasIdentitySpoofing


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
    return k_dist[i]
