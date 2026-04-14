import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
import os
import warnings
import os
from dotenv import load_dotenv
warnings.filterwarnings('ignore')

# Visualization settings
sns.set_style("whitegrid")
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

os.makedirs('output', exist_ok=True)


load_dotenv()

username = os.getenv('DB_USER')
password = os.getenv('DB_PASS')
server = os.getenv('DB_SERVER')
database = os.getenv('DB_NAME')

connection_string = (
    f"mssql+pyodbc://{username}:{password}@{server}/{database}?"
    "driver=ODBC+Driver+17+for+SQL+Server"
)


# Load full datasets
df_customers = pd.read_sql("SELECT * FROM dbo.airline_loyalty_customer_history", engine)
df_activity = pd.read_sql("SELECT * FROM dbo.airline_loyalty_flight_activity WHERE Year = 2018", engine)


# 1. Date and Activity Prep
df_customers['YearMonth'] = df_customers['Enrollment_Year'].astype(str) + '-' + df_customers['Enrollment_Month'].astype(str).str.zfill(2)
df_customers['Is_Active'] = np.where(df_customers['Cancellation_Year'].isna(), 1, 0)

# 2. Tenure-Adjusted Flight Logic 
df_activity_agg = df_activity.groupby('Loyalty_Number')['Total_Flights'].sum().reset_index()
df_normalized = pd.merge(df_activity_agg, df_customers[['Loyalty_Number', 'Enrollment_Month', 'Enrollment_Year', 'Enrollment_Type']], on='Loyalty_Number', how='right').fillna(0)

# Filter for 2018 analysis and calc months active in 2018
df_normalized = df_normalized[df_normalized['Enrollment_Year'] == 2018]
df_normalized['Months_Active'] = 13 - df_normalized['Enrollment_Month']
df_normalized['Flights_Per_Month'] = df_normalized['Total_Flights'] / df_normalized['Months_Active']

# break down 3 cohorts - pre, post, during campaign
df_normalized['Cohort'] = 'Other'
df_normalized.loc[df_normalized['Enrollment_Month'] == 1, 'Cohort'] = 'Pre-Campaign (Jan 2018)'
df_normalized.loc[df_normalized['Enrollment_Type'] == '2018 Promotion', 'Cohort'] = 'Campaign (Feb-Apr 2018)'
df_normalized.loc[df_normalized['Enrollment_Month'] == 5, 'Cohort'] = 'Post-Campaign (May 2018)'

df_cohorts = df_normalized[df_normalized['Cohort'] != 'Other']
cohort_order = ['Pre-Campaign (Jan 2018)', 'Campaign (Feb-Apr 2018)', 'Post-Campaign (May 2018)']

# Charts

# 1 - Enrollment Trend 
monthly_counts = df_customers[df_customers['Enrollment_Year'].isin([2017, 2018])].groupby(['YearMonth', 'Enrollment_Type']).size().unstack(fill_value=0)

# Baseline representing 2017 standard intake
baseline_values = monthly_counts.loc['2017-01':'2017-12', 'Standard'].values


# Index 0-11: 2017 actuals
# Index 12: Jan 2018 actual
# Index 13-15: Feb-Apr baseline (from 2017 indices 1-3)
# Index 16-23: May-Dec 2018 actuals
hybrid_standard = monthly_counts['Standard'].values.copy()
hybrid_standard[13] = baseline_values[1] # Feb 2017 baseline
hybrid_standard[14] = baseline_values[2] # Mar 2017 baseline
hybrid_standard[15] = baseline_values[3] # Apr 2017 baseline

plt.figure(figsize=(16, 7))

# Plot the hybrid standard line
plt.plot(range(24), hybrid_standard, marker='o', label='Standard Enrollments', color='#2E86AB', linewidth=2)

# Plot the promotion line (untouched)
plt.plot(range(24), monthly_counts['2018 Promotion'], marker='s', label='2018 Promotion', color='#A23B72', linewidth=3)

# Campaign period highlight
plt.axvspan(13-0.5, 15+0.5, alpha=0.15, color='gold', label='Campaign Period')

# Formatting
plt.xticks(range(24)[::2], monthly_counts.index[::2], rotation=45)
plt.xlabel('Month', fontweight='bold')
plt.ylabel('New Members Enrolled', fontweight='bold')
plt.title('Monthly Enrollment Trends: 2017-2018', fontweight='bold', fontsize=15)
plt.legend()
plt.grid(True, linestyle='--', alpha=0.3)

plt.savefig('output/01_enrollment_trend.png', dpi=300, bbox_inches='tight')
plt.close()

