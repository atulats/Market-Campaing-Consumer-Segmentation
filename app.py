"""Interactive marketing campaign dashboard. Run: streamlit run app.py"""

from pathlib import Path
import altair as alt
import pandas as pd
import streamlit as st

from src.marketing import ROOT, SPEND_COLS, CAMPAIGN_COLS, load_and_clean

st.set_page_config(page_title="Marketing Campaign Analytics", page_icon="📊", layout="wide")

PRODUCT_NAMES = {
    "MntWines": "Wine", "MntFruits": "Fruit", "MntMeatProducts": "Meat",
    "MntFishProducts": "Fish", "MntSweetProducts": "Sweets", "MntGoldProds": "Gold",
}
CAMPAIGN_NAMES = {**{f"AcceptedCmp{i}": f"Campaign {i}" for i in range(1, 6)}, "Response": "Latest campaign"}
SEGMENTS = {
    "High income (>75k)": "High_Income", "Young customer (<30)": "Young_Customer",
    "Campaign responder": "Campaign_Responder", "High web engagement (>5 visits)": "High_Web_Engagement",
    "Family customer (children >0)": "Family_Customer", "High spender (>90th percentile)": "High_Spender",
}


@st.cache_data(show_spinner="Loading customer data…")
def get_data() -> tuple[pd.DataFrame, dict]:
    cleaned = ROOT / "data" / "cleaned_marketing.csv"
    if cleaned.exists():
        df = pd.read_csv(cleaned)
        import json
        audit_path = ROOT / "data" / "cleaning_audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
        return df, audit
    return load_and_clean()


def percent(value: float) -> str:
    return f"{value:.1%}"


def bar_chart(frame: pd.DataFrame, x: str, y: str, title: str, *, sort=None, color="#265DAB"):
    chart = alt.Chart(frame).mark_bar(color=color, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X(x, sort=sort, title=None),
        y=alt.Y(y, title=None),
        tooltip=list(frame.columns),
    ).properties(height=320, title=title)
    st.altair_chart(chart, width="stretch")


df, audit = get_data()
st.title("Marketing campaign analytics")
st.caption("Customer-level exploration • Spend and income use the source CSV's unspecified monetary units • Age is measured as of the final enrollment date")

with st.sidebar:
    st.header("Explore customers")
    choices = {}
    for field, label in [("Country", "Country"), ("Education", "Education"), ("Marital_Status", "Marital status"), ("Age_Band", "Age band"), ("Income_Band", "Income band")]:
        values = sorted(df[field].dropna().unique().tolist())
        choices[field] = st.multiselect(label, values, default=values)
    st.caption("All tabs use these filters. Clear a selection to show no customers.")

mask = pd.Series(True, index=df.index)
for field, selected in choices.items():
    mask &= df[field].isin(selected)
filtered = df.loc[mask].copy()
if filtered.empty:
    st.warning("No customers match these filters. Choose at least one value in each filter.")
    st.stop()

size = len(filtered)
kpis = st.columns(4)
kpis[0].metric("Customers", f"{size:,}")
kpis[1].metric("Latest response rate", percent(filtered["Response"].mean()))
kpis[2].metric("Any campaign response", percent(filtered["Any_Campaign_Response"].mean()))
kpis[3].metric("Average spend", f"{filtered['Total_Spend'].mean():,.0f}")
st.caption("Any campaign response counts each customer once across Campaigns 1–5 and the latest campaign. Discounts are a purchase attribute, not an additional channel.")

overview, campaigns, products, opportunities, quality = st.tabs([
    "Overview", "Campaigns & segments", "Products & channels", "Opportunities", "Data quality"
])

