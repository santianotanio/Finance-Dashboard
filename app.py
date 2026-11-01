from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Family Finance Dashboard", page_icon="💰", layout="wide")

DATA_FILE = Path(__file__).parent / "data" / "Finance_dashboard_large_dataset.csv"

WEEKDAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

INCOME_COLOR = "#f8a3c0"
EXPENSE_COLOR = "#c9a2e8"
NET_COLOR = "#9fd8dc"


@st.cache_data(show_spinner="Loading 250,000 transactions…")
def load_data():
    df = pd.read_csv(DATA_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Amount_INR"] = pd.to_numeric(df["Amount_INR"], errors="coerce").fillna(0)
    for col in ["Transaction_Type", "Category", "Merchant", "Payment_Method", "City", "Status", "Account_ID"]:
        df[col] = df[col].astype(str).str.strip()
    df["Is_Income"] = df["Transaction_Type"].str.lower() == "income"
    df["Is_Expense"] = df["Transaction_Type"].str.lower() == "expense"
    df["Month_Date"] = df["Date"].dt.to_period("M").dt.to_timestamp()
    df["Month_Label"] = df["Month_Date"].dt.strftime("%b %y")
    return df


ld = load_data()


def fmt_rup(v):
    a = abs(float(v))
    sign = "-" if v < 0 else ""
    if a >= 1e7:
        return f"{sign}₹{a / 1e7:,.2f} Cr"
    if a >= 1e5:
        return f"{sign}₹{a / 1e5:,.2f} L"
    if a >= 1e3:
        return f"{sign}₹{a / 1e3:,.1f} K"
    return f"{sign}₹{a:,.0f}"


def money_axis(title):
    return alt.Axis(title=title, format="~s", labelExpr="'₹' + datum.label")


def month_axis(title="Month"):
    return alt.Axis(title=title, format="%b %y", labelAngle=-45)


def monthly_table(df):
    g = df.groupby(["Month_Date", "Transaction_Type"])["Amount_INR"].sum().unstack(fill_value=0)
    for c in ("Income", "Expense"):
        if c not in g.columns:
            g[c] = 0.0
    g["Net"] = g["Income"] - g["Expense"]
    g["Savings_Rate"] = np.where(g["Income"] > 0, g["Net"] / g["Income"] * 100, np.nan)
    return g.sort_index()


monthly_full = monthly_table(ld)


def chart_monthly_income_expense(mdf):
    long = mdf.reset_index().melt(id_vars="Month_Date", value_vars=["Income", "Expense"], var_name="Type", value_name="Amount")
    return (
        alt.Chart(long)
        .mark_line(point=True)
        .encode(
            x=alt.X("Month_Date:T", title=None, axis=month_axis()),
            y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
            color=alt.Color("Type:N", scale=alt.Scale(domain=["Income", "Expense"], range=[INCOME_COLOR, EXPENSE_COLOR])),
            tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
        )
        .interactive()
    )


def chart_net(mdf):
    d = mdf.reset_index()[["Month_Date", "Net"]].copy()
    d["Sign"] = np.where(d["Net"] >= 0, "Positive", "Negative")
    return alt.Chart(d).mark_bar().encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Net:Q", axis=money_axis("Net Cash Flow (INR)")),
        color=alt.Color("Sign:N", scale=alt.Scale(domain=["Positive", "Negative"], range=[INCOME_COLOR, EXPENSE_COLOR]), legend=None),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Net:Q", title="Net (₹)", format=",.0f")],
    )


def chart_savings_rate(mdf):
    d = mdf.reset_index()[["Month_Date", "Savings_Rate"]].dropna()
    bars = alt.Chart(d).mark_bar(color=NET_COLOR, opacity=0.25).encode(x=alt.X("Month_Date:T", title=None, axis=month_axis()), y=alt.Y("Savings_Rate:Q", title=None, axis=None))
    line = alt.Chart(d).mark_line(point=True, color=NET_COLOR).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Savings_Rate:Q", title="Savings Rate (%)"),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Savings_Rate:Q", title="Savings Rate (%)", format=".1f")],
    )
    return (bars + line + alt.Chart(d).mark_rule(color="gray", strokeDash=[4, 3]).encode(y=alt.datum(0))).interactive()


def chart_cumulative(mdf):
    d = mdf.reset_index()[["Month_Date", "Net"]].copy()
    d["Cumulative"] = d["Net"].cumsum()
    return alt.Chart(d).mark_area(color=NET_COLOR, opacity=0.25, line={"color": NET_COLOR}).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Cumulative:Q", axis=money_axis("Cumulative Net (INR)")),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Cumulative:Q", title="Cumulative (₹)", format=",.0f")],
    ).interactive()


