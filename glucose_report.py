import json 
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import datetime as dt
import pandas as pd
import numpy as np
import math as math
from scipy.stats import sem
from scipy import interpolate
from calendar import month_name
from fpdf import FPDF, HTMLMixin


'''**WARNING** 
This program was not created by and has never been assesd by a medical professional at any point. 
**Do not use this script to asses or monitor your health**. Please use accredited programs and 
equipment that have been recomended by medical professionals to monitor and asses your blood glucose 
levels. This script is just an excersise in parsing and displaying JSON data. '''


############ Data processing and calculations ############

#read json file and create dataframe 
with open('INSERT JSON FILE TO BE ANALYZED') as json_data:
    data = json.load(json_data)
    df = pd.DataFrame(data['BgReadings'])

#convert date string to a datetime object
df['dateString'] = pd.to_datetime(df['dateString'], format= '%Y-%m-%dT%H:%M:%S.%fZ')

#create mmol column 
df['mmol'] = df['sgv']*0.0555

#create a1c columns 
df['a1c_pc'] = (df['sgv']+46.7)/28.7
df['a1c_mmol'] = 10.929 * (df['a1c_pc'] - 2.15)

#calculate a1c and hba1c means and round to two decimal places 
a1c_mean_pc = round(df['a1c_pc'].mean(),2)
hba1c_mean_pc = round(df['a1c_mmol'].mean(),2)

#get start and end date 
start_date = df['dateString'][0].strftime('%d-%b-%Y')
end_date = df['dateString'].iloc[-1].strftime('%d-%b-%Y')

#calculate the total number of reading taken by sensor 
tot_readings = df.index[-1]

#calculate time difference between readings 
df['timediff_s'] = df['dateString'].diff().apply(lambda x: x/np.timedelta64(1, 's')).fillna(0).astype('int64')

#calculate total time measured 
tot_time  = df['timediff_s'].sum()

#calculate average time per reading over the 90 days. 
avg_time_per_reading = round((tot_time/tot_readings)/60, 2)

#print total reading to consol 
print(tot_readings)

################ 90 day section #################

#group by month and aggregate data on mmol 

month_day = df.groupby([df['dateString'].dt.month_name(), df['dateString'].dt.day], 
                       sort=False).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min'))

month_day_hour = df.groupby([df['dateString'].dt.month_name(), df['dateString'].dt.day, df['dateString'].dt.hour], 
                       sort=False).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min'))


#create absolute values of std to plot 
month_day['std+'] = month_day['mean_mmol']+month_day['std_mmol']
month_day['std-'] = month_day['mean_mmol']-month_day['std_mmol']


# get the number of the number of months
months = month_day.index.levels[0]


#number of plots 
nplots = months.size

#set plot width ratios
plots_width_ratios = [month_day.xs(month).index.size+1 for month in months]

#create 90 day figure 
fig_90, axes_90 = plt.subplots(nrows=1, ncols=nplots, sharey=True, figsize=(15, 5), dpi=500,
                         gridspec_kw = dict(width_ratios=plots_width_ratios, wspace=0.05), )


# Loop through array of axes to create grouped scatter plot for each month
alpha = 0.3 # used for grid lines, bottom spine and separation lines between zones
for last_day, month, ax in zip(plots_width_ratios, months, axes_90):
    
    #plot the hourly averages for each day 
    y = month_day_hour['mean_mmol'].xs(month).values
    x = month_day_hour['mean_mmol'].xs(month).index.get_level_values(0)
    
    ax.plot(x, y, marker = 'o', linestyle='', alpha = 0.2, color='sandybrown', zorder=0)

    # Create plot for the dily averages 
    month_day['mean_mmol'].xs(month).plot(ax=ax, legend=False, linestyle='--', marker = 'o', alpha = 1, color='forestgreen', zorder=2)
    
    #ax.fill_between(month_day['mean_mmol'].xs(month).index,  month_day['std+'].xs(month), month_day['std-'].xs(month), 
                    #alpha=0.3, color = 'grey')

    ax.autoscale(tight=False)
    ax.set_xlim([0, last_day+2])
    ax.set_ylim([0, 25])

    ax.axhline(y = 9, color = 'red', linestyle = ':')
    ax.axhline(y = 4, color = 'blue', linestyle = ':')

    for spine in ['top', 'left', 'right']:
        ax.spines[spine].set_visible(False)
        ax.spines['bottom'].set_alpha(alpha)

    # Set and place x labels for factory zones
    ax.set_xlabel(month, fontweight='bold', fontsize=12)
    ax.set_ylabel('Blood glucose (mmol/l)', fontweight='bold', fontsize=12)
    
    # remove ticks
    ax.tick_params(axis='both', length=0, pad=5, color='grey', labelsize=10)

