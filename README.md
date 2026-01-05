# Stage 2 Market Dashboard

Stage 2 Market Dashboard is an interactive Dash web app for visualizing daily equity scans and sector rotation, built on top of pre-generated CSV screen outputs.[1]

## Features

- Cleans raw scan files (percentage moves, volumes, relative volume) from the `data/` folder and merges them into a single time-series dataset.[1]
- Computes a simple momentum score using 1‑day price change and relative volume to rank stocks each day.[1]
- Sector rotation analysis view with a time-series chart of stock counts by sector based on selected dates.[1]
- Momentum map scatter plot of latest scan (price change vs relative volume, bubble size by volume, coloured by sector).[1]
- Top momentum table listing the leading symbols, sectors, and key metrics for the latest scan date.[1]

## Tech Stack

- Python, pandas  
- Plotly Express / Graph Objects  
- Dash & dash_bootstrap_components (FLATLY theme)[1]

## How to Run

1. Place your scan CSV files in `data/` named like `Stage 2_YYYY-MM-DD.csv`.[1]
2. Install dependencies:

   ```bash
   pip install pandas plotly dash dash-bootstrap-components
   ```

3. Run the app:

   ```bash
   python "Stage-2-Market-Dashboard.py"
   ```

4. Open the local URL printed in the terminal (typically `http://127.0.0.1:8050`) in a browser.[1]

[1](https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/attachments/66411444/693160bd-1b99-4bf7-ab23-e75ccfbd602e/Stage-2-Market-Dashboard.py)