def barh(d, cat_col="Category", val_col="Amount", color=EXPENSE_COLOR):
    return alt.Chart(d).mark_bar(color=color).encode(
        x=alt.X(f"{val_col}:Q", axis=money_axis("Amount (INR)")),
        y=alt.Y(f"{cat_col}:N", sort="-x", title=None),
        tooltip=[alt.Tooltip(f"{cat_col}:N", title=cat_col), alt.Tooltip(f"{val_col}:Q", title="Amount (₹)", format=",.0f")],
    )


def pie(d, cat_col="Category", val_col="Amount", colors="pastel1"):
    return alt.Chart(d).mark_arc(outerRadius=150, innerRadius=65).encode(
        theta=alt.Theta(f"{val_col}:Q", stack=True),
        color=alt.Color(f"{cat_col}:N", sort=None, scale=alt.Scale(scheme=colors), legend=None),
        tooltip=[alt.Tooltip(f"{cat_col}:N", title=cat_col), alt.Tooltip(f"{val_col}:Q", title="Amount (₹)", format=",.0f")],
    )


def chart_weekday(df):
    d = df.groupby("Weekday")["Amount_INR"].sum().reindex(WEEKDAY_ORDER, fill_value=0).reset_index()
    d.columns = ["Weekday", "Amount"]
    return alt.Chart(d).mark_bar(color=EXPENSE_COLOR).encode(
        x=alt.X("Weekday:N", sort=WEEKDAY_ORDER, title=None),
        y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
        tooltip=[alt.Tooltip("Weekday:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    )


def chart_heatmap(df):
    piv = df.pivot_table(index="Category", columns="Month_Label", values="Amount_INR", aggfunc="sum", fill_value=0)
    if piv.empty:
        return None
    label_order = df[["Month_Date", "Month_Label"]].drop_duplicates().sort_values("Month_Date")["Month_Label"].tolist()
    cat_order = piv.sum(axis=1).sort_values(ascending=False).index.tolist()
    long = piv.reset_index().melt(id_vars="Category", var_name="Month_Label", value_name="Expense")
    return alt.Chart(long).mark_rect().encode(
        x=alt.X("Month_Label:N", sort=label_order, title=None, axis=alt.Axis(labelAngle=-55, labelOverlap=True)),
        y=alt.Y("Category:N", sort=cat_order, title=None),
        color=alt.Color("Expense:Q", scale=alt.Scale(range=["#fdeaf0", "#f8bbd0", "#ec6a9c", "#d81b60"]), legend=alt.Legend(title="₹", format="~s")),
        tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Month_Label:N", title="Month"), alt.Tooltip("Expense:Q", title="Expense (₹)", format=",.0f")],
    ).interactive()


def chart_daily_rolling(df):
    daily = df.groupby("Date")["Amount_INR"].sum().sort_index()
    rolling = daily.rolling(30, min_periods=1).mean()
    long = pd.DataFrame({"Date": daily.index, "Daily Expense": daily.values, "30-Day Average": rolling.values}).melt(id_vars="Date", var_name="Type", value_name="Amount")
    return alt.Chart(long).mark_line().encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Amount:Q", axis=money_axis("Expense (INR)")),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Daily Expense", "30-Day Average"], range=["#d0d6df", EXPENSE_COLOR])),
        tooltip=[alt.Tooltip("Date:T", title="Date", format="%d %b %Y"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    ).interactive()


def grouped_period_bars(df, label_col, order=None):
    g = df.groupby([label_col, "Transaction_Type"])["Amount_INR"].sum().unstack(fill_value=0)
    for c in ("Income", "Expense"):
        if c not in g.columns:
            g[c] = 0.0
    g["Net"] = g["Income"] - g["Expense"]
    long = g.reset_index().melt(id_vars=label_col, var_name="Type", value_name="Amount")
    return alt.Chart(long).mark_bar().encode(
        x=alt.X(f"{label_col}:N", title=None, sort=order),
        xOffset=alt.XOffset("Type:N"),
        y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Income", "Expense", "Net"], range=[INCOME_COLOR, EXPENSE_COLOR, NET_COLOR])),
        tooltip=[alt.Tooltip(f"{label_col}:N"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    )


def histogram(values, bins=60, color=EXPENSE_COLOR):
    counts, edges = np.histogram(values, bins=bins)
    d = pd.DataFrame({"Amount": (edges[:-1] + edges[1:]) / 2, "Transactions": counts})
    return alt.Chart(d).mark_bar(color=color).encode(
        x=alt.X("Amount:Q", title="Amount (INR)", axis=alt.Axis(labelExpr="'₹' + datum.label", format="~s")),
        y=alt.Y("Transactions:Q", title="Transactions"),
        tooltip=[alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f"), alt.Tooltip("Transactions:Q", title="Count")],
    )


def barh_count(d, cat_col="Category", color=NET_COLOR):
    return alt.Chart(d).mark_bar(color=color).encode(
        x=alt.X("Transactions:Q", title="Transactions", axis=alt.Axis(format=",.0f")),
        y=alt.Y(f"{cat_col}:N", sort="-x", title=None),
        tooltip=[alt.Tooltip(f"{cat_col}:N"), alt.Tooltip("Transactions:Q", title="Count", format=",.0f")],
    )


def grouped_category_bars(df):
    g = df.groupby(["Category", "Transaction_Type"])["Amount_INR"].sum().unstack(fill_value=0)
    for c in ("Income", "Expense"):
        if c not in g.columns:
            g[c] = 0.0
    order = g["Expense"].sort_values(ascending=False).head(15).index.tolist()
    long = g.loc[order].reset_index().melt(id_vars="Category", var_name="Type", value_name="Amount")
    return alt.Chart(long).mark_bar().encode(
        x=alt.X("Amount:Q", axis=money_axis("Amount (INR)")),
        y=alt.Y("Category:N", sort=order, title=None),
        xOffset=alt.XOffset("Type:N"),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Income", "Expense"], range=[INCOME_COLOR, EXPENSE_COLOR])),
        tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    )


def chart_monthly_volume(df):
    all_cnt = df.groupby("Month_Date").size()
    exp_cnt = df[df["Is_Expense"]].groupby("Month_Date").size()
    d = pd.DataFrame({"All Transactions": all_cnt}).join(pd.DataFrame({"Expense Transactions": exp_cnt}), how="outer").fillna(0).reset_index()
    long = d.melt(id_vars="Month_Date", var_name="Type", value_name="Transactions")
    return alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Transactions:Q", title="Transactions"),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["All Transactions", "Expense Transactions"], range=[NET_COLOR, EXPENSE_COLOR])),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Type:N"), alt.Tooltip("Transactions:Q", title="Count", format=",.0f")],
    ).interactive()


def chart_top_categories_over_time(df):
    top10 = df.groupby("Category")["Amount_INR"].sum().nlargest(10).index
    piv = df[df["Category"].isin(top10)].pivot_table(index="Month_Date", columns="Category", values="Amount_INR", aggfunc="sum", fill_value=0)
    long = piv.reset_index().melt(id_vars="Month_Date", var_name="Category", value_name="Amount")
    return alt.Chart(long).mark_line(size=1.6).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
        color=alt.Color("Category:N", scale=alt.Scale(scheme="pastel1"), legend=alt.Legend(columns=2, symbolLimit=15)),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Category:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    ).interactive()


