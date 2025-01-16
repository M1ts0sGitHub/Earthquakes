import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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
    # Remove last (unvalid) row
    df = df.iloc[:-1]
    
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

def get_color(date, min_date, max_date):
    """
    Returns a color between blue (oldest) and red (newest) based on the date
    """
    # Convert dates to timestamps for calculation
    date_ts = pd.Timestamp(date).timestamp()
    min_ts = pd.Timestamp(min_date).timestamp()
    max_ts = pd.Timestamp(max_date).timestamp()
    
    # Calculate normalized position between 0 and 1
    if max_ts == min_ts:
        position = 1
    else:
        position = (date_ts - min_ts) / (max_ts - min_ts)
    
    # Ensure position is within the range [0, 1]
    position = max(0, min(1, position))
    
    # Create RGB values
    r = int(255 * position)
    b = int(255 * (1 - position))
    
    # Convert to hex color
    return f'#{r:02x}00{b:02x}'

def create_color_scale(min_date, max_date):
    fig, ax = plt.subplots(figsize=(8, 1))
    
    # Create gradient array
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack((gradient, gradient))
    
    # Create colors array
    colors = []
    for i in np.linspace(0, 1, 256):
        r = int(255 * i)
        b = int(255 * (1 - i))
        colors.append((r/255, 0, b/255))
    
    # Plot gradient
    ax.imshow(gradient, aspect='auto', cmap=mcolors.ListedColormap(colors))
    
    # Remove axes
    ax.set_xticks([0, 255])
    ax.set_xticklabels([min_date.strftime('%Y-%m-%d %H:%M'), 
                        max_date.strftime('%Y-%m-%d %H:%M')])
    ax.set_yticks([])
    
    # Add title
    ax.set_title('Earthquake Timeline', pad=10)
    
    # Adjust layout
    plt.tight_layout()
    
    return fig


#####  Building Site  #####

# Set page config
st.set_page_config(
    page_title="Greek Earthquakes Visualization",
    page_icon="🌍",
    layout="wide"
)

# Add custom CSS to control max width
st.markdown(
    """
    <style>
        .block-container {
            max-width: 900px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Load the data
df = load_earthquake_data()

# Title and description
st.title("🌍 Earthquakes in Greece")

# Sidebar filters
st.sidebar.header("Filters")

st.sidebar.markdown("---")

# Date range filter
min_date = df['Datetime'].min().date()
max_date = df['Datetime'].max().date()
selected_date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

st.sidebar.markdown("---")

# Magnitude filter
magnitude_range = st.sidebar.slider(
    "Magnitude Range",
    min_value=float(df['Mag'].min()),
    max_value=float(df['Mag'].max()),
    value=(0.0, float(df['Mag'].max())),
    step=0.1
)

st.sidebar.markdown("---")
st.sidebar.header("About")
st.sidebar.markdown("This Streamlit app provides an interactive visualization of recent earthquakes in Greece. It fetches real-time earthquake data from the National and Kapodistrian University of Athens Seismology Laboratory and displays it on a map. Users can filter the data by date range and magnitude to focus on specific events. The app also provides key statistics, such as the total number of earthquakes, average magnitude, and the strongest earthquake within the selected filters. Additionally, it includes a color scale to represent the timeline of earthquakes, making it easy to identify recent and older events. The most recent earthquake is highlighted with a green marker to make it easily identifiable. The data table at the bottom allows users to explore detailed information about each earthquake.")



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

# Display statistics
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        f"""
        <div style="text-align: center;">
            <p>Total Earthquakes</p>
            <h3>{len(filtered_df)}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f"""
        <div style="text-align: center;">
            <p>Average Magnitude</p>
            <h3>{filtered_df['Mag'].mean():.2f}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
with col3:
    st.markdown(
        f"""
        <div style="text-align: center;">
            <p>Strongest Earthquake</p>
            <h3>{filtered_df['Mag'].max():.2f}</h3>
        </div>
        """,
        unsafe_allow_html=True
    )


# Create the map
m = folium.Map(location=[38.2, 23.7], zoom_start=7, tiles='CartoDB positron')

# Add all earthquake points except the most recent one
for idx, row in filtered_df.iterrows():
    if row['Datetime'] != filtered_df['Datetime'].max():
        # Calculate color based on recency (more recent = darker)
        color = get_color(row['Datetime'], filtered_df['Datetime'].min(), filtered_df['Datetime'].max())

        # Calculate radius based on magnitude
        radius = row['Mag'] * 2.8 + 1.4
        
        # Create popup content
        popup_content = f"""
        <b>Date:</b> {row['Datetime'].strftime('%Y-%m-%d %H:%M')}<br>
        <b>Magnitude:</b> {row['Mag']:.1f}<br>
        <b>Depth:</b> {row['Dep']:.1f} km
        """
        
        # Add circle marker
        folium.CircleMarker(
            location=[row['Lat'], row['Long']],
            radius=radius,
            popup=folium.Popup(popup_content, max_width=400),
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            weight=0
        ).add_to(m)

# Add the most recent earthquake marker
most_recent = filtered_df.loc[filtered_df['Datetime'].idxmax()]
radius = most_recent['Mag'] * 2.8 + 1.4
popup_content = f"""
<b>Date:</b> {most_recent['Datetime'].strftime('%Y-%m-%d %H:%M')}<br>
<b>Magnitude:</b> {most_recent['Mag']:.1f}<br>
<b>Depth:</b> {most_recent['Dep']:.1f} km
"""

folium.CircleMarker(
    location=[most_recent['Lat'], most_recent['Long']],
    radius=radius,
    popup=folium.Popup(popup_content, max_width=400),
    fill=True,
    color='yellow',  # Outline color
    fill_color='green',
    fill_opacity=1,
    weight=1
).add_to(m)

# Display the map
st_folium(m, width=800, height=900)

# Create and display color scale
if not filtered_df.empty:
    color_scale_fig = create_color_scale(filtered_df['Datetime'].min(), 
                                       filtered_df['Datetime'].max())
    st.pyplot(color_scale_fig)

# Add a space
st.markdown("---")

# Display data table
st.subheader("Data")


# Display dataframe with custom index starting from 1
st.dataframe(
    filtered_df.sort_values('Datetime', ascending=False)
    [['Datetime', 'Lat', 'Long', 'Mag', 'Dep']]
    .reset_index(drop=True)  # Reset index
    .set_index((np.arange(len(filtered_df)) + 1))  # Set index starting from 1
    .style.format({
        'Datetime': lambda x: x.strftime('%Y/%m/%d %H:%M'),
        'Lat': '{:.4f}',
        'Long': '{:.4f}',
        'Mag': '{:.1f}',
        'Dep': '{:.1f}'
    }),
    height=385  # Set height to 500px
)

st.markdown("")
url = 'http://www.geophysics.geol.uoa.gr/stations/maps/recent_gr.html'
st.markdown(
    f"""
    <div style="text-align: center; font-size: 12px; margin-top: 20px;">
        Data source: <a href="{url}" target="_blank">National and Kapodistrian University of Athens Seismology Laboratory</a>
    </div>
    """,
    unsafe_allow_html=True
)