import os
import glob
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc
import datetime
import webbrowser
from threading import Timer

# --- CONFIGURATION ---
DATA_DIR = "data"
FILE_PATTERN = "Stage 2_*.csv" 

# --- 1. DATA CLEANING ---
def clean_percentage(x):
    if isinstance(x, str):
        clean_str = x.replace('%', '').replace(',', '')
        try: return float(clean_str)
        except ValueError: return 0.0
    return x

def clean_volume(x):
    if isinstance(x, str):
        x = x.upper().replace(',', '')
        if 'K' in x: return float(x.replace('K', '')) * 1000
        elif 'M' in x: return float(x.replace('M', '')) * 1000000
        elif 'B' in x: return float(x.replace('B', '')) * 1000000000
        try: return float(x)
        except ValueError: return 0.0
    return x

def load_and_process_data():
    all_files = glob.glob(os.path.join(DATA_DIR, FILE_PATTERN))
    if not all_files: return pd.DataFrame()

    df_list = []
    for filename in all_files:
        try:
            basename = os.path.basename(filename)
            date_str = basename.replace("Stage 2_", "").replace(".csv", "")
            scan_date = pd.to_datetime(date_str).date()
            
            df = pd.read_csv(filename)
            df['Date'] = pd.to_datetime(scan_date)
            df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            if 'Price Change % 1 day' in df.columns:
                df['Price Change % 1 day'] = df['Price Change % 1 day'].apply(clean_percentage)
            if 'Volume 1 day' in df.columns:
                df['Volume 1 day'] = df['Volume 1 day'].apply(clean_volume)
            if 'Relative Volume 1 day' in df.columns:
                 df['Relative Volume 1 day'] = pd.to_numeric(df['Relative Volume 1 day'], errors='coerce').fillna(0)
            
            df_list.append(df)
        except Exception as e:
            print(f"Error reading {filename}: {e}")

    if not df_list: return pd.DataFrame()
    return pd.concat(df_list, ignore_index=True).sort_values('Date')

df = load_and_process_data()

# --- 2. METRICS ---
top_sector_name = "N/A"
top_sector_count = 0
fastest_growing_sector = "N/A"
growth_str = "0"
latest_df = pd.DataFrame()
latest_date = datetime.date.today()

if not df.empty:
    latest_date = df['Date'].max().date()
    latest_df = df[df['Date'] == pd.to_datetime(latest_date)].copy()
    
    latest_df['Momentum Score'] = latest_df['Price Change % 1 day'] * latest_df['Relative Volume 1 day']
    latest_df = latest_df.sort_values('Momentum Score', ascending=False)

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

# --- 3. DASH LAYOUT ---
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

