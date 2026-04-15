import os
import json
import pandas as pd
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from . import db

# City coordinates for the map
CITY_COORDS = {
    "Delhi":     {"lat": 28.6139, "lng": 77.2090},
    "Mumbai":    {"lat": 19.0760, "lng": 72.8777},
    "Chennai":   {"lat": 13.0827, "lng": 80.2707},
    "Kolkata":   {"lat": 22.5726, "lng": 88.3639},
    "Hyderabad": {"lat": 17.3850, "lng": 78.4867},
    "Bengaluru": {"lat": 12.9716, "lng": 77.5946},
    "Pune":      {"lat": 18.5204, "lng": 73.8567},
    "Ahmedabad": {"lat": 23.0225, "lng": 72.5714},
}


def _seed_from_csv_if_empty():
    """Seed MongoDB from data.csv when the collection is empty."""
    if db.count() == 0:
        csv_path = os.path.join(settings.BASE_DIR, "data.csv")
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.lower().str.strip()
            df = df.rename(columns={"pm2.5": "pm25"})
            num_cols = ["pm25", "pm10", "no2", "co", "aqi", "asthma", "bronchitis", "cardiovascular"]
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
            db.insert_records(df.to_dict(orient="records"))


def dashboard_view(request):
    _seed_from_csv_if_empty()
    return render(request, "dashboard.html", {})


@csrf_exempt
def upload_view(request):
    if request.method == "POST" and request.FILES.get("file"):
        f = request.FILES["file"]
        try:
            df = pd.read_csv(f)
            df.columns = df.columns.str.lower().str.strip()
            df = df.rename(columns={"pm2.5": "pm25"})
            required = {"city", "pm25", "pm10", "no2", "co", "asthma", "bronchitis"}
            missing = required - set(df.columns)
            if missing:
                return JsonResponse({"ok": False, "error": f"Missing columns: {missing}"}, status=400)
            num_cols = ["pm25", "pm10", "no2", "co", "aqi", "asthma", "bronchitis", "cardiovascular"]
            for c in num_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
            db.insert_records(df.to_dict(orient="records"))
            return JsonResponse({"ok": True, "inserted": len(df)})
        except Exception as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=500)
    return JsonResponse({"ok": False, "error": "No file uploaded"}, status=400)


def api_data(request):
    """Return all records as JSON for Chart.js."""
    _seed_from_csv_if_empty()
    records = db.fetch_all()
    return JsonResponse({"records": records})


def api_stats(request):
    """Return aggregated stats, correlations, risk zones, and map data."""
    _seed_from_csv_if_empty()
    records = db.fetch_all()
    if not records:
        return JsonResponse({"error": "No data"}, status=404)

    df = pd.DataFrame(records)
    num_cols = ["pm25", "pm10", "no2", "co", "aqi", "asthma", "bronchitis", "cardiovascular"]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # ---- Summary KPIs ----
    kpis = {
        "avg_pm25":       round(float(df["pm25"].mean()), 2),
        "avg_aqi":        round(float(df["aqi"].mean()), 2) if "aqi" in df.columns else 0,
        "total_asthma":   int(df["asthma"].sum()),
        "total_bronchitis": int(df["bronchitis"].sum()),
        "total_cardiovascular": int(df["cardiovascular"].sum()) if "cardiovascular" in df.columns else 0,
        "total_records":  len(df),
    }

    # ---- Correlation Matrix ----
    corr_cols = [c for c in ["pm25", "pm10", "no2", "co", "asthma", "bronchitis", "cardiovascular"] if c in df.columns]
    corr = df[corr_cols].corr().round(3).to_dict()

    # ---- City-wise Aggregation ----
    city_group = df.groupby("city")[corr_cols].mean().round(2)
    city_data = city_group.reset_index().to_dict(orient="records")

    # ---- Risk Scoring ----
    df["risk_score"] = (
        (df["pm25"] / (df["pm25"].max() + 1)) * 40 +
        (df["pm10"] / (df["pm10"].max() + 1)) * 25 +
        (df["no2"]  / (df["no2"].max()  + 1)) * 15 +
        (df["co"]   / (df["co"].max()   + 1)) * 10 +
        (df["asthma"]    / (df["asthma"].max()     + 1)) * 5 +
        (df["bronchitis"] / (df["bronchitis"].max() + 1)) * 5
    ).round(2)

    # ---- AQI Trend (date-wise if date column exists) ----
    trend = []
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df_sorted = df.dropna(subset=[date_col]).sort_values(date_col)
        trend = df_sorted[[date_col, "pm25", "aqi"]].rename(
            columns={date_col: "date"}
        ).assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d")).to_dict(orient="records") if "aqi" in df.columns else []

    # ---- Map Markers ----
    map_markers = []
    for row in city_data:
        city = row.get("city", "")
        coords = CITY_COORDS.get(city, None)
        if coords:
            pm25 = row.get("pm25", 0)
            if pm25 > 150:
                risk = "High"; color = "#ef4444"
            elif pm25 > 75:
                risk = "Medium"; color = "#f59e0b"
            else:
                risk = "Low"; color = "#22c55e"
            map_markers.append({
                "city": city,
                "lat": coords["lat"],
                "lng": coords["lng"],
                "pm25": pm25,
                "aqi":  row.get("aqi", 0),
                "asthma": row.get("asthma", 0),
                "risk": risk,
                "color": color,
            })

    # ---- Policy Insights ----
    insights = []
    pm25_asthma = corr.get("pm25", {}).get("asthma", 0)
    pm10_bronchitis = corr.get("pm10", {}).get("bronchitis", 0)
    no2_cardio = corr.get("no2", {}).get("cardiovascular", 0)
    if pm25_asthma > 0.5:
        insights.append({"icon": "lung", "severity": "high", "text": f"Strong correlation ({pm25_asthma:.2f}) between PM2.5 and Asthma. Reduce vehicular and industrial emissions.", "policy": "Implement emission control zones and promote electric vehicles."})
    if pm10_bronchitis > 0.5:
        insights.append({"icon": "virus", "severity": "medium", "text": f"Significant link ({pm10_bronchitis:.2f}) between PM10 and Bronchitis. Construction dust controls required.", "policy": "Mandate dust suppression at construction sites and increase road cleaning."})
    if no2_cardio > 0.5:
        insights.append({"icon": "heart", "severity": "high", "text": f"NO2 levels show {no2_cardio:.2f} correlation with cardiovascular diseases.", "policy": "Expand green buffer zones near highways; enforce stricter vehicle emission standards."})
    insights.append({"icon": "tree", "severity": "info", "text": "Tree plantation reduces PM2.5 by up to 25% in urban areas.", "policy": "Target 1 million tree plantation drive in high-risk zones."})

    return JsonResponse({
        "kpis": kpis,
        "correlation": corr,
        "city_data": city_data,
        "trend": trend,
        "map_markers": map_markers,
        "insights": insights,
    })