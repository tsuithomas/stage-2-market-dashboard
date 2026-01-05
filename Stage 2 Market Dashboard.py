import os
import glob
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import datetime
import webbrowser
from threading import Timer

# --- CONFIGURATION ---
DATA_DIR = "data"
FILE_PATTERN = "Stage 2_*.csv" 

# --- 1. DATA CLEANING HELPERS ---
def clean_percentage(x):
    """Converts '5.4%' to float 5.4"""
    if isinstance(x, str):
        clean_str = x.replace('%', '').replace(',', '')
        try:
            return float(clean_str)
        except ValueError:
            return 0.0
    return x

def clean_volume(x):
    """Converts '1.5M' to 1500000, '500K' to 500000"""
    if isinstance(x, str):
        x = x.upper().replace(',', '')
        if 'K' in x:
            return float(x.replace('K', '')) * 1000
        elif 'M' in x:
            return float(x.replace('M', '')) * 1000000
        elif 'B' in x:
            return float(x.replace('B', '')) * 1000000000
        try:
            return float(x)
        except ValueError:
            return 0.0
    return x

# --- 2. DATA INGESTION ---
def load_and_process_data():
    all_files = glob.glob(os.path.join(DATA_DIR, FILE_PATTERN))
    
    if not all_files:
        print("No files found. Please check your data directory.")
        return pd.DataFrame()

    df_list = []
    for filename in all_files:
        try:
            basename = os.path.basename(filename)
            date_str = basename.replace("Stage 2_", "").replace(".csv", "")
            scan_date = pd.to_datetime(date_str).date()
            
            df = pd.read_csv(filename)
            df['Date'] = pd.to_datetime(scan_date)
            # Create a string version of date for the Category Axis (looks cleaner)
            df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            # --- CLEANING DATA TYPES ---
            if 'Price Change % 1 day' in df.columns:
                df['Price Change % 1 day'] = df['Price Change % 1 day'].apply(clean_percentage)
            
            if 'Volume 1 day' in df.columns:
                df['Volume 1 day'] = df['Volume 1 day'].apply(clean_volume)
                
            if 'Relative Volume 1 day' in df.columns:
                 df['Relative Volume 1 day'] = pd.to_numeric(df['Relative Volume 1 day'], errors='coerce').fillna(0)
            
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    if not df_list:
        return pd.DataFrame()

    full_df = pd.concat(df_list, ignore_index=True)
    full_df = full_df.sort_values('Date')
    return full_df

df = load_and_process_data()

# --- 3. METRICS & SCORECARD LOGIC ---
top_sector_name = "N/A"
top_sector_count = 0
fastest_growing_sector = "N/A"
growth_count = 0
growth_str = "0"

latest_df = pd.DataFrame()
latest_date = datetime.date.today()

if not df.empty:
    latest_date = df['Date'].max()
    latest_df = df[df['Date'] == latest_date].copy()
    
    # Calculate Momentum Score
    latest_df['Momentum Score'] = latest_df['Price Change % 1 day'] * latest_df['Relative Volume 1 day']
    latest_df = latest_df.sort_values('Momentum Score', ascending=False)

    # Scorecard Data
    sector_counts = latest_df['Sector'].value_counts()
    if not sector_counts.empty:
        top_sector_name = sector_counts.idxmax()
        top_sector_count = sector_counts.max()

    unique_dates = df['Date'].unique()
    if len(unique_dates) > 1:
        prev_date = unique_dates[-2]
        prev_df = df[df['Date'] == prev_date]
        curr_counts = latest_df['Sector'].value_counts()
        prev_counts = prev_df['Sector'].value_counts()
        delta = curr_counts.sub(prev_counts, fill_value=0)
        fastest_growing_sector = delta.idxmax()
        growth_count = int(delta.max())
        growth_str = f"+{growth_count}" if growth_count > 0 else str(growth_count)

# --- 4. STYLING ---
card_style = {
    'boxShadow': '0 4px 8px 0 rgba(0,0,0,0.2)', 'transition': '0.3s',
    'width': '20%', 'borderRadius': '5px', 'padding': '20px',
    'backgroundColor': '#f9f9f9', 'textAlign': 'center',
    'display': 'inline-block', 'margin': '10px'
}

# --- 5. DASH LAYOUT ---
app = Dash(__name__)