app.layout = dbc.Container([
    
    # Header
    dbc.NavbarSimple(brand="Stage 2 Market Scanner", brand_href="#", color="primary", dark=True, className="mb-4"),

    # Top Cards
    dbc.Row([
        dbc.Col(dbc.Card([dbc.CardHeader("Total Scanned Stocks"), dbc.CardBody([html.H2(f"{len(latest_df)}", className="text-center text-primary")])], color="light", outline=True), width=12, lg=4, className="mb-3"),
        dbc.Col(dbc.Card([dbc.CardHeader("Largest Sector"), dbc.CardBody([html.H2(top_sector_name, className="text-center text-info"), html.P(f"Count: {top_sector_count}", className="text-center text-muted small")])], color="light", outline=True), width=12, lg=4, className="mb-3"),
        dbc.Col(dbc.Card([dbc.CardHeader("Top Inflow Sector"), dbc.CardBody([html.H2(fastest_growing_sector, className="text-center text-success"), html.P(f"Change: {growth_str}", className="text-center text-muted small")])], color="light", outline=True), width=12, lg=4, className="mb-3"),
    ], className="mb-4"),

    # Sector Trend
    dbc.Card([
        dbc.CardHeader("🔎 Sector Rotation Analysis"),
        dbc.CardBody([
            html.Label("Compare Sectors:", className="fw-bold"),
            dcc.Dropdown(id='sector-dropdown', options=[{'label': s, 'value': s} for s in df['Sector'].dropna().unique()], multi=True, value=sector_counts.index[:5].tolist() if not df.empty else [], className="mb-3"),
            dcc.Loading(dcc.Graph(id='sector-trend-graph'))
        ])
    ], className="mb-4 shadow-sm"),

    # Momentum Scanner (Responsive Split)
    dbc.Row([
        # LEFT: GRAPH
        # lg=8 means "Use 8 columns on large screens". width=12 means "Use full width on mobile"
        dbc.Col(dbc.Card([
            dbc.CardHeader(f"🚀 Momentum Map ({latest_date})"),
            dbc.CardBody([dcc.Graph(id='momentum-scatter', style={'height': '600px'})])
        ], className="shadow-sm mb-3"), width=12, lg=8), 

        # RIGHT: TABLE
        # lg=4 means "Use 4 columns on large screens". It will naturally drop below on mobile.
        dbc.Col(dbc.Card([
            dbc.CardHeader("🏆 Top Momentum List"),
            dbc.CardBody([
                dash_table.DataTable(
                    id='top-stocks-table',
                    columns=[{"name": "Sym", "id": "Symbol"}, {"name": "Sec", "id": "Sector"}, {"name": "% Chg", "id": "Price Change % 1 day"}, {"name": "R.Vol", "id": "Relative Volume 1 day"}],
                    data=latest_df.head(15).to_dict('records'),
                    style_table={'overflowX': 'auto'},
                    style_as_list_view=True,
                    style_cell={'fontSize': '12px', 'textAlign': 'left', 'padding': '5px'},
                    style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 248, 248)'}],
                    page_size=13
                )
            ])
        ], className="shadow-sm mb-3"), width=12, lg=4)
    ], className="mb-4"),

    html.Div([html.Hr(), html.P("Automated Market Analysis Tool", className="text-center text-muted")], className="mb-4")
], fluid=True)

# --- CALLBACKS ---
@app.callback(Output('sector-trend-graph', 'figure'), Input('sector-dropdown', 'value'))
def update_sector_graph(selected_sectors):
    if df.empty or not selected_sectors: return go.Figure()
    filtered_df = df[df['Sector'].isin(selected_sectors)]
    sector_counts_hist = filtered_df.groupby(['DateStr', 'Sector']).size().reset_index(name='Stock Count')
    fig = px.line(sector_counts_hist, x='DateStr', y='Stock Count', color='Sector', markers=True, template="simple_white")
    fig.update_xaxes(type='category', tickangle=-45)
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), hovermode="x unified", legend=dict(orientation="h", y=1.1))
    return fig

@app.callback(Output('momentum-scatter', 'figure'), Input('sector-dropdown', 'value'))
def update_momentum_scatter(_):
    if latest_df.empty: return go.Figure()
    plot_df = latest_df.copy().reset_index(drop=True)
    cols = ['Relative Volume 1 day', 'Price Change % 1 day', 'Volume 1 day']
    for c in cols: plot_df[c] = pd.to_numeric(plot_df[c], errors='coerce').fillna(0)

    try:
        fig = px.scatter(
            plot_df, x='Relative Volume 1 day', y='Price Change % 1 day',
            hover_data=['Symbol', 'Sector', 'Market capitalization'],
            color='Sector', size='Volume 1 day',
            template="simple_white"
        )
        
        # --- FIX 1: Add Clear Y=0 Line ---
        fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1.5, opacity=0.5)
        
        # --- FIX 2: Move Legend to Right Side ---
        # Moving legend to the right prevents it from covering the dots
        fig.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(
                orientation="v",  # Vertical
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02  # Places it just outside the graph to the right
            )
        )
        # Add visual reference for "High Vol"
        fig.add_vline(x=1.5, line_dash="dash", line_color="green")
        
        return fig
    except Exception: return go.Figure()

def open_browser(): webbrowser.open_new("http://127.0.0.1:8050/")
if __name__ == '__main__':
    if not os.environ.get("WERKZEUG_RUN_MAIN"): Timer(1, open_browser).start()
    app.run(debug=True)