def chart_status(df):
    d = df["Status"].value_counts().reset_index()
    d.columns = ["Status", "Transactions"]
    return pie(d, "Status", val_col="Transactions", colors="pastel2")


st.sidebar.title("💰 Finance Dashboard")

DEFAULTS = {
    "nav": "Overview",
    "preset": "All time",
    "drange": (ld["Date"].min(), ld["Date"].max()),
    "city": None,
    "account": None,
    "payment": None,
    "category": None,
    "status": None,
}

if st.sidebar.button("↺ Reset all filters"):
    for k, v in DEFAULTS.items():
        st.session_state[k] = v

st.sidebar.divider()
nav = st.sidebar.radio("Navigate", ["Overview", "Spending", "Income", "Trends", "Budget Planner", "Transactions", "Insights"], key="nav")

st.sidebar.header("🔎 Filters")

preset = st.sidebar.selectbox("Quick range", ["All time", "Last 12 months", "Last 6 months", "Last 90 days", "Custom"], key="preset")

if preset == "Custom":
    date_from, date_to = st.sidebar.slider("Date range", min_value=ld["Date"].min().to_pydatetime(), max_value=ld["Date"].max().to_pydatetime(), value=(ld["Date"].min().to_pydatetime(), ld["Date"].max().to_pydatetime()), format="MMM YYYY", key="drange")
elif preset == "All time":
    date_from, date_to = ld["Date"].min(), ld["Date"].max()
else:
    max_d = ld["Date"].max()
    offset_map = {"Last 12 months": dict(months=12), "Last 6 months": dict(months=6), "Last 90 days": dict(days=90)}
    date_from, date_to = max_d - pd.DateOffset(**offset_map[preset]), max_d

with st.sidebar.expander("More filters", expanded=False):
    city_sel = st.multiselect("City", options=sorted(ld["City"].unique()), key="city")
    account_sel = st.multiselect("Account", options=sorted(ld["Account_ID"].unique()), key="account")
    payment_sel = st.multiselect("Payment method", options=sorted(ld["Payment_Method"].unique()), key="payment")
    category_sel = st.multiselect("Category", options=sorted(ld["Category"].unique()), key="category")
    status_sel = st.multiselect("Status", options=sorted(ld["Status"].unique()), key="status")

st.sidebar.caption(f"App v2.1 • Source: Finance_dashboard_large_dataset.csv • {len(ld):,} rows • {ld['Date'].min().date()} → {ld['Date'].max().date()}")