with overview:
    left, right = st.columns(2)
    with left:
        age_counts = filtered.groupby("Age_Band", observed=True).size().reindex(["18–29", "30–44", "45–59", "60+"], fill_value=0).reset_index(name="Customers")
        bar_chart(age_counts, "Age_Band:N", "Customers:Q", "Customer age mix", sort=["18–29", "30–44", "45–59", "60+"])
    with right:
        income_counts = filtered.groupby("Income_Band", observed=True).size().reindex(["≤35k", "35k–75k", "75k–100k", ">100k"], fill_value=0).reset_index(name="Customers")
        bar_chart(income_counts, "Income_Band:N", "Customers:Q", "Income mix", sort=["≤35k", "35k–75k", "75k–100k", ">100k"])
    st.subheader("Response by customer profile")
    dimension = st.selectbox("Compare by", ["Age_Band", "Income_Band", "Country", "Education", "Marital_Status"], format_func=lambda x: x.replace("_", " "), key="overview_dimension")
    profile = filtered.groupby(dimension).agg(Customers=("ID", "size"), Response_rate=("Response", "mean"), Average_spend=("Total_Spend", "mean")).reset_index()
    profile = profile.loc[profile.Customers >= 30].copy()
    if not profile.empty:
        profile["Response_rate"] *= 100
        bar_chart(profile, f"{dimension}:N", "Response_rate:Q", "Latest campaign response rate (%)", sort="-y")
        st.caption("Only groups with at least 30 customers are shown. Rates describe association, not a causal effect.")
    else:
        st.info("This selection has no profile groups with at least 30 customers.")
    st.dataframe(profile.rename(columns={"Response_rate": "Response rate (%)", "Average_spend": "Average spend"}).round(1), width="stretch", hide_index=True)

with campaigns:
    st.subheader("Acceptance by campaign")
    campaign_rates = pd.DataFrame({"Campaign": list(CAMPAIGN_NAMES.values()), "Acceptance rate (%)": [filtered[col].mean() * 100 for col in CAMPAIGN_NAMES], "Acceptances": [int(filtered[col].sum()) for col in CAMPAIGN_NAMES]})
    bar_chart(campaign_rates, "Campaign:N", "Acceptance rate (%):Q", "Share of selected customers accepting each campaign", sort=list(CAMPAIGN_NAMES.values()))
    st.caption("The six columns are separate offers. Their acceptance counts can overlap across customers.")
    st.subheader("Rule-based segments")
    segment_rows = []
    for label, column in SEGMENTS.items():
        cohort = filtered.loc[filtered[column] == 1]
        segment_rows.append({"Segment": label, "Customers": len(cohort), "Latest response rate (%)": cohort.Response.mean() * 100 if len(cohort) else 0, "Average spend": cohort.Total_Spend.mean() if len(cohort) else 0, "Average web visits": cohort.NumWebVisitsMonth.mean() if len(cohort) else 0})
    segment_table = pd.DataFrame(segment_rows)
    st.dataframe(segment_table.round(1), width="stretch", hide_index=True)
    st.caption("Segments overlap. 'Campaign responder' is defined by the latest response, so its 100% response rate is tautological and should not be used to choose future targets.")
    st.subheader("Campaign by profile")
    campaign = st.selectbox("Campaign", list(CAMPAIGN_NAMES), format_func=lambda x: CAMPAIGN_NAMES[x])
    group_field = st.selectbox("Group", ["Country", "Age_Band", "Income_Band", "Education", "Marital_Status", "Family_Customer", "High_Web_Engagement", "High_Spender"], format_func=lambda x: x.replace("_", " "))
    comparison = filtered.groupby(group_field).agg(Customers=("ID", "size"), Acceptances=(campaign, "sum"), Rate=(campaign, "mean")).reset_index()
    comparison = comparison.loc[comparison.Customers >= 30].copy()
    comparison["Rate"] = (comparison["Rate"] * 100).round(1)
    st.dataframe(comparison.sort_values("Rate", ascending=False).rename(columns={"Rate": "Acceptance rate (%)"}), width="stretch", hide_index=True)

