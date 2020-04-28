#!/usr/bin/env python
# Initial Date: January 2020
# Author: Rahul Bhadani
# Copyright (c) Rahul Bhadani, Arizona Board of Regents
# All rights reserved

import subprocess
import yaml
import os
import time
from io import BytesIO
import csv

import rosbag
from std_msgs.msg import String, Header
from geometry_msgs.msg  import Twist, Pose, PoseStamped
from nav_msgs.msg import Path, Odometry
from geometry_msgs.msg import Point, Twist
from sensor_msgs.msg import LaserScan


import numpy  as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sea
plt.style.use('seaborn')

class bagreader:
    '''
    `bagreader` class provides API to read rosbag files in an effective easy manner with significant hassle.
    This class is reimplementation of its MATLAB equivalent that can be found at https://github.com/jmscslgroup/ROSBagReader

    Parameters
    ----------------
    bagfile: `string`
        Bagreader constructor takes name of a bag file as an  argument. name of the bag file can be provided as the full  qualified path, relative path or just the file name.

    Attributes
    --------------
    bagfile: `string`
        Full path of the bag  file, e.g `/home/ece446/2019-08-21-22-00-00.bag`
    filename: `string`
        Name of the bag file, e.g. `2019-08-21-22-00-00.bag`
    dir: `string`
        Directory where bag file is located
    reader: `rosbag.Bag`
        rosbag.Bag object that 

    topic: `pandas dataframe`
        stores the available topic from bag file being read as a table
    n_messages: `integer`
        stores the number of messages
    message_types:`list`, `string`
        stores all the available message types
    datafolder: `string`
        stores the path/folder where bag file is present - may be relative to the bag file or full-qualified path.

        E.g. If bag file is at `/home/ece446/2019-08-21-22-00-00.bag`, then datafolder is `/home/ece446/2019-08-21-22-00-00/`

    message_dictionary: `dictionary`
        message_dictionary will be a python dictionary to keep track of what datafile have been generated mapped by types

    graycolordark: `tuple`
        dark gray color for timeseries plots

    graycolorlight: `tuple`
        light gray color for timeseries plots
    
    linecolor: `tuple`
        a set of line color for timeseries plots
    markercolor: `tuple`
        a set of marker color for timeseries plots

    Example
    ---------
    >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 

    '''

    def __init__(self, bagfile):
        self.bagfile = bagfile
        
        slashindices = find(bagfile, '/')
        
        # length of slashindices list will be zero if a user has pass only bag file name , e.g. 2020-03-04-12-22-42.bag
        if  len(slashindices) > 0:
            self.filename =bagfile[slashindices[-1]:]
            self.dir = bagfile[slashindices[0]:slashindices[-1]]
        else:
            self.filename = bagfile
            self.dir = './'

        self.reader = rosbag.Bag(self.bagfile)

        info = self.reader.get_type_and_topic_info() 
        self.topic_tuple = info.topics.values()
        self.topics = info.topics.keys()

        self.message_types = []
        for t1 in self.topic_tuple: self.message_types.append(t1.msg_type)

        self.n_messages = []
        for t1 in self.topic_tuple: self.n_messages.append(t1.message_count)

        self.frequency = []
        for t1 in self.topic_tuple: self.frequency.append(t1.frequency)

        self.topic_table = pd.DataFrame(list(zip(self.topics, self.message_types, self.n_messages, self.frequency)), columns=['Topics', 'Types', 'Message Count', 'Frequency'])

        self.start_time = self.reader.get_start_time()
        self.end_time = self.reader.get_end_time()

        self.datafolder = bagfile[0:-4]

        if os.path.exists(self.datafolder):
            print("[INFO]  Data folder {0} already exists. Not creating.".format(self.datafolder))
        else:
            try:
                os.mkdir(self.datafolder)
            except OSError:
                print("[ERROR] Failed to create the data folder {0}.".format(self.datafolder))
            else:
                print("[INFO]  Successfully created the data folder {0}.".format(self.datafolder))


        

    def laser_data(self, **kwargs):
        '''
        Class method `laser_data` extracts laser data from the given file, assuming laser data is of type `sensor_msgs/LaserScan`.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of laser scan type

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> laserdatafile = b.laser_data()
        >>> print(laserdatafile)

        '''
        tstart =None
        tend = None
        
        type_to_look ="sensor_msgs/LaserScan"
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time",
                                "header.seq", 
                                "header.frame_id", 
                                "angle_min" , 
                                "angle_max", 
                                "angle_increment", 
                                "time_increment", 
                                "scan_time", 
                                "range_min", 
                                "range_max"]

        for p in range(0, 182):
            column_names.append("ranges_" + str(p))
        for p in range(0, 182):
            column_names.append("intensities_" + str(p))

        all_msg = []
        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            #msg_list = [LaserScan() for count in range(message_counts[i])]
            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend): 
                    #msg_list[k] = msg
                    
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.header.seq, 
                                            msg.header.frame_id, 
                                            msg.angle_min,
                                            msg.angle_max, 
                                            msg.angle_increment, 
                                            msg.time_increment, 
                                            msg.scan_time,  
                                            msg.range_min, 
                                            msg.range_max]

                    ranges = [None]*182
                    intensities = [None]*182

                    for ir, ran in enumerate(msg.ranges):
                        ranges[ir] = ran

                    for ir, ran in enumerate(msg.intensities):
                        intensities[ir] = ran

                    new_row  = new_row + ranges
                    new_row = new_row + intensities
                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def vel_data(self, **kwargs):
        '''
        Class method `vel_data` extracts velocity data from the given file, assuming laser data is of type `geometry_msgs/Twist`.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of geometry_msgs/Twist type

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> veldatafile = b.vel_data()
        >>> print(veldatafile)

        '''
        tstart = None
        tend = None
        
        type_to_look ="geometry_msgs/Twist"
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time",
                                "linear.x", 
                                "linear.y", 
                                "linear.z" , 
                                "angular.x", 
                                "angular.y", 
                                "angular.z"]

        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend):
                    
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.linear.x, 
                                            msg.linear.y,
                                            msg.linear.z,
                                            msg.angular.x,
                                            msg.angular.y,
                                            msg.angular.z]

                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def std_data(self, **kwargs):
        '''
        Class method `std_data` extracts velocity data from the given file, assuming laser data is of type `std_msgs/{bool, byte, Float32, Float64, Int16, Int32, Int8, UInt16, UInt32, UInt64, UInt8}` of 1-dimension.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of `std_msgs/{bool, byte, Float32, Float64, Int16, Int32, Int8, UInt16, UInt32, UInt64, UInt8}`

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> stddatafile = b.std_data()
        >>> print(stddatafile)

        '''
        tstart = None
        tend = None
        
        type_to_look =["std_msgs/Bool", "'std_msgs/Byte", "std_msgs/Float32", "std_msgs/Float64",
                                    "std_msgs/Int8", "std_msgs/Int16", "std_msgs/Int32",
                                    "std_msgs/Uint8", "std_msgs/Uint16", "std_msgs/Uint32"]

        table_rows = self.topic_table[self.topic_table['Types'].isin(type_to_look)]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time", "data"]

        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend):
                    
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.data]

                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def compressed_images(self, **kwargs):
        raise NotImplementedError("To be implemented")

    def odometry_data(self, **kwargs):
        '''
        Class method `odometry_data` extracts velocity data from the given file, assuming laser data is of type `nav_msgs/Odometry`.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of nav_msgs/Odometry type

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> odomdatafile = b.odometry_data()
        >>> print(odomdatafile)

        '''
        tstart = None
        tend = None
        
        type_to_look ="nav_msgs/Odometry"
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time",
                                "header.seq", 
                                "header.frame_id", 
                                "child_frame_id",
                                "pose.x" , 
                                "pose.y", 
                                "pose.z", 
                                "orientation.x", 
                                "orientation.y", 
                                "orientation.z",
                                "orientation.w",
                                "linear.x",
                                "linear.y",
                                "linear.z",
                                "angular.x",
                                "angular.y",
                                "angular.z"]

        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend):
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.header.seq, 
                                            msg.header.frame_id,
                                            msg.child_frame_id,
                                            msg.pose.pose.position.x,
                                            msg.pose.pose.position.y,
                                            msg.pose.pose.position.z,
                                            msg.pose.pose.orientation.x,
                                            msg.pose.pose.orientation.y,
                                            msg.pose.pose.orientation.z,
                                            msg.pose.pose.orientation.w,
                                            msg.twist.twist.linear.x,
                                            msg.twist.twist.linear.y,
                                            msg.twist.twist.linear.z]

                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def wrench_data(self, **kwargs):
        '''
        Class method `wrench_data` extracts velocity data from the given file, assuming laser data is of type `geometry_msgs/Wrench`.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of geometry_msgs/Wrench type

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> wrenchdatafile = b.wrench_data()
        >>> print(wrenchdatafile)

        '''
        tstart = None
        tend = None
        
        type_to_look ="geometry_msgs/Wrench"
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time",
                                "force.x", 
                                "force.y", 
                                "force.z" , 
                                "torque.x", 
                                "torque.y", 
                                "torque.z"]

        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend):
                    
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.force.x, 
                                            msg.force.y,
                                            msg.force.z,
                                            msg.torque.x,
                                            msg.torque.y,
                                            msg.torque.z]

                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def  clock_data(self, **kwargs):
        '''
        Class method `vel_data` extracts velocity data from the given file, assuming laser data is of type `rosgraph_msgs/Clock`.

        Parameters
        -------------
        kwargs
            variable keyword arguments

        Returns
        ---------
        `list`
            A list of strings. Each string will correspond to file path of CSV file that contains extracted data of rosgraph_msgs/Clock type

        Example
        ----------
        >>> b = bagreader('/home/ivory/CyverseData/ProjectSparkle/sparkle_n_1_update_rate_100.0_max_update_rate_100.0_time_step_0.01_logtime_30.0_2020-03-01-23-52-11.bag') 
        >>> clockdatafile = b.clock_data()
        >>> print(clockdatafile)

        '''
        tstart = None
        tend = None
        
        type_to_look ="rosgraph_msgs/Clock"
        table_rows = self.topic_table[self.topic_table['Types']==type_to_look]
        topics_to_read = table_rows['Topics'].values
        message_counts = table_rows['Message Count'].values
        
        column_names = ["Time",
                                "clock.secs", 
                                "clock.nsecs"]

        csvlist = []
        for i in range(len(table_rows)):
            file_to_write = self.datafolder + "/" + topics_to_read[i].replace("/", "-") + ".csv"

            k = 0
            with open(file_to_write, "w", newline='') as f:
                writer = csv.writer(f, delimiter=',')
                writer.writerow(column_names) # write the header
                for topic, msg, t in self.reader.read_messages(topics=topics_to_read[i], start_time=tstart, end_time=tend):
                    new_row = [t.secs + t.nsecs*1e-9, 
                                            msg.clock.secs, 
                                            msg.clock.nsecs]

                    writer.writerow(new_row)
                
                k = k + 1

            csvlist.append(file_to_write)
        return csvlist

    def pointcloud_data(self, **kwargs):
        raise NotImplementedError("To be implemented")

    def plot_vel(self):
        '''
        `plot_vel` plots the timseries velocity data
        '''

        csvfiles = self.vel_data()
        
        dataframes = [None]*len(csvfiles)

        # read the csvfiles into pandas dataframe
        for i, csv in enumerate(csvfiles):
            df = pd.read_csv(csv)
            dataframes[i] = df

        plt.rcParams['figure.figsize'] = [18, 6*len(csvfiles)]
        plt.rcParams['font.size'] = 16.0
        plt.rcParams['legend.fontsize'] = 14.0
        plt.rcParams['xtick.labelsize'] = 14.0
        plt.rcParams['ytick.labelsize'] = 14.0
        plt.rcParams['legend.markerscale']  = 2.0
        
        fig, axs = plt.subplots(len(csvfiles))

        if len(csvfiles) == 1:
            ax_ = []
            ax_.append(axs)
            axs = ax_

        fig.tight_layout(pad=6.0)
        for i, df in enumerate(dataframes):
            sea.scatterplot(x = 'Time', y='linear.x', data=df, marker='D', ax = axs[i], linewidth=0.3, s = 12, color="#2E7473")
            sea.scatterplot(x = 'Time', y='linear.y', data=df, marker='s', ax = axs[i], linewidth=0.3, s= 12, color="#EE5964")
            sea.scatterplot(x = 'Time', y='linear.z', data=df, marker='p', ax = axs[i], linewidth=0.3, s = 12, color="#ED9858")
            sea.scatterplot(x = 'Time', y='angular.x', data=df, marker='P', ax = axs[i], linewidth=0.3, s= 12, color="#EDE358")
            sea.scatterplot(x = 'Time', y='angular.y', data=df, marker='*', ax = axs[i], linewidth=0.3, s= 12, color="#004F4A")
            sea.scatterplot(x = 'Time', y='angular.z', data=df, marker='8', ax = axs[i], linewidth=0.3, s= 12, color="#4F4A00")
            axs[i].legend(df.columns.values[1:])
            axs[i].set_title(csvfiles[i], fontsize=16)
            axs[i].set_xlabel('Time', fontsize=14)
            axs[i].set_ylabel('Messages', fontsize=14)
            
        fig.suptitle("Velocity Timeseries Plot", fontsize = 20)
        plt.show()

    def plot_std(self):
        '''
        `plot_std` plots the timseries standard Messages such as  `std_msgs/{bool, byte, Float32, Float64, Int16, Int32, Int8, UInt16, UInt32, UInt64, UInt8}` of 1-dimension
        '''

        csvfiles = self.std_data()
        
        dataframes = [None]*len(csvfiles)

        # read the csvfiles into pandas dataframe
        for i, csv in enumerate(csvfiles):
            df = pd.read_csv(csv)
            dataframes[i] = df

        plt.rcParams['figure.figsize'] = [18, 6*len(csvfiles)]
        plt.rcParams['font.size'] = 16.0
        plt.rcParams['legend.fontsize'] = 14.0
        plt.rcParams['xtick.labelsize'] = 14.0
        plt.rcParams['ytick.labelsize'] = 14.0
        plt.rcParams['legend.markerscale']  = 2.0
        
        fig, axs = plt.subplots(len(csvfiles))

        if len(csvfiles) == 1:
            ax_ = []
            ax_.append(axs)
            axs = ax_
        
        fig.tight_layout(pad=6.0)
        for i, df in enumerate(dataframes):
            sea.scatterplot(x = 'Time', y='data', data=df, marker='D', ax = axs[i], linewidth=0.3, s = 12, color="#2E7473")
            axs[i].legend(df.columns.values[1:])
            axs[i].set_title(csvfiles[i], fontsize=16)
            axs[i].set_xlabel('Time', fontsize=14)
            axs[i].set_ylabel('Messages', fontsize=14)
            
        fig.suptitle("Standard Messages Timeseries Plot", fontsize = 20)
        plt.show()

    def plot_odometry(self):
        '''
        `plot_odometry` plots the timseries odometry data
        '''

        csvfiles = self.odometry_data()
        
        dataframes = [None]*len(csvfiles)

        # read the csvfiles into pandas dataframe
        for i, csv in enumerate(csvfiles):
            df = pd.read_csv(csv)
            dataframes[i] = df

        plt.rcParams['figure.figsize'] = [18, 6*len(csvfiles)]
        plt.rcParams['font.size'] = 16.0
        plt.rcParams['legend.fontsize'] = 14.0
        plt.rcParams['xtick.labelsize'] = 14.0
        plt.rcParams['ytick.labelsize'] = 14.0
        plt.rcParams['legend.markerscale']  = 2.0

        fig, axs = plt.subplots(len(csvfiles))

        if len(csvfiles) == 1:
            ax_ = []
            ax_.append(axs)
            axs = ax_

        print(axs)
        fig.tight_layout(pad=6.0)
        for i, df in enumerate(dataframes):
            sea.scatterplot(x = 'Time', y='pose.x', data=df, marker='D', ax = axs[i], linewidth=0.3, s = 12, color="#2E7473")
            sea.scatterplot(x = 'Time', y='pose.y', data=df, marker='D', ax = axs[i], linewidth=0.3, s= 12, color="#EE5964")
            sea.scatterplot(x = 'Time', y='pose.z', data=df, marker='D', ax = axs[i], linewidth=0.3, s = 12, color="#ED9858")
            sea.scatterplot(x = 'Time', y='orientation.x', data=df, marker='*', ax = axs[i], linewidth=0.3, s= 12, color="#EDE358")
            sea.scatterplot(x = 'Time', y='orientation.y', data=df, marker='*', ax = axs[i], linewidth=0.3, s= 12, color="#004F4A")
            sea.scatterplot(x = 'Time', y='orientation.z', data=df, marker='8', ax = axs[i], linewidth=0.3, s= 12, color="#4F4A00")
            sea.scatterplot(x = 'Time', y='orientation.w', data=df, marker='8', ax = axs[i], linewidth=0.3, s= 12, color="#004d40")
            sea.scatterplot(x = 'Time', y='linear.x', data=df, marker='s', ax = axs[i], linewidth=0.3, s= 12, color="#ba68c8")
            sea.scatterplot(x = 'Time', y='linear.y', data=df, marker='s', ax = axs[i], linewidth=0.3, s= 12, color="#2C0C32")
            sea.scatterplot(x = 'Time', y='linear.z', data=df, marker='P', ax = axs[i], linewidth=0.3, s= 12, color="#966851")
            sea.scatterplot(x = 'Time', y='angular.x', data=df, marker='P', ax = axs[i], linewidth=0.3, s= 12, color="#517F96")
            sea.scatterplot(x = 'Time', y='angular.y', data=df, marker='p', ax = axs[i], linewidth=0.3, s= 12, color="#B3C1FC")
            sea.scatterplot(x = 'Time', y='angular.z', data=df, marker='p', ax = axs[i], linewidth=0.3, s= 12, color="#FCEFB3")
            axs[i].legend(df.columns.values[4:])
            axs[i].set_title(csvfiles[i], fontsize=16)
            axs[i].set_xlabel('Time', fontsize=14)
            axs[i].set_ylabel('Messages', fontsize=14)
            
        fig.suptitle("Odometry Messages Timeseries Plot", fontsize = 20)
        plt.show()

    def plot_wrench(self):
        '''
        `plot_wrench` plots the timseries wrench data
        '''

        csvfiles = self.wrench_data()
        
        dataframes = [None]*len(csvfiles)

        # read the csvfiles into pandas dataframe
        for i, csv in enumerate(csvfiles):
            df = pd.read_csv(csv)
            dataframes[i] = df

        plt.rcParams['figure.figsize'] = [18, 6*len(csvfiles)]
        plt.rcParams['font.size'] = 16.0
        plt.rcParams['legend.fontsize'] = 14.0
        plt.rcParams['xtick.labelsize'] = 14.0
        plt.rcParams['ytick.labelsize'] = 14.0
        plt.rcParams['legend.markerscale']  = 2.0

        fig, axs = plt.subplots(len(csvfiles))

        if len(csvfiles) == 1:
            ax_ = []
            ax_.append(axs)
            axs = ax_
            
        fig.tight_layout(pad=6.0)
        for i, df in enumerate(dataframes):
            sea.scatterplot(x = 'Time', y='force.x', data=df, marker='D', ax = axs[i], linewidth=0.3, s = 12, color="#2E7473")
            sea.scatterplot(x = 'Time', y='force.y', data=df, marker='s', ax = axs[i], linewidth=0.3, s= 12, color="#EE5964")
            sea.scatterplot(x = 'Time', y='force.z', data=df, marker='*', ax = axs[i], linewidth=0.3, s = 12, color="#ED9858")
            sea.scatterplot(x = 'Time', y='torque.x', data=df, marker='P', ax = axs[i], linewidth=0.3, s= 12, color="#EDE358")
            sea.scatterplot(x = 'Time', y='torque.y', data=df, marker='p', ax = axs[i], linewidth=0.3, s= 12, color="#004F4A")
            sea.scatterplot(x = 'Time', y='torque.z', data=df, marker='8', ax = axs[i], linewidth=0.3, s= 12, color="#4F4A00")
            axs[i].legend(df.columns.values[1:])
            axs[i].set_title(csvfiles[i], fontsize=16)
            axs[i].set_xlabel('Time', fontsize=14)
            axs[i].set_ylabel('Messages', fontsize=14)
            
        fig.suptitle("Wrench Timeseries Plot", fontsize = 20)
        plt.show()

    def animate_laser(self):
        raise NotImplementedError("To be implemented")

    def animate_pointcloud(self):
        raise NotImplementedError("To be implemented")