#manually add the legend 
patch = [Line2D([0], [0], marker='o', color='w', label='Hourly Average',
                          markerfacecolor='sandybrown', markersize=10, alpha=0.7),
        Line2D([0], [0], marker='o', color='w', label='Daily Average',
                          markerfacecolor='forestgreen', markersize=10)]


ax.legend(handles=patch, fontsize="15")

fig_90.savefig('90_day.jpg',bbox_inches='tight') 

############# percentage time in target ###########

#group time difference by the value of mmol 
target_bins = df.groupby(pd.cut(df['mmol'], [0, 4, 9, 30]))['timediff_s'].sum().reset_index()

#get binned values of summed time 
low_time = target_bins['timediff_s'].loc[0]
target_time = target_bins['timediff_s'].loc[1]
high_time = target_bins['timediff_s'].loc[2]

#work out percentages 
low_pc = round((low_time/tot_time)*100, 2)
target_pc = round((target_time/tot_time)*100,2)
high_pc = round((high_time/tot_time)*100,2)

#make lists to plot 
pc = [round(target_pc), round(low_pc), round(high_pc)]
state = ['Target', 'Low', 'High']

# plot % time in target graph 
fig_pctime, ax2 = plt.subplots(figsize=(5,5), dpi=500)
ax2.bar(state, pc, color = ['darkgreen', 'lightsteelblue', 'darkred'])
ax2.set_xlabel('State',fontweight='bold')
ax2.set_ylabel('% Time',fontweight='bold')
ax2.set_ylim([0,100])

for spine in ['top', 'right']:
        ax2.spines[spine].set_visible(False)
        

fig_pctime.savefig('pc_time.jpg', bbox_inches='tight') 


#frequency in different states 

in_target = (df['mmol'] >= 4) & (df['mmol'] <= 9)
df_target = df[in_target]

in_high = df['mmol'] > 9 
df_high = df[in_high]

in_low = df['mmol'] < 4
df_low = df[in_low]


#plot frequency figure 
fig_hist_state, (ax3, ax4, ax5) = plt.subplots(3, figsize=(7,10), dpi=500)
target_hour = df.groupby(df_target['dateString'].dt.hour)['mmol'].count().plot(kind='bar', color = 'forestgreen', ax=ax3, xlabel='' )
high_hour = df.groupby(df_high['dateString'].dt.hour)['mmol'].count().plot(kind='bar', color = 'darkred', ax=ax4, xlabel='')
low_hour = df.groupby(df_low['dateString'].dt.hour)['mmol'].count().plot(kind='bar', color = 'lightsteelblue', ax=ax5, xlabel='')

#universal labels 
fig_hist_state.supxlabel('Hours of the day')
fig_hist_state.supylabel('Frequncy of readings')


fig_hist_state.savefig('hist.jpg',bbox_inches='tight')


########### average week graph ###########

#group data by week and day

avg_week = df.groupby([df['dateString'].dt.isocalendar().week, df['dateString'].dt.dayofweek], 
                       sort=False).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min'))

avg_day = df.groupby(df['dateString'].dt.dayofweek, 
                       sort=False).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min'))


# get the number of the number of months
weeks = avg_week.index.levels[0]

#create avg week figure 
fig_avg_week , ax6 = plt.subplots(figsize=(7,5), dpi=500)