def ffilter(df):
    mask = (df["Date"] >= date_from) & (df["Date"] <= date_to + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1))
    if city_sel:
        mask &= df["City"].isin(city_sel)
    if account_sel:
        mask &= df["Account_ID"].isin(account_sel)
    if payment_sel:
        mask &= df["Payment_Method"].isin(payment_sel)
    if category_sel:
        mask &= df["Category"].isin(category_sel)
    if status_sel:
        mask &= df["Status"].isin(status_sel)
    return df[mask]


fdf = ffilter(ld)
exp_df = fdf[fdf["Is_Expense"]]
inc_df = fdf[fdf["Is_Income"]]

st.title("💰 Family Finance Dashboard")
st.caption(f"Showing {len(fdf):,} of {len(ld):,} transactions • {date_from.date()} → {min(date_to, ld['Date'].max()).date()}")

if fdf.empty:
    st.warning("No transactions match the selected filters. Loose a filter or hit Reset.")
    st.stop()

mdf = monthly_table(fdf)
total_income = inc_df["Amount_INR"].sum()
total_expense = exp_df["Amount_INR"].sum()
net = total_income - total_expense
savings_rate = net / total_income * 100 if total_income else np.nan

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Income", fmt_rup(total_income))
k2.metric("Total Expense", fmt_rup(total_expense))
k3.metric("Net Cash Flow", fmt_rup(net))
k4.metric("Savings Rate", f"{savings_rate:.1f}%" if total_income else "—")
k5.metric("Transactions", f"{len(fdf):,}")

st.divider()

if nav == "Overview":
    m1, m2 = st.columns([3, 2])
    prev, last = mdf.iloc[-2], mdf.iloc[-1] if len(mdf) >= 2 else None
    with m1:
        st.subheader("Monthly Income vs Expense")
        st.altair_chart(chart_monthly_income_expense(mdf), width="stretch")
    with m2:
        st.subheader("Latest Month Snapshot")
        if last is not None:
            mdate = mdf.index[-1]
            st.markdown(f"**{pd.Timestamp(mdate).strftime('%B %Y')}**")
            c1, c2, c3 = st.columns(3)
            c1.metric("Income", fmt_rup(last["Income"]), delta=fmt_rup(last["Income"] - prev["Income"]) if last is not None else None)
            c2.metric("Expense", fmt_rup(last["Expense"]), delta=fmt_rup(last["Expense"] - prev["Expense"]) if last is not None else None)
            c3.metric("Net", fmt_rup(last["Net"]), delta=fmt_rup(last["Net"] - prev["Net"]) if last is not None else None)
            st.metric("Savings Rate", f"{last['Savings_Rate']:.1f}%" if pd.notna(last["Savings_Rate"]) else "—", delta=f"{last['Savings_Rate'] - prev['Savings_Rate']:.1f} pts" if pd.notna(last["Savings_Rate"]) and pd.notna(prev["Savings_Rate"]) and last is not None else None)
        else:
            st.info("Only one month in view.")
    left, right = st.columns(2)
    with left:
        st.subheader("Net Cash Flow by Month")
        st.altair_chart(chart_net(mdf), width="stretch")
    with right:
        st.subheader("Monthly Savings Rate")
        st.altair_chart(chart_savings_rate(mdf), width="stretch")
    st.subheader("Cumulative Net Cash Flow")
    st.altair_chart(chart_cumulative(mdf), width="stretch")
    st.subheader("Monthly Ledger")
    ledger = mdf.reset_index()
    ledger["Month"] = ledger["Month_Date"].dt.strftime("%b %Y")
    st.dataframe(ledger[["Month", "Income", "Expense", "Net", "Savings_Rate"]], column_config={
        "Income": st.column_config.NumberColumn("Income (₹)", format="₹ %,.0f"),
        "Expense": st.column_config.NumberColumn("Expense (₹)", format="₹ %,.0f"),
        "Net": st.column_config.NumberColumn("Net (₹)", format="₹ %,.0f"),
        "Savings_Rate": st.column_config.NumberColumn("Savings Rate (%)", format="%.1f %%"),
    }, hide_index=True, width="stretch")

