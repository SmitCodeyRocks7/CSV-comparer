import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="Missing Credit Report Comparator", page_icon="📊", layout="wide")

# Custom CSS for a modern look
st.markdown("""
    <style>
    .main {background-color: #f8fafc;}
    .stButton>button {background-color: #4f8bf9; color: white; font-weight: bold; border-radius: 8px;}
    .stDownloadButton {background-color: #22bb33; color: white; font-weight: bold; border-radius: 8px;}
    .stTable {background-color: #fff; border-radius: 8px;}
    .upload-label {
        font-size: 1.2rem;
        font-weight: 700;
        color: #4f8bf9;
        margin-bottom: 0.5rem;
        letter-spacing: 1px;
    }
    .upload-box {
        background: #f0f4fa;
        border-radius: 10px;
        padding: 0.5rem 1rem 0.5rem 1rem; /* Reduced vertical padding */
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(79,139,249,0.07);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Missing Credit Report Comparator")
st.write("""
Upload your **Base** and **Comparer** CSV files below. The app will compare them and show you the rows present in the comparer but missing in the base, using all relevant columns. You can preview your files, see the results, and download the missing credit report.
""")

# File uploaders with clear labels and attractive boxes
col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown('<div class="upload-label">Base</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        base_file = st.file_uploader("Upload BASE CSV (the one to check for missing data)", type=["csv"], key="base")
        st.markdown('</div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="upload-label">Comparer</div>', unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        comparer_file = st.file_uploader("Upload COMPARER CSV (the one to compare against)", type=["csv"], key="comparer")
        st.markdown('</div>', unsafe_allow_html=True)

def extract_quarter_year(po):
    match = re.match(r'Q(\d)(\d{2})', str(po).strip())
    if match:
        quarter = int(match.group(1))
        year = int('20' + match.group(2))
        return quarter, year
    return None, None

def get_drug_name(row):
    if 'DRUG NAME' in row and pd.notna(row['DRUG NAME']):
        return str(row['DRUG NAME']).strip()
    if 'DESCRIPTION' in row and pd.notna(row['DESCRIPTION']):
        m = re.search(r'Credit memo\s*:\s*([^\-]+)', str(row['DESCRIPTION']))
        if m:
            return m.group(1).strip()
    if 'PO #' in row and pd.notna(row['PO #']):
        m = re.match(r'Q\d{3,4}\s*(.*)', str(row['PO #']))
        if m:
            return m.group(1).strip()
    return ''

def process_and_compare(base_df, comparer_df):
    # Ensure DRUG NAME exists
    for df in [base_df, comparer_df]:
        if 'DRUG NAME' not in df.columns:
            df['DRUG NAME'] = df.apply(get_drug_name, axis=1)
        else:
            df['DRUG NAME'] = df['DRUG NAME'].fillna('').astype(str).str.strip()
    # Use QUARTER KEY if present in both, else extract quarter/year from PO #
    use_quarter_key = 'QUARTER KEY' in base_df.columns and 'QUARTER KEY' in comparer_df.columns
    if use_quarter_key:
        sort_cols = ['DRUG NAME', 'QUARTER KEY']
        base_sorted = base_df.sort_values(sort_cols, ascending=[True, True]).reset_index(drop=True)
        comparer_sorted = comparer_df.sort_values(sort_cols, ascending=[True, True]).reset_index(drop=True)
    else:
        for df in [base_df, comparer_df]:
            quarters, years = zip(*df['PO #'].map(extract_quarter_year))
            df['Quarter'] = quarters
            df['Year'] = years
        sort_cols = ['DRUG NAME', 'Year', 'Quarter']
        base_sorted = base_df.sort_values(sort_cols, ascending=[True, True, True]).reset_index(drop=True)
        comparer_sorted = comparer_df.sort_values(sort_cols, ascending=[True, True, True]).reset_index(drop=True)
    # Find common columns
    common_cols = list(set(base_sorted.columns) & set(comparer_sorted.columns))
    if not common_cols:
        return pd.DataFrame(), 'No common columns found between the two files. Cannot compare.'
    # Compare: find rows in comparer not in base (on common columns)
    base_subset = base_sorted[common_cols].drop_duplicates()
    comparer_subset = comparer_sorted[common_cols].drop_duplicates()
    missing_rows = comparer_subset.merge(base_subset, on=common_cols, how='left', indicator=True)
    missing_rows = missing_rows[missing_rows['_merge'] == 'left_only']
    missing_rows = missing_rows.drop(columns=['_merge'])
    # Merge with original comparer to get all columns, then reindex to match base/comparer columns
    final_columns = ['ACCOUNT', 'PO #', 'DESCRIPTION', 'CREDIT AMT', 'DRUG LETTER', 'DRUG NAME', 'QUARTER KEY']
    full_missing = comparer_sorted.merge(missing_rows, on=common_cols, how='inner')
    for col in final_columns:
        if col not in full_missing.columns:
            full_missing[col] = ''
    full_missing = full_missing[final_columns]
    return full_missing, None

# Main logic
if base_file and comparer_file:
    try:
        base_df = pd.read_csv(base_file)
        comparer_df = pd.read_csv(comparer_file)
        st.markdown("---")
        st.subheader(":blue[Preview: Base CSV]")
        st.dataframe(base_df.head(20), use_container_width=True)
        st.subheader(":orange[Preview: Comparer CSV]")
        st.dataframe(comparer_df.head(20), use_container_width=True)
        st.markdown("---")
        if st.button("🔍 Compare and Find Missing Rows", type="primary"):
            with st.spinner("Comparing files and generating report..."):
                result_df, error = process_and_compare(base_df, comparer_df)
            if error:
                st.error(error)
            else:
                st.success(f"Comparison complete! Rows present in comparer but missing in base: {len(result_df)}")
                st.dataframe(result_df, use_container_width=True, height=400)
                # Download button
                csv_bytes = result_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download Missing Credit Report CSV",
                    data=csv_bytes,
                    file_name="Missing_Credit_Report.csv",
                    mime="text/csv"
                )
    except Exception as e:
        st.error(f"Error processing files: {e}")
else:
    st.info("Please upload both the base and comparer CSV files to begin.") 