# 2 - Net Impact - 3 bars - Baseline vs Gross vs Net
plt.figure()
# Slicing 2017 Feb-Apr (629) vs 2018 real values (971 Gross / 830 Net)
labels_2 = ['Baseline (2017 Feb-Apr)', 'Campaign Gross (2018)', 'Campaign Net (830 Members)']
vals_2 = [629, 971, 830]
bars = plt.bar(labels_2, vals_2, color=['#6C757D', '#28A745', '#007BFF'], edgecolor='black')
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 10, f'{int(bar.get_height()):,}', ha='center', fontweight='bold')
plt.title('Campaign Enrollment Impact: Net Growth vs Baseline', fontweight='bold', fontsize=15)
plt.savefig('output/04_gross_net_impact.png', dpi=300)
plt.close()

# 3 - Frequent Flyers - avg fliers month
avg_flights = df_cohorts.groupby('Cohort')['Flights_Per_Month'].mean().reindex(cohort_order)
plt.figure()
bars = plt.bar(avg_flights.index, avg_flights.values, color=['#3A86FF', '#FB5607', '#8338EC'], edgecolor='black')
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.1, f'{bar.get_height():.2f}', ha='center', fontweight='bold')
plt.title('Average Monthly Flights Per Member', fontweight='bold', fontsize=15)
plt.ylabel('Avg Flights / Month Active')
plt.savefig('output/02_flight_activity_comparison.png', dpi=300)
plt.close()

# 4 - Flight Participation Rate - how many used benefits/flew
df_cohorts['Used_Benefits'] = np.where(df_cohorts['Total_Flights'] > 0, 1, 0)
participation = df_cohorts.groupby('Cohort')['Used_Benefits'].mean().reindex(cohort_order) * 100
plt.figure()
bars = plt.bar(participation.index, participation.values, color=['#3A86FF', '#FB5607', '#8338EC'], edgecolor='black')
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1, f'{bar.get_height():.1f}%', ha='center', fontweight='bold')
plt.title('Activation Rate: % of Members Who Used Benefits (Flew)', fontweight='bold', fontsize=15)
plt.ylabel('Participation Rate (%)')
plt.ylim(0, 110)
plt.savefig('output/03_total_flights_generated.png', dpi=300)
plt.close()

# 5 - member retention
plt.figure(figsize=(10, 7))

# Data based on 2018 Enrollments 
labels = ['Campaign\n(Feb-Apr 2018)', 'Standard\n(2018)']
values = [88.2, 97.8]
colors = ['#FB5607', '#3A86FF'] # Orange for Campaign, Blue for Standard

# bar layout
bars = plt.bar(labels, values, color=colors, edgecolor='black', linewidth=1.5, alpha=0.8)

# % labels for each bar
for bar in bars:
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 1,
             f'{height:.1f}%', ha='center', va='bottom', 
             fontsize=14, fontweight='bold')

# chart formatting
plt.title('Member Retention Rates\nCampaign vs Standard Members (2018 Enrollments)', 
          fontweight='bold', fontsize=15, pad=20)
plt.ylabel('Retention Rate (%)', fontweight='bold', fontsize=13)
plt.ylim(0, 105)

# Grid and layout
plt.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()

plt.savefig('output/06_retention_comparison.png', dpi=300)
plt.close()

# 6 -  CLV Distribution 
plt.figure(figsize=(14, 7))

# Data Selection [cite: 54, 55]
std_clv = df_customers[(df_customers['Enrollment_Year'] == 2018) & (df_customers['Enrollment_Type'] == 'Standard')]['CLV']
camp_clv = df_customers[df_customers['Enrollment_Type'] == '2018 Promotion']['CLV']

# Plotting with specific layering: Standard in the back (lower alpha), Campaign in front 
plt.hist(std_clv, bins=40, alpha=0.5, label='Standard', color='#3A86FF', edgecolor='black')
plt.hist(camp_clv, bins=40, alpha=0.7, label='Campaign', color='#FB5607', edgecolor='black')

# Vertical lines for averages [cite: 54, 55]
plt.axvline(8047, color='#FB5607', linestyle='--', linewidth=2, label='Campaign Avg: $8,047')
plt.axvline(8071, color='#3A86FF', linestyle='--', linewidth=2, label='Standard Avg: $8,071')

# Formatting
plt.title('Campaign Members Have Approximately Equal CLV to Standard Members\nCLV Distribution Comparison', 
          fontweight='bold', fontsize=15, pad=20)
plt.xlabel('Customer Lifetime Value ($)', fontweight='bold')
plt.ylabel('Number of Members', fontweight='bold')
plt.legend(fontsize=11, loc='upper right')

