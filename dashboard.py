
import os
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ClientFinder | Dashboard",
    page_icon="🎯",
    layout="wide"
)

CSV_FILE = "client_prospects.csv"

st.markdown("""
<style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    div[data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 16px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎯 ClientFinder")
st.caption("Your private business prospecting workspace")

if not os.path.exists(CSV_FILE):
    st.warning("No prospect data found yet.")
    st.info(
        "Run `python client_finder.py` first. "
        "Your agent will create client_prospects.csv here."
    )
    st.stop()

try:
    df = pd.read_csv(CSV_FILE).fillna("")
except (OSError, pd.errors.ParserError) as error:
    st.error(f"Could not read the CSV: {error}")
    st.stop()

if df.empty:
    st.info("Your prospect file is empty. Run a search to collect leads.")
    st.stop()

# Ensure optional columns exist so older CSVs still work.
for column in [
    "business", "domain", "website", "email", "contact_page",
    "feature_requested", "feature_evidence", "recommendation",
    "search_query", "search_source"
]:
    if column not in df.columns:
        df[column] = ""

# Sidebar filters
st.sidebar.header("Filter prospects")

search_text = st.sidebar.text_input(
    "Search business or domain"
).strip().lower()

features = sorted(
    value for value in df["feature_requested"].unique()
    if str(value).strip()
)
selected_features = st.sidebar.multiselect(
    "Feature investigated",
    features,
    default=features
)

email_filter = st.sidebar.selectbox(
    "Public email",
    ["All prospects", "Email found", "No email found"]
)

filtered = df.copy()

if search_text:
    searchable = (
        filtered["business"].astype(str)
        + " " + filtered["domain"].astype(str)
        + " " + filtered["website"].astype(str)
    ).str.lower()
    filtered = filtered[searchable.str.contains(search_text, regex=False)]

filtered = filtered[
    filtered["feature_requested"].isin(selected_features)
]

if email_filter == "Email found":
    filtered = filtered[filtered["email"].astype(str).str.strip() != ""]
elif email_filter == "No email found":
    filtered = filtered[filtered["email"].astype(str).str.strip() == ""]

# Overview metrics
total = len(filtered)
with_email = int(filtered["email"].astype(str).str.strip().ne("").sum())
with_contact = int(
    filtered["contact_page"].astype(str).str.strip().ne("").sum()
)
unique_domains = filtered["domain"].replace("", pd.NA).nunique()

st.subheader("Overview")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Prospects", total)
m2.metric("Public emails found", with_email)
m3.metric("Contact pages found", with_contact)
m4.metric("Unique domains", unique_domains)

st.divider()

# Analytics
left, right = st.columns(2)

with left:
    st.subheader("Prospects by feature")
    feature_counts = (
        filtered["feature_requested"]
        .replace("", "Unknown")
        .value_counts()
    )
    if not feature_counts.empty:
        st.bar_chart(feature_counts)
    else:
        st.info("No feature data available.")

with right:
    st.subheader("Research coverage")
    coverage = pd.DataFrame({
        "Research item": ["Email found", "Contact page found"],
        "Count": [with_email, with_contact]
    }).set_index("Research item")
    st.bar_chart(coverage)

st.divider()

# Prospect list
st.subheader("Prospect list")
st.caption(
    "Search results are candidates, not confirmed buyers. "
    "Verify each opportunity before contacting a business."
)

display_columns = [
    "business", "domain", "website", "email", "contact_page",
    "feature_requested", "feature_evidence", "recommendation"
]
display_columns = [c for c in display_columns if c in filtered.columns]

st.dataframe(
    filtered[display_columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "website": st.column_config.LinkColumn("Website"),
        "contact_page": st.column_config.LinkColumn("Contact page"),
    }
)

csv_data = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Download filtered prospects",
    data=csv_data,
    file_name="filtered_client_prospects.csv",
    mime="text/csv"
)

st.divider()

# Inspect a single candidate
st.subheader("Inspect a prospect")

options = filtered.index.tolist()
if options:
    chosen = st.selectbox(
        "Choose a business",
        options,
        format_func=lambda i: (
            str(df.loc[i, "business"]) or str(df.loc[i, "domain"])
        )
    )

    prospect = df.loc[chosen]

    st.markdown(f"### {prospect['business'] or prospect['domain']}")

    if prospect["website"]:
        st.markdown(f"[Open website]({prospect['website']})")
    if prospect["contact_page"]:
        st.markdown(f"[Open contact page]({prospect['contact_page']})")

    st.write("**Public email(s):**", prospect["email"] or "Not found")
    st.write("**Feature investigated:**", prospect["feature_requested"])
    st.write("**Observed evidence:**", prospect["feature_evidence"])
    st.write("**Possible service:**", prospect["recommendation"])

    st.info(
        "A missing keyword is not proof that a feature is absent. "
        "Check the actual site and its pages before proposing work."
    )
else:
    st.info("No prospects match these filters.")
