import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import calendar

# Set page configuration
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# Add CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 1rem;
    }
    .filter-section {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Dashboard title
st.markdown("<h1 class='main-header'>Sales Analytics Dashboard</h1>", unsafe_allow_html=True)

# File uploader
uploaded_file = st.file_uploader("Upload your sales data CSV file", type=["csv"])

if uploaded_file is not None:
    try:
        # Load the data
        @st.cache_data
        def load_data(file):
            df = pd.read_csv(file)
            # Convert DealDate to datetime
            df['DealDate'] = pd.to_datetime(df['DealDate'])
            # Add derived time fields
            df['Year'] = df['DealDate'].dt.year
            df['Month'] = df['DealDate'].dt.month
            df['MonthName'] = df['DealDate'].dt.month_name()
            df['Quarter'] = df['DealDate'].dt.quarter
            df['WeekOfYear'] = df['DealDate'].dt.isocalendar().week
            df['YearMonth'] = df['DealDate'].dt.strftime('%Y-%m')
            return df
        
        df = load_data(uploaded_file)
        st.success("Data successfully loaded!")
        
        # Display data summary
        with st.expander("View Data Summary"):
            st.dataframe(df.head())
            st.write(f"Total Records: {len(df)}")
            st.write(f"Date Range: {df['DealDate'].min().date()} to {df['DealDate'].max().date()}")
        
        # Create sidebar for filters
        st.sidebar.markdown("<h2 class='sub-header'>Filters</h2>", unsafe_allow_html=True)
        
        # Define categorical filters
        categorical_filters = ['State', 'Make', 'Model', 'BodyStyle', 'DriveType', 'Trim']
        
        # Add filters to sidebar
        filter_selections = {}
        for filter_col in categorical_filters:
            unique_values = ['All'] + sorted(df[filter_col].unique().tolist())
            filter_selections[filter_col] = st.sidebar.selectbox(
                f"Select {filter_col}",
                unique_values,
                index=0
            )
        
        # Add year range filter
        year_min = int(df['Year'].min())
        year_max = int(df['Year'].max())
        selected_years = st.sidebar.slider(
            "Select Year Range",
            min_value=year_min,
            max_value=year_max,
            value=(year_min, year_max)
        )
        
        # Apply filters to data
        filtered_df = df.copy()
        for filter_col, selected_value in filter_selections.items():
            if selected_value != 'All':
                filtered_df = filtered_df[filtered_df[filter_col] == selected_value]
        
        # Apply year filter
        filtered_df = filtered_df[(filtered_df['Year'] >= selected_years[0]) & 
                                (filtered_df['Year'] <= selected_years[1])]
        
        # Main dashboard area
        st.markdown("<h2 class='sub-header'>Dashboard</h2>", unsafe_allow_html=True)
        
        # Display KPIs in a row
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_sales = filtered_df['Price'].sum()
            st.metric("Total Sales", f"${total_sales:,.2f}")
        
        with col2:
            avg_price = filtered_df['Price'].mean()
            st.metric("Average Sale Price", f"${avg_price:,.2f}")
        
        with col3:
            total_vehicles = len(filtered_df)
            st.metric("Total Vehicles Sold", f"{total_vehicles:,}")
        
        # Time period selector for trend analysis
        st.markdown("<h3 class='sub-header'>Sales Trend Analysis</h3>", unsafe_allow_html=True)
        time_period = st.radio(
            "Select Time Period",
            options=["Monthly", "Quarterly", "Yearly"],
            horizontal=True
        )
        
        # Prepare time series data based on selected period
        if time_period == "Monthly":
            time_field = 'YearMonth'
            time_groupby = filtered_df.groupby('YearMonth')
            # Sort by year and month
            sort_order = sorted(filtered_df['YearMonth'].unique())
        elif time_period == "Quarterly":
            filtered_df['YearQuarter'] = filtered_df['Year'].astype(str) + "-Q" + filtered_df['Quarter'].astype(str)
            time_field = 'YearQuarter'
            time_groupby = filtered_df.groupby('YearQuarter')
            # Sort by year and quarter
            sort_order = sorted(filtered_df['YearQuarter'].unique())
        else:  # Yearly
            time_field = 'Year'
            time_groupby = filtered_df.groupby('Year')
            sort_order = sorted(filtered_df['Year'].unique())
        
        # Aggregate sales by time period
        sales_over_time = time_groupby.agg({
            'Price': ['sum', 'mean', 'count']
        }).reset_index()
        
        # Flatten the multi-level column names
        sales_over_time.columns = [' '.join(col).strip() if col[1] else col[0] for col in sales_over_time.columns.values]
        
        # Rename columns for clarity
        sales_over_time.rename(columns={
            'Price sum': 'Total Sales',
            'Price mean': 'Average Price',
            'Price count': 'Units Sold'
        }, inplace=True)
        
        # Sort by the time field
        sales_over_time[time_field] = pd.Categorical(sales_over_time[time_field], categories=sort_order, ordered=True)
        sales_over_time.sort_values(by=time_field, inplace=True)
        
        # Create time series plot
        fig_time_series = px.line(
            sales_over_time,
            x=time_field,
            y=['Total Sales', 'Units Sold'],
            title=f"Sales Trend ({time_period})",
            template='plotly_white',
            markers=True
        )
        
        fig_time_series.update_layout(
            xaxis_title="Time Period",
            yaxis_title="Value",
            legend_title="Metric",
            height=500
        )
        
        st.plotly_chart(fig_time_series, use_container_width=True)
        
        # Category analysis section
        st.markdown("<h3 class='sub-header'>Category Analysis</h3>", unsafe_allow_html=True)
        
        # Select category for analysis
        category_options = ['Make', 'Model', 'State', 'BodyStyle', 'DriveType', 'Trim']
        selected_category = st.selectbox("Select Category for Analysis", category_options)
        
        # Create category analysis plots
        col1, col2 = st.columns(2)
        
        with col1:
            # Top categories by sales volume
            category_sales = filtered_df.groupby(selected_category)['Price'].sum().reset_index()
            category_sales = category_sales.sort_values('Price', ascending=False).head(10)
            
            fig_category_sales = px.bar(
                category_sales,
                x=selected_category,
                y='Price',
                title=f"Top 10 {selected_category} by Sales Volume",
                color='Price',
                color_continuous_scale='blues'
            )
            
            fig_category_sales.update_layout(
                xaxis_title=selected_category,
                yaxis_title="Total Sales ($)",
                height=400
            )
            
            st.plotly_chart(fig_category_sales, use_container_width=True)
        
        with col2:
            # Top categories by unit count
            category_counts = filtered_df[selected_category].value_counts().reset_index()
            category_counts.columns = [selected_category, 'Count']
            category_counts = category_counts.sort_values('Count', ascending=False).head(10)
            
            fig_category_counts = px.bar(
                category_counts,
                x=selected_category,
                y='Count',
                title=f"Top 10 {selected_category} by Units Sold",
                color='Count',
                color_continuous_scale='greens'
            )
            
            fig_category_counts.update_layout(
                xaxis_title=selected_category,
                yaxis_title="Units Sold",
                height=400
            )
            
            st.plotly_chart(fig_category_counts, use_container_width=True)
        
        # Additional insights
        st.markdown("<h3 class='sub-header'>Additional Insights</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Average price by category
            avg_price_by_category = filtered_df.groupby(selected_category)['Price'].mean().reset_index()
            avg_price_by_category = avg_price_by_category.sort_values('Price', ascending=False).head(10)
            
            fig_avg_price = px.bar(
                avg_price_by_category,
                x=selected_category,
                y='Price',
                title=f"Average Price by {selected_category}",
                color='Price',
                color_continuous_scale='reds'
            )
            
            fig_avg_price.update_layout(
                xaxis_title=selected_category,
                yaxis_title="Average Price ($)",
                height=400
            )
            
            st.plotly_chart(fig_avg_price, use_container_width=True)
        
        with col2:
            # Sales distribution by age
            if 'CustomerAge' in df.columns:
                age_bins = [0, 25, 35, 45, 55, 65, 100]
                age_labels = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
                
                filtered_df['AgeGroup'] = pd.cut(filtered_df['CustomerAge'], bins=age_bins, labels=age_labels)
                age_distribution = filtered_df.groupby('AgeGroup')['Price'].sum().reset_index()
                
                fig_age = px.pie(
                    age_distribution,
                    values='Price',
                    names='AgeGroup',
                    title="Sales Distribution by Customer Age Group",
                    hole=0.4,
                    color_discrete_sequence=px.colors.sequential.Viridis
                )
                
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                # Alternative visualization if CustomerAge is not available
                month_distribution = filtered_df.groupby('MonthName')['Price'].sum().reset_index()
                # Ensure months are in correct order
                month_order = {month: i for i, month in enumerate(calendar.month_name[1:])}
                month_distribution['MonthOrder'] = month_distribution['MonthName'].map(month_order)
                month_distribution = month_distribution.sort_values('MonthOrder')
                
                fig_month = px.bar(
                    month_distribution,
                    x='MonthName',
                    y='Price',
                    title="Sales Distribution by Month",
                    color='Price',
                    color_continuous_scale='viridis'
                )
                
                fig_month.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Total Sales ($)",
                    height=400
                )
                
                st.plotly_chart(fig_month, use_container_width=True)
        
        # Show the data table with filters applied
        with st.expander("View Filtered Data"):
            st.dataframe(filtered_df)
            
            # Add download button for filtered data
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Download Filtered Data as CSV",
                data=csv,
                file_name=f"filtered_sales_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error("Please ensure your CSV file has the expected columns and format.")
else:
    # Display instructions when no file is uploaded
    st.info("""
    ### Welcome to the Sales Analytics Dashboard!
    
    Upload your sales data CSV file to get started. Your file should include these columns:
    - State: The state where the sale occurred
    - DealerID: Unique identifier for the dealer
    - DealerName: Name of the dealership
    - UniquePersonID: Unique identifier for the customer
    - CustomerName: Name of the customer
    - CustomerAge: Age of the customer
    - CustomerEthnicity: Ethnicity of the customer
    - VehicleID: Unique identifier for the vehicle
    - DealDate: Date of the sale (should be in a format convertible to datetime)
    - Price: Sale price of the vehicle
    - Make: Vehicle manufacturer
    - Model: Vehicle model
    - Year: Vehicle model year
    - Trim: Vehicle trim level
    - BodyStyle: Vehicle body style
    - DriveType: Vehicle drive type
    
    Once you upload your file, you'll be able to:
    - Filter data by various categories
    - View sales trends over time
    - Analyze performance by different categories
    - Download filtered data for further analysis
    """)