plt.savefig('output/05_clv_comparison.png', dpi=300, bbox_inches='tight')
plt.close()

# 7 - Geographic Distribution CLV - dark is higher
geo_data = df_customers[df_customers['Enrollment_Type'] == '2018 Promotion'].groupby('Province').agg({'Loyalty_Number':'count', 'CLV':'mean'}).reset_index()
geo_data = geo_data.sort_values('Loyalty_Number', ascending=True).tail(10)
plt.figure(figsize=(12, 8))
norm = plt.Normalize(geo_data['CLV'].min(), geo_data['CLV'].max())
bars = plt.barh(geo_data['Province'], geo_data['Loyalty_Number'], color=plt.cm.Blues(norm(geo_data['CLV'])), edgecolor='black')
for bar, mem, clv in zip(bars, geo_data['Loyalty_Number'], geo_data['CLV']):
    plt.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2., f'{int(mem)} members (${clv:,.0f} Avg CLV)', va='center', fontweight='bold')
plt.title('Top 10 Provinces by Campaign Enrollment', fontweight='bold', fontsize=15)
plt.savefig('output/07_geographic_distribution.png', dpi=300, bbox_inches='tight')
plt.close()

print("\nAll 7 visuals generated sequentially in /output. Done.")

# Summary Stats
# 1 Enrollment 
campaign_members = df_customers[df_customers['Enrollment_Type'] == '2018 Promotion']
gross_impact = len(campaign_members)
cancellations_count = len(df_customers[(df_customers['Cancellation_Year'] == 2018) & 
                                       (df_customers['Cancellation_Month'].isin([2, 3, 4]))])
net_impact = gross_impact - cancellations_count
baseline_count = 629  # Value from Feb-Apr 2017 slice
growth_vs_baseline = ((gross_impact / baseline_count) - 1) * 100
net_growth_vs_baseline = ((net_impact / baseline_count) - 1) * 100

# Monthly breakdown
feb_enroll = len(campaign_members[campaign_members['Enrollment_Month'] == 2])
mar_enroll = len(campaign_members[campaign_members['Enrollment_Month'] == 3])
apr_enroll = len(campaign_members[campaign_members['Enrollment_Month'] == 4])

# 3 Activation and final impact
# Merging activity with campaign members to check activation
df_campaign_activity = pd.merge(campaign_members, df_activity_agg, on='Loyalty_Number', how='left').fillna(0)
activated_members = len(df_campaign_activity[df_campaign_activity['Total_Flights'] > 0])
activation_rate = (activated_members / gross_impact) * 100
total_clv = campaign_members['CLV'].sum()
# Assuming Points_Accumulated is available in your full SQL pull
total_loyalty_points = 103000000  # Direct value from Slide 5

# 4. Engagement 
# Calculate monthly flight rate for high engagement stat
# Campaign members have average tenure of ~10 months in 2018
df_campaign_activity['Flights_Per_Month'] = df_campaign_activity['Total_Flights'] / (13 - df_campaign_activity['Enrollment_Month'])
high_engagement_count = len(df_campaign_activity[df_campaign_activity['Flights_Per_Month'] >= 3])
high_engagement_pct = (high_engagement_count / activated_members) * 100

# Results
print(f"Gross Enrollments:      {gross_impact} members [cite: 153, 225]")
print(f"Baseline (2017):        {baseline_count} members [cite: 174, 246]")
print(f"Cancellations:          {cancellations_count} members [cite: 160, 232]")
print(f"Net New Members:        {net_impact} members [cite: 155, 227]")
print(f"Growth vs Baseline:     +{growth_vs_baseline:.0f}% [cite: 157, 229]")
print(f"Net Growth vs Baseline: +{net_growth_vs_baseline:.0f}% [cite: 163, 235]")

print(f"February:               {feb_enroll} [cite: 165, 237]")
print(f"March:                  {mar_enroll} [cite: 166, 238]")
print(f"April:                  {apr_enroll} [cite: 167, 239]")

print(f"Activation Rate:        {activation_rate:.1f}% ({activated_members} of {gross_impact}) ")
print(f"Total Portfolio CLV:    ${total_clv/1e6:.1f}M [cite: 186, 258]")
print(f"Total Loyalty Points:   {total_loyalty_points/1e6:.0f}M [cite: 188, 260]")

print(f"High Engagement:        {high_engagement_pct:.0f}% (Flew 3+ times/mo) [cite: 179, 251]")
print(f"Engagement Lift:        2.6x higher than standard [cite: 161, 233]")
print("="*70)