app.layout = html.Div([
    html.H1("Stage 2 Market Dashboard", style={'textAlign': 'center', 'fontFamily': 'sans-serif'}),
    
    # SCORECARDS
    html.Div([
        html.Div([html.H4("Total Scanned"), html.H2(f"{len(latest_df)}", style={'color': '#2c3e50'})], style=card_style),
        html.Div([html.H4("Largest Sector"), html.H2(top_sector_name, style={'color': '#2980b9'}), html.P(f"({top_sector_count} stocks)")], style=card_style),
        html.Div([html.H4("Top Sector Inflow"), html.H2(fastest_growing_sector, style={'color': '#27ae60'}), html.P(f"Change: {growth_str}")], style=card_style),
    ], style={'textAlign': 'center', 'marginBottom': '30px'}),

    # SECTOR TRENDS
    html.Div([
        html.H3("Sector Rotation Analysis"),
        html.Label("Select Sectors:", style={'fontWeight': 'bold'}),
        dcc.Dropdown(
            id='sector-dropdown',
            options=[{'label': s, 'value': s} for s in df['Sector'].dropna().unique()],
            multi=True,
            value=sector_counts.index[:5].tolist() if not df.empty else [],
        ),
        dcc.Graph(id='sector-trend-graph'),
    ], style={'padding': '20px', 'borderTop': '1px solid #ddd', 'borderBottom': '1px solid #ddd'}),

    # MOMENTUM SCANNER
    html.Div([
        html.H3(f"Momentum Scanner (Data: {latest_date})"),
        html.Div([
            html.Div([dcc.Graph(id='momentum-scatter')], style={'width': '60%', 'display': 'inline-block'}),
            html.Div([
                html.H4("Top Momentum Plays"),
                dash_table.DataTable(
                    id='top-stocks-table',
                    columns=[{"name": i, "id": i} for i in ['Symbol', 'Sector', 'Price Change % 1 day', 'Relative Volume 1 day']],
                    data=latest_df.head(10).to_dict('records'),
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px', 'fontFamily': 'sans-serif'},
                    style_header={'backgroundColor': '#ecf0f1', 'fontWeight': 'bold'},
                    page_size=10
                )
            ], style={'width': '38%', 'display': 'inline-block', 'verticalAlign': 'top', 'paddingLeft': '2%'})
        ])
    ], style={'padding': '20px'})
])

# --- 6. CALLBACKS ---

@app.callback(
    Output('sector-trend-graph', 'figure'),
    Input('sector-dropdown', 'value')
)
def update_sector_graph(selected_sectors):
    if df.empty or not selected_sectors:
        return go.Figure()

    filtered_df = df[df['Sector'].isin(selected_sectors)]
    # Use 'DateStr' here so Plotly sees it as text categories
    sector_counts_hist = filtered_df.groupby(['DateStr', 'Sector']).size().reset_index(name='Stock Count')
    
    fig = px.line(
        sector_counts_hist, 
        x='DateStr', # Use the string version
        y='Stock Count', 
        color='Sector', 
        markers=True,
        title="Breadth: Number of Stocks Qualifying for Stage 2"
    )
    
    # --- FIX 1: FORCE EVEN INTERVALS ---
    # type='category' ensures Plotly treats every date as an equal step, ignoring gaps
    fig.update_xaxes(type='category', tickangle=-45) 
    
    fig.update_layout(
        hovermode="x unified",
        plot_bgcolor='white',
        paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
    )
    return fig

@app.callback(
    Output('momentum-scatter', 'figure'),
    Input('sector-dropdown', 'value')
)
def update_momentum_scatter(_):
    if latest_df.empty:
        return go.Figure()

    # --- FIX 2: SAFE COPY & TYPE CHECKING ---
    plot_df = latest_df.copy().reset_index(drop=True)
    
    # Ensure numeric columns
    cols_to_check = ['Relative Volume 1 day', 'Price Change % 1 day', 'Volume 1 day']
    for col in cols_to_check:
        plot_df[col] = pd.to_numeric(plot_df[col], errors='coerce').fillna(0)

    try:
        fig = px.scatter(
            plot_df,
            x='Relative Volume 1 day',
            y='Price Change % 1 day',
            hover_data=['Symbol', 'Sector', 'Market capitalization'],
            color='Sector',
            size='Volume 1 day',
            title="Momentum Map: Rel Vol vs Price Change"
            # REMOVED: template="plotly_white" (Fixes crash)
        )
        
        # Manually apply clean white styling
        fig.update_layout(
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(showgrid=True, gridcolor='#f0f0f0'),
            yaxis=dict(showgrid=True, gridcolor='#f0f0f0')
        )

        fig.add_vline(x=1.5, line_dash="dash", line_color="green", annotation_text="High Vol")
        fig.add_hline(y=0, line_dash="solid", line_color="black")
        return fig
    except Exception as e:
        print(f"Graph Error: {e}")
        return go.Figure()

# --- 7. RUN ---
def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050/")

if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        Timer(1, open_browser).start()
    app.run(debug=True)