with products:
    st.subheader("Product spending")
    product_dimension = st.selectbox("Break down product mix by", ["Age_Band", "Income_Band", "Marital_Status", "Country", "Education"], format_func=lambda x: x.replace("_", " "), key="product_dimension")
    product_group = filtered.groupby(product_dimension)[SPEND_COLS].mean().reset_index()
    product_long = product_group.melt(id_vars=product_dimension, var_name="Product", value_name="Average spend")
    product_long["Product"] = product_long["Product"].map(PRODUCT_NAMES)
    product_chart = alt.Chart(product_long).mark_bar().encode(
        x=alt.X(f"{product_dimension}:N", title=None), y=alt.Y("Average spend:Q"), color=alt.Color("Product:N"),
        tooltip=[product_dimension, "Product", alt.Tooltip("Average spend:Q", format=",.1f")],
    ).properties(height=350, title="Average spend per customer by product")
    st.altair_chart(product_chart, width="stretch")
    st.caption("Product averages are per customer in each group, including customers with zero spend.")
    st.subheader("Purchases and web engagement")
    channel = filtered.groupby("High_Spender").agg(Customers=("ID", "size"), Web=("NumWebPurchases", "mean"), Store=("NumStorePurchases", "mean"), Catalog=("NumCatalogPurchases", "mean"), Discount=("NumDealsPurchases", "mean"), Web_visits=("NumWebVisitsMonth", "mean")).reset_index()
    channel["High_Spender"] = channel["High_Spender"].map({0: "Other customers", 1: "High spenders"})
    st.dataframe(channel.rename(columns={"High_Spender": "Customer group", "Web_visits": "Monthly web visits", "Discount": "Discount purchases"}).round(2), width="stretch", hide_index=True)
    channel_long = channel.melt(id_vars="High_Spender", value_vars=["Web", "Store", "Catalog"], var_name="Channel", value_name="Average purchases")
    chart = alt.Chart(channel_long).mark_bar().encode(x=alt.X("High_Spender:N", title=None), y="Average purchases:Q", color="Channel:N", xOffset="Channel:N", tooltip=list(channel_long.columns)).properties(height=310, title="Average purchases by channel")
    st.altair_chart(chart, width="stretch")

with opportunities:
    st.subheader("Under-served customers")
    underserved = filtered.loc[filtered.Under_Served == 1]
    c1, c2, c3 = st.columns(3)
    c1.metric("Under-served customers", f"{len(underserved):,}")
    c2.metric("Share of selected customers", percent(len(underserved) / len(filtered)))
    c3.metric("Average monthly web visits", f"{underserved.NumWebVisitsMonth.mean():.1f}" if len(underserved) else "—")
    st.caption("Rule: spend below the full-dataset median, more than 5 web visits per month, and no response to the latest campaign. This identifies a diagnostic cohort, not proven unmet demand.")
    if len(underserved):
        underserved_profile = underserved.groupby(["Country", "Age_Band", "Income_Band"]).agg(Customers=("ID", "size"), Average_spend=("Total_Spend", "mean"), Average_web_visits=("NumWebVisitsMonth", "mean")).reset_index().sort_values("Customers", ascending=False)
        st.dataframe(underserved_profile.head(20).round(1), width="stretch", hide_index=True)
    st.subheader("Prospective target profiles")
    profiles = filtered.groupby(["Country", "Age_Band", "Income_Band", "Family_Customer"]).agg(Customers=("ID", "size"), Response_rate=("Response", "mean"), Average_spend=("Total_Spend", "mean")).reset_index()
    profiles = profiles.loc[profiles.Customers >= 100].copy()
    profiles["Response rate (%)"] = profiles.Response_rate * 100
    profiles = profiles.drop(columns="Response_rate").sort_values(["Response rate (%)", "Average_spend"], ascending=False)
    st.dataframe(profiles.head(20).rename(columns={"Family_Customer": "Has children"}).round(1), width="stretch", hide_index=True)
    st.caption("Profiles use only traits known before a future campaign. A minimum of 100 selected customers reduces unstable rankings; test promising groups in a controlled campaign before scaling.")

with quality:
    st.subheader("Cleaning audit")
    st.json(audit)
    st.markdown("Income is kept in its original units. Values above the Tukey upper fence are flagged, not removed. Records with unknown spend, purchases, campaign flags, or invalid dates/ages are excluded because their measures cannot be interpreted reliably. Missing income is filled with the country median, then the overall median, and flagged.")
    st.subheader("Data dictionary")
    st.dataframe(pd.read_csv(ROOT / "marketing_data_dictionary.csv"), width="stretch", hide_index=True)
    st.download_button("Download filtered clean data", data=filtered.to_csv(index=False).encode("utf-8"), file_name="filtered_marketing.csv", mime="text/csv")