# Loop weeks and make average for each week in 90 day period 
for week in weeks:
     avg_week['mean_mmol'].xs(week).plot(ax=ax6, legend=False, linestyle='', marker='o', markersize = 14, alpha = 0.3, color='sandybrown')

#plot average week for total 90 days
avg_day['mean_mmol'].plot(ax=ax6, legend=False, linestyle='--', marker='o', markersize = 14, alpha = 1, color='forestgreen')

#add highlow lines 
ax6.axhline(y = 9, color = 'red', linestyle = ':')
ax6.axhline(y = 4, color = 'blue', linestyle = ':')

#remove box 
for spine in ['top', 'right']:
    ax6.spines[spine].set_visible(False)

#set figure bits and bobs 
ax6.set_xlabel(xlabel='')
ax6.set_ylabel('Blood glucose (mmol/l)', fontweight='bold', fontsize=15)
ax6.set_xticks(ticks=list(range(0, 7)) )
ax6.set_xticklabels(['Mon', 'Tue','Wed', 'Thur', 'Fri', 'Sat', 'Sun'], weight='bold', fontsize=14)
ax6.set_yticks(ticks=list(range(0, 21, 2)) )
ax6.set_yticklabels(ax6.get_yticks(), weight='bold', fontsize=14)


patch = [Line2D([0], [0], marker='o', color='w', label='Weekly Day Average',
                          markerfacecolor='sandybrown', markersize=10, alpha=0.7),
        Line2D([0], [0], marker='o', color='w', label='90 Day Daily Average',
                          markerfacecolor='forestgreen', markersize=10)]

ax6.legend(handles=patch, fontsize="15")

ax6.set_ylim(0, 20)

#save figure 
fig_avg_week.savefig('average_week.jpg', bbox_inches='tight')



########### average day graph ###########

#group data by hour and day and min and hour 
min_day = df.groupby([df['dateString'].dt.hour, df['dateString'].dt.minute,], 
                       sort=False).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min'))

hour_day = df.groupby(df['dateString'].dt.hour, 
                       sort=True).agg(mean_mmol=('mmol', 'mean'), count_mmol=('mmol', 'count'),
                        std_mmol=('mmol', 'std'), max_mmol=('mmol', 'max'), min_mmol=('mmol', 'min')).reset_index()

print(min_day[0:100])

print()

print(hour_day)


#create the figure 
fig_avg_day, ax7 =plt.subplots(figsize=(10,5), dpi=500)

# x and y values for each day average mean mmol
y = min_day['mean_mmol'].values
x = min_day['mean_mmol'].index.get_level_values(0)

#plot mean values for minute for a given hour of each day 
ax7.plot(x, y, marker = 'o', linestyle='', alpha = 0.3, color='sandybrown', markersize = 10, zorder=0)

#plot mean for each hour of an average day 
ax7.plot(hour_day['dateString'], hour_day['mean_mmol'], linestyle='--', marker = 'o', markersize = 10, alpha = 1, color='forestgreen', zorder=2)

#add high and low lines 
ax7.axhline(y = 9, color = 'red', linestyle = ':')
ax7.axhline(y = 4, color = 'blue', linestyle = ':')

#remove box 
for spine in ['top', 'right']:
    ax7.spines[spine].set_visible(False)
    
#set graph bits and bobs
ax7.set_ylabel('Blood glucose (mmol/l)', fontweight='bold', fontsize=15)
ax7.set_xticks(ticks=list(range(0, 24)) )
ax7.set_xticklabels(ax7.get_xticks(), weight='bold', fontsize=14)
ax7.set_yticks(ticks=list(range(0, 15, 2)) )
ax7.set_yticklabels(ax7.get_yticks(), weight='bold', fontsize=14)


patch = [Line2D([0], [0], marker='o', color='w', label='Minute Average',
                          markerfacecolor='sandybrown', markersize=10, alpha=0.7),
        Line2D([0], [0], marker='o', color='w', label='Hourly Average',
                          markerfacecolor='forestgreen', markersize=10)]

ax7.legend(handles=patch, fontsize="15")

