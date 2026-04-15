import pandas as pd

# Load dataset
df = pd.read_csv("data.csv")

# Clean column names (VERY IMPORTANT)
df.columns = df.columns.str.lower().str.replace('.', '').str.replace(' ', '')

# Check columns
print("Columns:", df.columns)

# -------------------------------
# 1. CORRELATION ANALYSIS
# -------------------------------

correlation = df[['pm25', 'pm10', 'no2', 'co',
                  'asthma', 'bronchitis', 'cardiovascular']].corr()
correlation.to_csv("correlation.csv")

print("\n=== CORRELATION MATRIX ===\n")
print(correlation)

# -------------------------------
# 2. HIGH RISK ZONE DETECTION
# -------------------------------
df['risk_level'] = df['pm25'].apply(
    lambda x: 'High' if x > 100 else 'Medium' if x > 50 else 'Low'
)

high_risk = df[df['risk_level'] == 'High']

print("\n=== HIGH RISK AREAS ===\n")
print(high_risk[['city', 'pm25', 'asthma']])

# -------------------------------
# 3. REGION-WISE ANALYSIS
# -------------------------------
region_analysis = df.groupby('city').mean(numeric_only=True)

print("\n=== REGION ANALYSIS ===\n")
print(region_analysis)

# -------------------------------
# 4. INSIGHTS (WINNING PART)
# -------------------------------
print("\n=== INSIGHTS ===\n")

if correlation.loc['pm25', 'asthma'] > 0.5:
    print("WARNING: Strong link between PM2.5 and Asthma")

if correlation.loc['pm10', 'bronchitis'] > 0.5:
    print("WARNING: PM10 significantly impacts Bronchitis")

if correlation.loc['no2', 'cardiovascular'] > 0.5:
    print("WARNING: NO2 linked with Heart Diseases")