elif nav == "Spending":
    cat_sum = exp_df.groupby("Category")["Amount_INR"].sum().sort_values(ascending=False)
    avg_exp = exp_df["Amount_INR"].mean() if not exp_df.empty else 0
    s1, s2, s3 = st.columns(3)
    s1.metric("Total Spending", fmt_rup(total_expense))
    s2.metric("Avg Expense / Transaction", f"₹{avg_exp:,.0f}")
    s3.metric("Top Category", f"{cat_sum.index[0]}", delta=f"{cat_sum.iloc[0] / total_expense * 100:.1f}% of all spending")
    top = cat_sum.reset_index()
    top.columns = ["Category", "Amount"]
    share = top.head(10).copy()
    share["Share"] = share["Amount"] / total_expense * 100
    other = pd.DataFrame([{"Category": "Other", "Amount": top["Amount"][10:].sum()}])
    pie_df = pd.concat([share[["Category", "Amount"]], other], ignore_index=True)
    left, right = st.columns(2)
    with left:
        st.subheader("Expense by Category")
        st.altair_chart(barh(top), width="stretch")
    with right:
        st.subheader("Category Share (Top 10 + Other)")
        st.altair_chart(pie(pie_df), width="stretch")
    pm = exp_df.groupby("Payment_Method")["Amount_INR"].sum().sort_values(ascending=False).reset_index()
    pm.columns = ["Payment_Method", "Amount"]
    city = exp_df.groupby("City")["Amount_INR"].sum().sort_values(ascending=False).reset_index()
    city.columns = ["City", "Amount"]
    acc = exp_df.groupby("Account_ID")["Amount_INR"].sum().sort_values(ascending=False).reset_index()
    acc.columns = ["Account", "Amount"]
    l2, r2 = st.columns(2)
    with l2:
        st.subheader("By Payment Method")
        st.altair_chart(pie(pm, "Payment_Method", colors="pastel2"), width="stretch")
    with r2:
        st.subheader("By Day of Week")
        st.altair_chart(chart_weekday(exp_df), width="stretch")
    l3, r3 = st.columns(2)
    with l3:
        st.subheader("By City")
        st.altair_chart(barh(city, "City"), width="stretch")
    with r3:
        st.subheader("By Account")
        st.altair_chart(barh(acc, "Account"), width="stretch")
    merch = exp_df.groupby("Merchant")["Amount_INR"].sum().sort_values(ascending=False).head(15).reset_index()
    merch.columns = ["Merchant", "Amount"]
    st.subheader("Top 15 Merchants")
    st.altair_chart(barh(merch, "Merchant"), width="stretch")
    avg_cat = exp_df.groupby("Category")["Amount_INR"].mean().sort_values(ascending=False).reset_index()
    avg_cat.columns = ["Category", "Amount"]
    freq_cat = exp_df["Category"].value_counts().reset_index()
    freq_cat.columns = ["Category", "Transactions"]
    l5, r5 = st.columns(2)
    with l5:
        st.subheader("Average Expense by Category")
        st.altair_chart(barh(avg_cat, color="#c9a2e8"), width="stretch")
    with r5:
        st.subheader("Expense Count by Category")
        st.altair_chart(barh_count(freq_cat), width="stretch")
    st.subheader("Income vs Expense by Category")
    st.altair_chart(grouped_category_bars(fdf), width="stretch")
    st.subheader("Expense Heatmap — Category × Month")
    hm = chart_heatmap(exp_df)
    if hm is not None:
        st.altair_chart(hm, width="stretch")

elif nav == "Income":
    inc_cat = inc_df.groupby("Category")["Amount_INR"].sum().sort_values(ascending=False)
    i1, i2 = st.columns(2)
    i1.metric("Total Income", fmt_rup(total_income))
    i2.metric("Income Transactions", f"{len(inc_df):,}")
    incs = inc_cat.reset_index()
    incs.columns = ["Category", "Amount"]
    left, right = st.columns(2)
    with left:
        st.subheader("Income by Category")
        st.altair_chart(barh(incs, color=INCOME_COLOR), width="stretch")
    with right:
        st.subheader("Income by Account")
        inc_acc = inc_df.groupby("Account_ID")["Amount_INR"].sum().sort_values(ascending=False).reset_index()
        inc_acc.columns = ["Account", "Amount"]
        st.altair_chart(barh(inc_acc, "Account", color=INCOME_COLOR), width="stretch")
    st.subheader("Monthly Income Trend")
    mi = inc_df.groupby("Month_Date")["Amount_INR"].sum().reset_index()
    mi.columns = ["Month_Date", "Income"]
    st.altair_chart(alt.Chart(mi).mark_line(point=True, color=INCOME_COLOR).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Income:Q", axis=money_axis("Income (INR)")),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Income:Q", title="Income (₹)", format=",.0f")],
    ).interactive(), width="stretch")
    daily_inc = inc_df.groupby("Date")["Amount_INR"].sum().reset_index()
    daily_inc.columns = ["Date", "Income"]
    st.subheader("Daily Income Trend")
    st.altair_chart(alt.Chart(daily_inc).mark_line(color=INCOME_COLOR).encode(
        x=alt.X("Date:T", title=None),
        y=alt.Y("Income:Q", axis=money_axis("Income (INR)")),
        tooltip=[alt.Tooltip("Date:T", title="Date", format="%d %b %Y"), alt.Tooltip("Income:Q", title="Income (₹)", format=",.0f")],
    ).interactive(), width="stretch")
    l3, r3 = st.columns(2)
    with l3:
        st.subheader("Income Distribution")
        st.altair_chart(histogram(inc_df["Amount_INR"], color=INCOME_COLOR), width="stretch")
    with r3:
        st.subheader("Income Table")
        inc_table = incs.copy()
        inc_table["Share"] = inc_table["Amount"] / total_income * 100
        st.dataframe(inc_table, column_config={
            "Amount": st.column_config.NumberColumn("Income (₹)", format="₹ %,.0f"),
            "Share": st.column_config.NumberColumn("Share (%)", format="%.1f %%"),
        }, hide_index=True, width="stretch")

