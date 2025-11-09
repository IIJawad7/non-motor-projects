import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Configuration ---
st.set_page_config(
    layout="wide", 
    page_title="Transaction Summary Dashboard",
    page_icon="💰",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS for modern styling ---
st.markdown("""
<style>
/* Header styling */
.dashboard-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 15px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dashboard-title {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
}

.dashboard-subtitle {
    font-size: 1.1rem;
    opacity: 0.9;
    margin-top: 0.5rem;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: var(--background-color);
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    border-left: 4px solid #667eea;
    border: 1px solid var(--border-color);
}

/* Upload box styling */
[data-testid="stFileUploader"] {
    background: var(--background-color);
    padding: 2rem;
    border-radius: 12px;
    border: 2px dashed #667eea;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Filter section styling */
.filter-container {
    background: var(--background-color);
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
    border-left: 4px solid #764ba2;
    border: 1px solid var(--border-color);
}

/* Info box */
.stAlert {
    border-radius: 10px;
    border-left: 4px solid #667eea;
}

/* Expander styling */
[data-testid="stExpander"] {
    background: var(--background-color);
    border-radius: 10px;
    border: 1px solid var(--border-color);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
</style>
""", unsafe_allow_html=True)

# --- Date Filtering Functions ---
def get_date_range(filter_option, reference_date=None):
    """Calculate start and end dates based on filter option."""
    if reference_date is None:
        reference_date = datetime.now()
    
    today = reference_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if filter_option == "Today":
        start_date = today
        end_date = today
    
    elif filter_option == "Yesterday":
        yesterday = today - timedelta(days=1)
        start_date = yesterday
        end_date = yesterday
    
    elif filter_option == "Last 7 Days":
        start_date = today - timedelta(days=6)
        end_date = today
    
    elif filter_option == "Last 30 Days":
        start_date = today - timedelta(days=29)
        end_date = today
    
    elif filter_option == "Last 90 Days":
        start_date = today - timedelta(days=89)
        end_date = today
    
    elif filter_option == "Last 180 Days":
        start_date = today - timedelta(days=179)
        end_date = today
    
    elif filter_option == "Last 365 Days":
        start_date = today - timedelta(days=364)
        end_date = today
    
    elif filter_option == "This Month":
        start_date = today.replace(day=1)
        end_date = today
    
    elif filter_option == "Previous Month":
        first_day_this_month = today.replace(day=1)
        last_day_prev_month = first_day_this_month - timedelta(days=1)
        start_date = last_day_prev_month.replace(day=1)
        end_date = last_day_prev_month
    
    elif filter_option == "This Year":
        start_date = today.replace(month=1, day=1)
        end_date = today
    
    elif filter_option == "Previous Year":
        start_date = today.replace(year=today.year-1, month=1, day=1)
        end_date = today.replace(year=today.year-1, month=12, day=31)
    
    else:  # "All Time"
        return None, None
    
    return start_date, end_date

def filter_data_by_date(df, start_date, end_date, date_column='Created On'):
    """Filter dataframe by date range."""
    if start_date is None or end_date is None:
        return df
    
    df_filtered = df.copy()
    df_filtered[date_column] = pd.to_datetime(df_filtered[date_column], errors='coerce')
    df_filtered = df_filtered.dropna(subset=[date_column])
    
    # Normalize dates to midnight for comparison
    df_filtered['date_only'] = df_filtered[date_column].dt.normalize()
    start_date_normalized = pd.Timestamp(start_date).normalize()
    end_date_normalized = pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    
    mask = (df_filtered['date_only'] >= start_date_normalized) & (df_filtered['date_only'] <= end_date_normalized)
    result = df_filtered[mask].drop(columns=['date_only'])
    
    return result

# --- Data Loading and Processing ---
@st.cache_data
def load_and_process_data(file_path, filter_option="All Time", date_column='Created On'):
    """Loads the Excel/CSV data and performs aggregation."""
    try:
        if file_path.name.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None, None, None
    
    original_df = df.copy()
    
    if date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
        df = df.dropna(subset=[date_column])
    
    start_date, end_date = get_date_range(filter_option)
    if start_date is not None and date_column in df.columns:
        df = filter_data_by_date(df, start_date, end_date, date_column)
    
    if df.empty:
        return original_df, None, 0, 0, start_date, end_date

    transaction_summary = df.groupby('Transaction Category').agg(
        **{'# of transactions': ('Amount Paid', 'count'),
           'Total Amount Paid': ('Amount Paid', 'sum')}
    ).reset_index()

    transaction_summary['Total Amount Paid'] = transaction_summary['Total Amount Paid'].round(2)
    transaction_summary = transaction_summary.sort_values('Total Amount Paid', ascending=False)
    
    grand_total_amount = transaction_summary['Total Amount Paid'].sum()
    grand_total_count = transaction_summary['# of transactions'].sum()
    
    return original_df, transaction_summary, grand_total_amount, grand_total_count, start_date, end_date

# --- Streamlit App Layout ---

# Custom header
st.markdown("""
    <div class="dashboard-header">
        <h1 class="dashboard-title">💰 Transaction Category Analysis</h1>
        <p class="dashboard-subtitle">Comprehensive summary of transaction amounts by category</p>
    </div>
""", unsafe_allow_html=True)

# --- File Upload ---
uploaded_file = st.file_uploader(
    "📁 Upload your CSV or Excel file", 
    type=['csv', 'xlsx'],
    help="Upload a file containing 'Transaction Category' and 'Amount Paid' columns"
)

if uploaded_file:
    # Date filter options
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    st.markdown("### 📅 Date Filter")
    
    col_filter1, col_filter2 = st.columns([1, 3])
    
    with col_filter1:
        filter_options = [
            "All Time",
            "Today",
            "Yesterday", 
            "Last 7 Days",
            "Last 30 Days",
            "Last 90 Days",
            "Last 180 Days",
            "Last 365 Days",
            "This Month",
            "Previous Month",
            "This Year",
            "Previous Year"
        ]
        
        selected_filter = st.selectbox(
            "Select Time Period",
            filter_options,
            index=0
        )
    
    with col_filter2:
        if selected_filter != "All Time":
            start_date, end_date = get_date_range(selected_filter)
            if start_date and end_date:
                st.info(f"📆 Showing data from **{start_date.strftime('%B %d, %Y')}** to **{end_date.strftime('%B %d, %Y')}**")
        else:
            st.info("📆 Showing all available data")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Load and process data with filter
    original_df, summary_df, grand_total, grand_count, start_date, end_date = load_and_process_data(
        uploaded_file, 
        selected_filter
    )
    
    # Add debug info
    if selected_filter != "All Time":
        start_date_debug, end_date_debug = get_date_range(selected_filter)
        with st.expander("🔍 Debug Info - Click to see filter details"):
            st.write(f"**Filter Selected:** {selected_filter}")
            st.write(f"**Start Date:** {start_date_debug}")
            st.write(f"**End Date:** {end_date_debug}")
            if original_df is not None and 'Created On' in original_df.columns:
                date_col = pd.to_datetime(original_df['Created On'], errors='coerce')
                st.write(f"**Date Range in File:** {date_col.min()} to {date_col.max()}")
                st.write(f"**Total Rows Before Filter:** {len(original_df)}")
                if summary_df is not None:
                    st.write(f"**Total Rows After Filter:** {grand_count}")
            else:
                st.write("**'Created On' column not found in data**")
    
    if summary_df is not None and not summary_df.empty:
        # 1. Display Key Metrics
        st.markdown("### 📊 Key Metrics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Transactions", f"{grand_count:,}")
        with col2:
            st.metric("Grand Total", f"SAR {grand_total:,.2f}")
        with col3:
            st.metric("Total Categories", summary_df.shape[0])
        with col4:
            avg_transaction = grand_total / grand_count if grand_count > 0 else 0
            st.metric("Avg per Transaction", f"SAR {avg_transaction:,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # 2. Visualizations
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 📈 Amount by Category")
            fig_bar = px.bar(
                summary_df.head(10), 
                x='Total Amount Paid', 
                y='Transaction Category',
                orientation='h',
                color='Total Amount Paid',
                color_continuous_scale=[[0, '#e0c3fc'], [0.25, '#c084fc'], [0.5, '#a855f7'], [0.75, '#7c3aed'], [1, '#5b21b6']],
                text='Total Amount Paid'
            )
            fig_bar.update_traces(
                texttemplate='SAR %{text:,.0f}', 
                textposition='outside',
                marker=dict(line=dict(color='white', width=1)),
                cliponaxis=False
            )
            
            # Calculate appropriate x-axis range to fit all labels
            max_value = summary_df.head(10)['Total Amount Paid'].max()
            x_axis_max = max_value * 1.2
            
            fig_bar.update_layout(
                showlegend=False,
                height=500,
                margin=dict(l=20, r=20, t=40, b=20),
                yaxis={'categoryorder':'total ascending'},
                xaxis=dict(
                    showgrid=True,
                    range=[0, x_axis_max]
                )
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        
        with col_right:
            st.markdown("### 🥧 Distribution by Category")
            fig_pie = px.pie(
                summary_df, 
                values='Total Amount Paid', 
                names='Transaction Category',
                color_discrete_sequence=px.colors.sequential.Purples_r
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                textfont=dict(color='white', size=12),
                hovertemplate='<b>%{label}</b><br>Amount: SAR %{value:,.2f}<br>Percentage: %{percent}'
            )
            fig_pie.update_layout(
                showlegend=True,
                height=500,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 3. Display Detailed Category Table
        st.markdown("### 📋 Category-wise Summary Table")
        
        summary_display = summary_df.copy()
        summary_display['% of Total'] = (summary_display['Total Amount Paid'] / grand_total * 100).round(2)
        
        num_rows = len(summary_display)
        table_height = min(max(num_rows * 35 + 38, 150), 600)
        
        st.dataframe(
            summary_display, 
            use_container_width=True,
            column_config={
                "Transaction Category": st.column_config.TextColumn(
                    "Category",
                    width="medium"
                ),
                "# of transactions": st.column_config.NumberColumn(
                    "Transactions",
                    format="%d"
                ),
                "Total Amount Paid": st.column_config.NumberColumn(
                    "Total Amount (SAR)",
                    format="SAR %.2f"
                ),
                "% of Total": st.column_config.NumberColumn(
                    "% of Total",
                    format="%.2f%%"
                )
            },
            hide_index=True,
            height=table_height
        )

        st.markdown("<br>", unsafe_allow_html=True)

        # 4. Transaction count visualization
        st.markdown("### Transaction Count by Category")
        
        fig_count = px.bar(
            summary_df.head(10), 
            x='Transaction Category', 
            y='# of transactions',
            color='# of transactions',
            color_continuous_scale='Purples',
            text='# of transactions'
        )
        fig_count.update_traces(
            texttemplate='%{text}', 
            textposition='outside',
            marker=dict(line=dict(color='white', width=1))
        )
        fig_count.update_layout(
            showlegend=False,
            height=550,
            xaxis={'categoryorder':'total descending'},
            margin=dict(l=40, r=40, t=60, b=40),
            yaxis=dict(showgrid=True)
        )
        st.plotly_chart(fig_count, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # 5. Optional: Display Raw Data
        with st.expander("🔍 View Raw Data"):
            st.dataframe(original_df, use_container_width=True, height=400)
    
    elif summary_df is None:
        st.warning("⚠️ No data available for the selected time period. Please try a different date range.")

else:
    st.info("👆 Please upload a CSV or Excel file to get started.")