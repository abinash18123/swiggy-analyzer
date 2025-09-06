"""
Interactive dashboard for Swiggy order analysis
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html
import dash_bootstrap_components as dbc

# Load and process data
df = pd.read_csv('../swiggy_orders.csv')
df['order_time'] = pd.to_datetime(df['order_time'])
df['delivery_time'] = pd.to_datetime(df['delivery_time'])
df['order_month'] = df['order_time'].dt.strftime('%Y-%m')
df['order_hour'] = df['order_time'].dt.hour
df['order_day'] = df['order_time'].dt.day_name()

# Initialize the Dash app
app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])

def create_monthly_trend():
    """Create monthly spending and order trend visualization"""
    monthly_data = df.groupby('order_month').agg({
        'total_amount': 'sum',
        'restaurant_name': 'count',
        'discount_amount': 'sum'
    }).reset_index()
    monthly_data.columns = ['month', 'total_spent', 'order_count', 'total_discount']
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bar chart for spending
    fig.add_trace(
        go.Bar(
            x=monthly_data['month'],
            y=monthly_data['total_spent'],
            name='Total Spent (₹)',
            marker_color='#FF6B6B',
            hovertemplate="Month: %{x}<br>Total Spent: ₹%{y:,.0f}<extra></extra>"
        ),
        secondary_y=False
    )
    
    # Add line for order count
    fig.add_trace(
        go.Scatter(
            x=monthly_data['month'],
            y=monthly_data['order_count'],
            name='Number of Orders',
            line=dict(color='#4ECDC4', width=3),
            hovertemplate="Month: %{x}<br>Orders: %{y}<extra></extra>"
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        title='Monthly Spending and Order Trends',
        xaxis_title='Month',
        yaxis_title='Amount (₹)',
        yaxis2_title='Number of Orders',
        hovermode='x unified',
        showlegend=True,
        template='plotly_white'
    )
    
    return fig

def create_restaurant_analysis():
    """Create restaurant analysis visualization"""
    restaurant_data = df.groupby('restaurant_name').agg({
        'total_amount': ['sum', 'count']
    }).reset_index()
    restaurant_data.columns = ['restaurant_name', 'total_spent', 'order_count']
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Top Restaurants by Spending', 'Top Restaurants by Orders'),
        specs=[[{"type": "pie"}, {"type": "pie"}]]
    )
    
    # Top 10 by spending
    top_spend = restaurant_data.nlargest(10, 'total_spent')
    fig.add_trace(
        go.Pie(
            labels=top_spend['restaurant_name'],
            values=top_spend['total_spent'],
            name='By Spending',
            hole=0.4,
            hovertemplate="Restaurant: %{label}<br>Total Spent: ₹%{value:,.0f}<extra></extra>"
        ),
        row=1, col=1
    )
    
    # Top 10 by orders
    top_orders = restaurant_data.nlargest(10, 'order_count')
    fig.add_trace(
        go.Pie(
            labels=top_orders['restaurant_name'],
            values=top_orders['order_count'],
            name='By Orders',
            hole=0.4,
            hovertemplate="Restaurant: %{label}<br>Orders: %{value}<extra></extra>"
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title='Restaurant Analysis',
        showlegend=False,
        template='plotly_white'
    )
    
    return fig

def create_time_analysis():
    """Create time pattern analysis visualization"""
    hourly_data = df['order_hour'].value_counts().sort_index()
    
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=hourly_data.index,
            y=hourly_data.values,
            marker_color='#45B7D1',
            hovertemplate="Hour: %{x}:00<br>Orders: %{y}<extra></extra>"
        )
    )
    
    fig.update_layout(
        title='Order Distribution by Hour of Day',
        xaxis_title='Hour of Day',
        yaxis_title='Number of Orders',
        template='plotly_white',
        xaxis=dict(
            tickmode='array',
            ticktext=[f'{i:02d}:00' for i in range(24)],
            tickvals=list(range(24))
        )
    )
    
    return fig

def create_delivery_time_analysis():
    """Create delivery time analysis visualization"""
    fig = go.Figure()
    fig.add_trace(
        go.Box(
            y=df['delivery_duration_mins'],
            name='Delivery Time',
            marker_color='#96CEB4',
            hovertemplate="Delivery Time: %{y} minutes<extra></extra>"
        )
    )
    
    fig.update_layout(
        title='Delivery Time Distribution (in minutes)',
        yaxis_title='Minutes',
        template='plotly_white',
        showlegend=False
    )
    
    return fig

def create_summary_cards():
    """Create summary statistics cards"""
    total_orders = len(df)
    total_spent = df['total_amount'].sum()
    avg_order = total_spent / total_orders
    total_saved = df['discount_amount'].abs().sum()
    
    cards = [
        dbc.Card(
            dbc.CardBody([
                html.H4(f"₹{total_spent:,.2f}", className="card-title text-primary"),
                html.P("Total Amount Spent", className="card-text"),
            ]),
            className="mb-4"
        ),
        dbc.Card(
            dbc.CardBody([
                html.H4(str(total_orders), className="card-title text-success"),
                html.P("Total Orders", className="card-text"),
            ]),
            className="mb-4"
        ),
        dbc.Card(
            dbc.CardBody([
                html.H4(f"₹{avg_order:,.2f}", className="card-title text-info"),
                html.P("Average Order Value", className="card-text"),
            ]),
            className="mb-4"
        ),
        dbc.Card(
            dbc.CardBody([
                html.H4(f"₹{total_saved:,.2f}", className="card-title text-warning"),
                html.P("Total Amount Saved", className="card-text"),
            ]),
            className="mb-4"
        ),
    ]
    return dbc.Row([dbc.Col(card, width=3) for card in cards])

# App layout
app.layout = dbc.Container([
    html.H1("Swiggy Order Analysis Dashboard", className="text-center my-4"),
    create_summary_cards(),
    dbc.Row([dbc.Col([dcc.Graph(figure=create_monthly_trend())], width=12)], className="mb-4"),
    dbc.Row([dbc.Col([dcc.Graph(figure=create_restaurant_analysis())], width=12)], className="mb-4"),
    dbc.Row([dbc.Col([dcc.Graph(figure=create_time_analysis())], width=12)], className="mb-4"),
    dbc.Row([dbc.Col([dcc.Graph(figure=create_delivery_time_analysis())], width=12)], className="mb-4"),
], fluid=True)

if __name__ == '__main__':
    print("Starting Swiggy Analysis Dashboard...")
    print("Open http://localhost:8050 in your browser")
    app.run(debug=True, port=8050)
