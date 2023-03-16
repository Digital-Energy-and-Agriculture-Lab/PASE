#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  6 16:18:54 2023

@author: roxane
"""

import numpy as np
import matplotlib.pyplot as plt

def graph_1_Yaxis(data_x=None, data1=None, data2=None, data3=None, data4=None, 
                  data_x_name=None, data1_name=None, data2_name=None, data3_name=None, 
                  data4_name=None, ax1_name=None, graph_name=None):
    
    plt.style.use('classic')
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    lgd1 = ax1.plot(data_x, data1, '#F0CD4B', label=data1_name)
    lgd = lgd1
    if data2 is not None:
        lgd2 = ax1.plot(data_x, data2, '#FF9F33', label=data2_name)
        lgd = lgd + lgd2
    if data3 is not None:
        lgd3 = ax1.plot(data_x, data3, '#44C244', label=data3_name)
        lgd = lgd + lgd3
    if data4 is not None:    
        lgd4 = ax1.plot(data_x, data4, '#348335', label=data4_name)  
        lgd = lgd + lgd4            
    ax1.set_ylabel(ax1_name)
    ax1.set_xlabel(data_x_name)
    #fig.title(graph_name)

    lgds = [l.get_label() for l in lgd]
    ax1.legend(lgd, lgds, loc=0)
    ax1.grid()
    plt.show()

    path = 'OUTPUTS/GRAPHS/'+graph_name+'.png'
    fig.savefig(path, format='png')
    
    
def graph_2_Yaxis(data_x=None, data1=None, data2=None, data3=None, data4=None, 
                        data5=None, data6=None, data_x_name=None, data1_name=None, data2_name=None,
                        data3_name=None, data4_name=None, data5_name=None, data6_name=None,
                        ax1_name=None, ax2_name=None, graph_name=None):
    
    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    lgd1 = ax1.plot(data_x, data1, '#FF6103', label=data1_name)
    lgd = lgd1
    if data2 is not None:
        lgd2 = ax1.plot(data_x, data2, '#98F5FF', label=data2_name)
        lgd = lgd + lgd2
    if data3 is not None:
        lgd3 = ax1.plot(data_x, data3, '#CDAA7D', label=data3_name)
        lgd = lgd + lgd3
    if data4 is not None:
        ax2 = ax1.twinx()
        lgd4 = ax2.plot(data_x, data4, '#FF7256', label=data4_name)
        lgd = lgd + lgd4
        ax2.set_ylabel(ax2_name)
    if data5 is not None:    
        lgd5 = ax2.plot(data_x, data5, '#FF4040', label=data5_name)  
        lgd = lgd + lgd5
    if data6 is not None:
        lgd6 = ax2.plot(data_x, data6, '#A52A2A', label=data6_name)     
        lgd = lgd + lgd6
    ax1.set_ylabel(ax1_name)
    ax1.set_xlabel(data_x_name)
    #fig.title(graph_name)

    lgds = [l.get_label() for l in lgd]
    ax1.legend(lgd, lgds, loc=0)
    ax1.grid()
    plt.show()

    path = "OUTPUTS/GRAPHS/" + graph_name + ".png"
    fig.savefig(path, format='png')    
    

    
    
def histogram_3or4_series(x_label, data_s1, data_s2, data_s3, label_s1,
                          label_s2, label_s3, y_label, graph_title,
                          data_s4=None, label_s4=None):
    
    X_axis = np.arange(len(data_s1))
    d = 0.2 
    
    plt.style.use('classic')
    plt.bar(X_axis-1.5*d, data_s1, d, label = label_s1, color='#ffcc00')
    plt.bar(X_axis-d/2, data_s2, d, label = label_s2, color='#4d94ff')
    plt.bar(X_axis+d/2, data_s3, d, label = label_s3, color='#d9d9d9')
    if data_s4 is not None:
        plt.bar(X_axis+1.5*d, data_s4, d, label = label_s4, color='#8C60B6')
    plt.xticks(X_axis, x_label)
    plt.xlim(-1, 12)
    plt.ylabel(y_label, fontweight='bold')
    plt.legend(loc='best')
    plt.grid()
    plt.savefig('OUTPUTS/GRAPHS/'+graph_title+'.png')
    plt.show()