elif nav == "Trends":
    st.subheader("Daily Expense with 30-Day Average")
    st.altair_chart(chart_daily_rolling(exp_df), width="stretch")
    q = fdf.assign(Quarter_Label="Q" + fdf["Quarter"].str.replace("Q", "", regex=False) + " " + fdf["Year"].astype(str))
    qlabels = q.drop_duplicates("Quarter_Label").sort_values(["Year", "Quarter"])["Quarter_Label"].tolist()
    st.subheader("Quarterly Performance")
    st.altair_chart(grouped_period_bars(q, "Quarter_Label", order=qlabels), width="stretch")
    st.subheader("Yearly Performance")
    st.altair_chart(grouped_period_bars(fdf.assign(Year=fdf["Year"].astype(str)), "Year", order=[str(y) for y in sorted(ld["Year"].unique())]), width="stretch")
    vol = chart_monthly_volume(fdf)
    l2, r2 = st.columns(2)
    with l2:
        st.subheader("Transaction Volume (Monthly)")
        st.altair_chart(vol, width="stretch")
    with r2:
        st.subheader("Expense Amount Distribution")
        st.altair_chart(histogram(exp_df["Amount_INR"]), width="stretch")
    avg_m = exp_df.groupby("Month_Date")["Amount_INR"].mean().reset_index()
    avg_m.columns = ["Month_Date", "Average Expense"]
    med_m = exp_df.groupby("Month_Date")["Amount_INR"].median().reset_index()
    med_m.columns = ["Month_Date", "Median Expense"]
    merged = pd.merge(avg_m, med_m, on="Month_Date")
    long = merged.melt(id_vars="Month_Date", var_name="Type", value_name="Amount")
    st.subheader("Average vs Median Expense per Transaction")
    st.altair_chart(alt.Chart(long).mark_line(point=True).encode(
        x=alt.X("Month_Date:T", title=None, axis=month_axis()),
        y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Average Expense", "Median Expense"], range=[NET_COLOR, EXPENSE_COLOR])),
        tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.2f")],
    ).interactive(), width="stretch")
    st.subheader("Top 10 Expense Categories Over Time")
    st.altair_chart(chart_top_categories_over_time(exp_df), width="stretch")