ax7.set_ylim(0, 15)

#save file 
fig_avg_day.savefig('average_day.jpg', bbox_inches='tight')



######### report building ##############
# 1. Set up the PDF doc basics
pdf = FPDF(orientation = 'P', unit = 'mm', format='A4')
pdf.add_page()




## Title
pdf.set_font('Arial', 'B', 16)
pdf.cell(40, 10, border=0, ln = 0)
pdf.cell(120, 10, 'Glucose report for ***INSERT OWN NAME***', ln =0, align='C', border=0)
pdf.ln(20)


# timeframe of the analysis period 
pdf.set_font('Arial','', 12)
pdf.multi_cell(w=0, h=5, txt= "This report encompases a total of " +str(tot_readings)+
               " readings over the 90 day time period from " + str(start_date) + " to " + str(end_date) +
               '. This averages a reading every ' +str(avg_time_per_reading) + ' minute.')

#write a1c 
pdf.ln(5)
pdf.multi_cell(w=0, h=5, txt= 'During this time period, the average A1c % was:' )
pdf.ln(5)
pdf.set_font('Arial','B', 20)
pdf.set_text_color(220, 50, 50)
pdf.cell(40, 10, border=0, ln = 0)

pdf.cell(120, 10, str(a1c_mean_pc) + "%", ln =0, align='C', border=0)

pdf.ln(10)
pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'The average HbA1c was: ' )
pdf.ln(5)
pdf.set_font('Arial','B', 20)
pdf.set_text_color(220, 50, 50)
pdf.cell(40, 10, border=0, ln = 0)
pdf.cell(120, 10, str(hba1c_mean_pc) + " mmol/mol", ln =0, align='C', border=0)

## 90-day figure 
pdf.ln(30)
pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'The below figure is a representation of the 90 days recorded through the XDrip4 app. ' +
               'The orange markers represent average glucose readings for each hour of a day. These markers are semi transparent '+
                'meaning that where the color is darker represents clusters of stable glucose readings where hourly averages were similar. '+
                 'The green markers represent the average daily glucose for any given day. Red and Blue lines represent high and low markers respectivly.' )
pdf.ln(20)

## Image
pdf.image('INSERT FILE PATH', w = 190, h=65)
pdf.ln(30)

pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'In the image below we use the data to create an "Average Week" for the 90 day period. ' +
               'Orange markers represent average glucose readings for each day of the 12 week period. ' +
               'Green markers represent the daily average for the sum of the readings for each day of the week.')
pdf.ln(10)
## Image
pdf.image('INSERT FILE PATH', w = 125, h=85)
## Line breaks
pdf.ln(20)


pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'Doing a similar thing but we use the data to create an "Average Day" for the 90 day period. ' +
               'This time the orange markers represent average glucose readings for each minute of a given hour. ' +
               'Green markers represent the hourly average in a day')
pdf.ln(10)
## Image
pdf.image('INSERT FILE PATH', w = 170, h=85)
## Line breaks
pdf.ln(20)


pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'If we group the glucose readings into reading that are in target, low and high; ' +
               'it is then possible to count the frequency of those events across the 90 day period of readings '+
               '(total number '+ str(tot_readings) +'). We can see the Geraldine was in target ' + str(target_pc) +
               '%  of the time, she was high ' +str(high_pc) + '% of the time and was low ' +
               str(low_pc)+ '% of the time.')
pdf.ln(10)
## Image
pdf.image('INSERT FILE PATH', w = 175, h=175)
## Line breaks
pdf.ln(20)


pdf.set_font('Arial','', 12)
pdf.set_text_color(0, 0, 0)
pdf.multi_cell(w=0, h=5, txt= 'Finally the figure below show the frequency of readings in target, low and high for each hour of the day over the 90 day period')
pdf.ln(10)
## Image
pdf.image('INSERT FILE PATH', w = 190, h=250)
## Line breaks
pdf.ln(20)




# 3. Output the PDF file
pdf.output('Glucoe report ' +str(start_date) + ' to ' +str(end_date)+'.pdf', 'F')


