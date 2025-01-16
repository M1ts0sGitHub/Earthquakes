import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium

# Set page config
st.set_page_config(
    page_title="Greek Earthquakes Visualization",
    page_icon="🌍",
    layout="wide"
)

# Title and description
st.title("🌍 Recent Earthquakes in Greece")
st.markdown("Data source: National and Kapodistrian University of Athens Seismology Laboratory")

@st.cache_data(ttl=300)  # Cache the data for 5 minutes
def load_earthquake_data():
    # Getting Data
    url = "http://www.geophysics.geol.uoa.gr/stations/gmaps3/event_output2j.php?type=cat"
    response = requests.get(url)
    
    df_list = []
    # Split the response into columns and rows
    line_split = response.text.split('\n')
    for line in line_split:
        word_split = line.split()
        df_list.append(word_split)
    
    # Assign the data and column_names to our dataframe
    df = pd.DataFrame(df_list[1:], columns=df_list[0])
    # Keep the last 500 earthquakes
    df = df.iloc[:500]
    
    # Convert Lat & Long from text to float
    df['Lat'] = df['Lat'].str.replace(',', '.').astype(float)
    df['Long'] = df['Long'].str.replace(',', '.').astype(float)
    df['Dep'] = df['Dep'].str.replace(',', '.').astype(float)
    df['Mag'] = df['Mag'].str.replace(',', '.').astype(float)
    
    # Create one datetime column
    df['Datetime'] = pd.to_datetime(df['Year'].astype(str) + '-' + 
                                  df['Mo'].astype(str) + '-' + 
                                  df['Dy'].astype(str) + ' ' + 
                                  df['Hr'].astype(str) + ':' + 
                                  df['Mn'].astype(str))
    # From GMT --> Greece Time Zone
    df['Datetime'] = df['Datetime'] + pd.Timedelta(hours=2)
    
    # Clean up the dataframe
    cols_to_drop = ['RMS','dx','dy','dz','Np','Na','Gap','Year', 'Mo', 'Dy', 'Hr', 'Mn', 'Sec']
    df.drop(cols_to_drop, axis=1, inplace=True)
    
    return df

# Load the data
df = load_earthquake_data()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
min_date = df['Datetime'].min().date()
max_date = df['Datetime'].max().date()
selected_date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(max_date - timedelta(days=7), max_date),
    min_value=min_date,
    max_value=max_date
)

# Magnitude filter
magnitude_range = st.sidebar.slider(
    "Magnitude Range",
    min_value=float(df['Mag'].min()),
    max_value=float(df['Mag'].max()),
    value=(0.0, float(df['Mag'].max())),
    step=0.1
)

# Filter the data
if len(selected_date_range) == 2:
    start_date, end_date = selected_date_range
    mask = (
        (df['Datetime'].dt.date >= start_date) & 
        (df['Datetime'].dt.date <= end_date) &
        (df['Mag'] >= magnitude_range[0]) &
        (df['Mag'] <= magnitude_range[1])
    )
    filtered_df = df[mask]
else:
    filtered_df = df

# Create the map
m = folium.Map(location=[38.2, 23.7], zoom_start=7)

# Add earthquake points
for idx, row in filtered_df.iterrows():
    # Calculate color based on recency (more recent = darker)
    days_old = (max_date - row['Datetime'].date()).days
    opacity = max(0.3, 1 - (days_old / 30))
    
    # Calculate radius based on magnitude
    radius = row['Mag'] * 5000
    
    # Create popup content
    popup_content = f"""
    <b>Date:</b> {row['Datetime'].strftime('%Y-%m-%d %H:%M')}<br>
    <b>Magnitude:</b> {row['Mag']:.1f}<br>
    <b>Depth:</b> {row['Dep']:.1f} km
    """
    
    # Add circle marker
    folium.CircleMarker(
        location=[row['Lat'], row['Long']],
        radius=5,
        popup=popup_content,
        color='red',
        fill=True,
        fill_color='red',
        fill_opacity=opacity,
        weight=1
    ).add_to(m)

# Display the map
st_folium(m, width=800, height=600)

# Display statistics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Earthquakes", len(filtered_df))
with col2:
    st.metric("Average Magnitude", f"{filtered_df['Mag'].mean():.2f}")
with col3:
    st.metric("Strongest Earthquake", f"{filtered_df['Mag'].max():.2f}")

# Display data table
st.subheader("Earthquake Data")
st.dataframe(
    filtered_df.sort_values('Datetime', ascending=False)
    [['Datetime', 'Lat', 'Long', 'Mag', 'Dep']]
    .style.format({
        'Lat': '{:.4f}',
        'Long': '{:.4f}',
        'Mag': '{:.1f}',
        'Dep': '{:.1f}'
    })
)