elif nav == "Budget Planner":
    st.info("Budget planner uses the **full dataset** (ignores the sidebar filters). Average monthly spend per category is pre-filled — edit any number; your edits are kept for this session.")

    @st.cache_data(show_spinner=False)
    def default_budgets():
        exp_full = ld[ld["Is_Expense"]]
        cat_month = exp_full.groupby(["Category", "Month_Date"])["Amount_INR"].sum().groupby("Category").mean().reset_index()
        cat_month.columns = ["Category", "Monthly Spend"]
        cat_month["Budget"] = (cat_month["Monthly Spend"] / 100).apply(np.ceil) * 100
        return cat_month[["Category", "Budget"]]

    if "budgets" not in st.session_state:
        st.session_state["budgets"] = default_budgets().copy()

    budget_df = st.data_editor(
        st.session_state["budgets"],
        column_config={
            "Category": st.column_config.TextColumn("Category", disabled=True),
            "Budget": st.column_config.NumberColumn("Monthly Budget (₹)", min_value=0, format="₹ %,.0f"),
        },
        hide_index=True,
        width="stretch",
        key="budget_editor",
    )
    st.session_state["budgets"] = budget_df
    exp_full = ld[ld["Is_Expense"]]
    month_options = sorted(exp_full["Month_Date"].dropna().unique())
    month_label = st.selectbox("Target month", [pd.Timestamp(m).strftime("%B %Y") for m in month_options], index=len(month_options) - 1)
    chosen = month_options[[pd.Timestamp(m).strftime("%B %Y") for m in month_options].index(month_label)]
    spend = exp_full[exp_full["Month_Date"] == chosen].groupby("Category")["Amount_INR"].sum()
    bmap = dict(zip(budget_df["Category"], budget_df["Budget"]))
    comp = pd.DataFrame([{"Category": c, "Budget": float(bmap[c]), "Spent": float(spend.get(c, 0.0))} for c in bmap])
    comp_order = comp.sort_values("Spent", ascending=False)["Category"].tolist()
    comp_long = comp.melt(id_vars="Category", var_name="Type", value_name="Amount")
    st.subheader(f"Budget vs Spent — {month_label}")
    st.altair_chart(alt.Chart(comp_long).mark_bar().encode(
        x=alt.X("Amount:Q", axis=money_axis("Amount (INR)")),
        y=alt.Y("Category:N", sort=comp_order, title=None),
        xOffset=alt.XOffset("Type:N"),
        color=alt.Color("Type:N", scale=alt.Scale(domain=["Budget", "Spent"], range=[NET_COLOR, INCOME_COLOR])),
        tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Type:N"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
    ), width="stretch")
    overs = []
    cols = st.columns(3)
    i = 0
    tot_b, tot_s = budget_df["Budget"].sum(), 0.0
    for cat in bmap:
        spent = float(spend.get(cat, 0.0))
        tot_s += spent
        budget = float(bmap[cat])
        pct = spent / budget if budget > 0 else np.inf
        over = budget > 0 and spent > budget
        if over:
            overs.append((cat, spent, budget, pct))
        with cols[i % 3]:
            st.markdown(f"**{cat}** {'🔴' if over else '🟢'}")
            st.caption(f"Spent  {fmt_rup(spent)} / {fmt_rup(budget)}  ({pct * 100:.0f}%)" if budget > 0 else "No budget set")
            st.progress(min(pct, 1.0) if budget > 0 else 0.0)
        i += 1
    st.divider()
    o1, o2, o3 = st.columns(3)
    o1.metric("Total Budget", fmt_rup(tot_b))
    o2.metric(f"Spent in {month_label}", fmt_rup(tot_s), delta=fmt_rup(tot_s - tot_b))
    o3.metric("Overall Utilization", f"{tot_s / tot_b * 100:.1f}%" if tot_b > 0 else "—")
    st.progress(min(tot_s / tot_b, 1.0) if tot_b > 0 else 0.0)
    if overs:
        st.error(f"{len(overs)} category(ies) over budget in {month_label}: " + ", ".join(f"{c} ({p * 100:.0f}%)" for c, s, b, p in overs))
    else:
        st.success(f"All categories within budget in {month_label}. 🎉")

elif nav == "Transactions":
    q25 = exp_df.nlargest(25, "Amount_INR")[["Date", "Merchant", "Category", "Payment_Method", "City", "Amount_INR"]].copy()
    st.subheader("25 Largest Expense Transactions")
    st.dataframe(q25, column_config={
        "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
        "Amount_INR": st.column_config.NumberColumn("Amount (₹)", format="₹ %,.0f"),
    }, hide_index=True, width="stretch")
    st.subheader("Transaction Status & Volume")
    sl, sr = st.columns([1, 2])
    with sl:
        st.altair_chart(chart_status(fdf), width="stretch")
    with sr:
        acc_cnt = fdf["Account_ID"].value_counts().reset_index()
        acc_cnt.columns = ["Account", "Transactions"]
        city_cnt = fdf["City"].value_counts().reset_index()
        city_cnt.columns = ["City", "Transactions"]
        st.altair_chart(barh_count(acc_cnt, "Account"), width="stretch")
        st.altair_chart(barh_count(city_cnt, "City"), width="stretch")
    t1, t2 = st.columns(2)
    with t1:
        st.subheader("Spending by Day of Month")
        dm = exp_df.assign(Day=exp_df["Date"].dt.day).groupby("Day")["Amount_INR"].sum().reindex(range(1, 32), fill_value=0).reset_index()
        dm.columns = ["Day", "Amount"]
        st.altair_chart(alt.Chart(dm).mark_bar(color=NET_COLOR).encode(
            x=alt.X("Day:O", title="Day of Month"),
            y=alt.Y("Amount:Q", axis=money_axis("Amount (INR)")),
            tooltip=[alt.Tooltip("Day:O", title="Day"), alt.Tooltip("Amount:Q", title="Amount (₹)", format=",.0f")],
        ), width="stretch")
    with t2:
        st.subheader("Monthly Expense Trend (Filtered View)")
        me = exp_df.groupby("Month_Date")["Amount_INR"].sum().reset_index()
        me.columns = ["Month_Date", "Expense"]
        st.altair_chart(alt.Chart(me).mark_line(point=True, color=EXPENSE_COLOR).encode(
            x=alt.X("Month_Date:T", title=None, axis=month_axis()),
            y=alt.Y("Expense:Q", axis=money_axis("Expense (INR)")),
            tooltip=[alt.Tooltip("Month_Date:T", title="Month", format="%B %Y"), alt.Tooltip("Expense:Q", title="Expense (₹)", format=",.0f")],
        ).interactive(), width="stretch")
    st.subheader(f"Filtered Transactions ({len(fdf):,} rows)")
    st.caption("Preview shows the first 5,000 rows — download the CSV below for the full export.")
    preview = fdf.drop(columns=["Is_Income", "Is_Expense", "Month_Date", "Month_Label"]).head(5000)
    st.dataframe(preview, column_config={
        "Date": st.column_config.DateColumn("Date", format="DD MMM YYYY"),
        "Amount_INR": st.column_config.NumberColumn("Amount (₹)", format="₹ %,.0f"),
    }, hide_index=True, width="stretch", height=450)
    st.download_button(
        "⬇ Download filtered data as CSV",
        data=fdf.drop(columns=["Is_Income", "Is_Expense", "Month_Date", "Month_Label"]).to_csv(index=False),
        file_name="filtered_transactions.csv",
        mime="text/csv",
    )

