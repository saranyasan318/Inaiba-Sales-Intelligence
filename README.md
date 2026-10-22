INAIBA Sales Forecasting and Business Insights Dashboard

Transform Sales Data into Forecasts, Insights, and Smarter Business Decisions.

INAIBA Sales Forecasting and Business Insights Dashboard is an interactive business intelligence application built with Python and Streamlit. It helps users analyse historical sales performance, forecast future sales, detect unusual business activities, assess data quality, and generate actionable business recommendations from a single interface.

The application supports both original and imperfect sales datasets, enabling users to identify data-quality issues before relying on analytical results.

Overview

INAIBA brings sales analytics, forecasting, anomaly detection, data validation, and business insights together in one dashboard. It transforms raw sales data into meaningful information through interactive visualisations, performance indicators, predictive analysis, and downloadable reports.

Key Features

1. Data Upload & Profiling

* Upload sales datasets for analysis.
* Preview records, columns, and data types.
* Review dataset size and transaction date ranges.
* Identify missing values, duplicates, invalid dates, and inconsistent data.
* Inspect imperfect datasets to understand data-quality issues.

2. Executive KPI Overview

Monitor business performance through key performance indicators:

* Total Revenue
* Total Orders
* Total Quantity Sold
* Average Order Value
* Sales Growth
* Number of Detected Anomalies

3. Sales & Business Analytics

Explore historical sales performance using interactive visualisations:

* Monthly Revenue Trends
* Monthly Order Counts
* Revenue by Category
* Top 10 Products by Revenue
* Revenue by Region or Branch
* Top 10 Customers
* Quantity vs. Revenue Analysis
* Sales Value Distribution

4. Sales Forecasting

Estimate future sales using historical sales patterns.

Supported forecast horizons:

* 3 Months
* 6 Months
* 9 Months
* 12 Months

Forecasting outputs include:

* Historical and predicted sales
* Forecast trend visualisations
* Forecast summary tables
* Model performance evaluation
* Mean Absolute Error (MAE)
* Mean Absolute Percentage Error (MAPE)
* Forecast model comparison

Forecasts are estimates and should be interpreted alongside model performance, data quality, and historical limitations.

5. Anomaly & Risk Monitoring

Identify unusual sales patterns that may require further investigation:

* Significant sales increases or declines
* Unusually large transactions
* Abnormal product performance
* Unusual daily or monthly activity

The anomaly table can include actual values, expected values, percentage differences, possible explanations, and recommended verification actions.

Potential explanations are treated as hypotheses unless supported by the available data.

6. Data Quality & Validation

Evaluate dataset reliability through checks for:

* Missing values
* Duplicate records
* Invalid dates
* Negative quantities
* Negative or zero sales values
* Inconsistent category names
* Unusually high or low values

7. Business Insights & Recommendations

Convert analytical findings into management-focused insights based on:

* Revenue trends
* Product and category performance
* Regional and branch comparisons
* Customer concentration
* Forecast results
* Detected anomalies
* Sales volume and revenue relationships

The objective is to help users identify opportunities, investigate risks, and make informed business decisions.

8. Reports & Downloads

Export analytical outputs for further use:

* Cleaned Sales Dataset — CSV
* Forecast Results — CSV
* Anomaly Results — CSV
* Business Insights and Recommendations Report
* Data Quality Report

Available downloads depend on the features implemented in the current version.

Application Navigation

The dashboard is organised into nine modules:

1. Executive Overview
2. Sales Performance
3. Products & Categories
4. Regions / Branches
5. Forecasting
6. Anomalies & Risks
7. Business Insights
8. Data Quality
9. Reports & Downloads

Technology Stack

Technology	Purpose
Python	Core application logic and analytics
Streamlit	Interactive dashboard interface
Pandas	Data manipulation and processing
NumPy	Numerical computation
Plotly	Interactive visualisations
Scikit-learn	Model evaluation and machine learning utilities
Statsmodels	Time-series forecasting, if used
OpenPyXL	Excel file support, if used

The final technology list should match the libraries used in the repository.

Application Workflow

Upload Sales Dataset
        ↓
Preview & Data Quality Checks
        ↓
Apply Global Filters
        ↓
Executive KPI Overview
        ↓
Sales, Product & Customer Analysis
        ↓
Regional & Branch Analysis
        ↓
Sales Forecasting
  (3 / 6 / 9 / 12 Months)
        ↓
Anomaly & Risk Monitoring
        ↓
Business Insights & Recommendations
        ↓
Reports & Downloads

Getting Started

Prerequisites

* Python 3.10 or a compatible version for your dependencies
* Git
* Visual Studio Code or another Python IDE

1. Clone the Repository

git clone YOUR_GITHUB_REPOSITORY_URL
cd YOUR_REPOSITORY_FOLDER

Replace the placeholders with your actual GitHub repository URL and folder name.

2. Create a Virtual Environment

Windows:

python -m venv .venv
.venv\Scripts\activate

3. Install Dependencies

If the repository contains a requirements.txt file:

pip install -r requirements.txt

4. Run the Application

Replace App.py if your actual application entry point uses a different filename.

streamlit run App.py

The application will open in your browser, where you can upload a sales dataset and explore the available modules.

Dataset Requirements

The application is designed to analyse sales transaction data. Depending on the features used, suitable fields may include:

* Transaction Date
* Order ID
* Product Name
* Category
* Customer ID or Customer Name
* Region or Branch
* Quantity
* Sales or Revenue

Column names and required fields depend on the dataset and the application’s data-mapping logic. For meaningful forecasting, use sufficient historical data with consistent date coverage.

Privacy note: Use synthetic, anonymised, or authorised datasets. Do not commit confidential customer information or proprietary company data to a public repository.

Project Objectives

* Turn raw sales records into actionable business information.
* Improve visibility into sales and product performance.
* Support forecasting and business planning.
* Identify unusual sales patterns and potential risks.
* Evaluate data quality before analysis.
* Provide reusable reports for business decision-making.

Future Enhancements

Potential future improvements include:

* Additional forecasting algorithms and automated model selection.
* More robust forecast evaluation and prediction intervals.
* Configurable anomaly detection thresholds.
* Advanced customer segmentation.
* Automated business insight generation.
* Scheduled reports and deployment improvements.

Limitations

* Forecast accuracy depends on historical data quality and the forecasting method.
* Anomalies indicate unusual behaviour, not necessarily fraud or errors.
* Business recommendations should be reviewed in the context of business operations.
* Performance metrics should be calculated using suitable historical holdout data.
* Missing or inconsistent data may affect analytical reliability.

Project Status

Project: INAIBA Sales Forecasting and Business Insights Dashboard

Category: Business Intelligence, Data Analytics & Sales Forecasting

Interface: Interactive Streamlit Dashboard

Status: Update this section to reflect the current implementation and testing status.

Author

Developed as part of work on the INAIBA sales intelligence platform.

License

Add the appropriate license before distributing the project publicly. For company-owned code, confirm authorisation and ownership before publishing or selecting an open-source license.