def find(s, ch):
    '''
    Function `find` returns indices all the occurence of `ch` in `s` 

    Parameters
    -------------
    s: `string`
        String or a setence where to search for occurrences of the character `ch`

    s: `char`
        Character to look for

    Returns
    ---------
    `list`
        List of indices of occurrences of character `ch` in the string `s`.

    '''
    return [i for i, ltr in enumerate(s) if ltr == ch]



    
    
def timeindex(df, inplace=False):
    '''
    Convert multi Dataframe of which on column must be 'Time'  to pandas-compatible timeseries where timestamp is used to replace indices

    Parameters
    --------------

    df: `pandas.DataFrame`
        A pandas dataframe with two columns with the column names "Time" and "Message"

    inplace: `bool`
        Modifies the actual dataframe, if true, otherwise doesn't.

    Returns
    -----------
    `pandas.DataFrame`
        Pandas compatible timeseries with a single column having column name "Message" where indices are timestamp in hum  an readable format.
    '''
    
    if inplace:
        newdf = df
    else:
        newdf =df.copy()

    newdf['Time'] = df['Time']
    newdf['ClockTime'] = newdf['Time'].apply(dateparse)
    Time = pd.to_datetime(newdf['Time'], unit='s')
    newdf['Clock'] = pd.DatetimeIndex(Time)
    
    if inplace:
        newdf.set_index('Clock', inplace=inplace)
        newdf.drop(['ClockTime'], axis = 1, inplace=inplace)
    else:
        newdf = newdf.set_index('Clock')
        newdf = newdf.drop(['ClockTime'], axis = 1)
    return newdf