elif nav == "Insights":
    cat_sum = exp_df.groupby("Category")["Amount_INR"].sum().sort_values(ascending=False)
    merchant_sum = exp_df.groupby("Merchant")["Amount_INR"].sum().sort_values(ascending=False)
    payment_sum = exp_df.groupby("Payment_Method")["Amount_INR"].sum().sort_values(ascending=False)
    weekday_sum = exp_df.groupby("Weekday")["Amount_INR"].sum().reindex(WEEKDAY_ORDER, fill_value=0)
    bullets = [
        f"- 🏠 **{cat_sum.index[0]}** is your biggest expense at **{fmt_rup(cat_sum.iloc[0])}** ({cat_sum.iloc[0] / total_expense * 100:.1f}% of all spending).",
        f"- 🛒 Your top merchant is **{merchant_sum.index[0]}** — {fmt_rup(merchant_sum.iloc[0])} ({merchant_sum.iloc[0] / total_expense * 100:.1f}% of spending).",
        f"- 💳 Most payments flow through **{payment_sum.index[0]}** ({fmt_rup(payment_sum.iloc[0])}, {payment_sum.iloc[0] / total_expense * 100:.1f}%).",
        f"- 🏙️ **{exp_df.groupby('City')['Amount_INR'].sum().idxmax()}** has the highest city spending.",
        f"- 📅 Weekends account for **{(weekday_sum['Saturday'] + weekday_sum['Sunday']) / total_expense * 100:.1f}%** of spending (weekday round-out: {(weekday_sum['Monday'] + weekday_sum['Tuesday'] + weekday_sum['Wednesday'] + weekday_sum['Thursday'] + weekday_sum['Friday']) / total_expense * 100:.1f}%).",
        f"- 💰 Overall savings rate is **{savings_rate:.1f}%**.",
    ]
    if len(mdf) >= 2:
        best = mdf["Savings_Rate"].idxmax()
        worst = mdf["Savings_Rate"].idxmin()
        bullets.append(f"- 🏆 Best savings month: **{pd.Timestamp(best).strftime('%B %Y')}** ({mdf.loc[best, 'Savings_Rate']:.1f}%). Weakest: **{pd.Timestamp(worst).strftime('%B %Y')}** ({mdf.loc[worst, 'Savings_Rate']:.1f}%).")
        prev, last = mdf.iloc[-2], mdf.iloc[-1]
        direction = "📈 rising" if last["Net"] >= prev["Net"] else "📉 falling"
        bullets.append(f"- 🔄 Latest net cash flow is **{direction}**: {fmt_rup(prev['Net'])} → {fmt_rup(last['Net'])} month-over-month.")
    big = exp_df.nlargest(1, "Amount_INR").iloc[0]
    bullets.append(f"- 💸 Largest single expense: **₹{big['Amount_INR']:,.0f}** at **{big['Merchant']}** on {pd.Timestamp(big['Date']).strftime('%d %b %Y')}.")
    st.markdown("\n".join(bullets))
    st.divider()
    top10 = cat_sum.head(10).reset_index()
    top10.columns = ["Category", "Amount"]
    pm_ins = payment_sum.head(8).reset_index()
    pm_ins.columns = ["Payment_Method", "Amount"]
    city_ins = exp_df.groupby("City")["Amount_INR"].sum().sort_values(ascending=False).reset_index()
    city_ins.columns = ["City", "Amount"]
    ia, ib = st.columns(2)
    with ia:
        st.subheader("Top 10 Expense Categories")
        st.altair_chart(barh(top10), width="stretch")
    with ib:
        st.subheader("Payment Method Share")
        st.altair_chart(pie(pm_ins, "Payment_Method"), width="stretch")
    ic, idd = st.columns(2)
    with ic:
        st.subheader("Spending by City")
        st.altair_chart(barh(city_ins, "City"), width="stretch")
    with idd:
        st.subheader("Spending by Weekday")
        st.altair_chart(chart_weekday(exp_df), width="stretch")
    st.subheader("Monthly Net Cash Flow")
    st.altair_chart(chart_net(mdf), width="stretch")

st.caption("Built with Streamlit • Data — Finance_dashboard_large_dataset.csv")
