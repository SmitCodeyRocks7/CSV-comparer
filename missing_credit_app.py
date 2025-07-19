import streamlit as st
import pandas as pd
import io
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from twilio.rest import Client as TwilioClient
import base64
import os

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

def clean_po(po):
    if pd.isna(po):
        return ''
    return re.sub(r'\s+', '', str(po)).strip().lower()

def add_spaces(po):
    if pd.isna(po):
        return ''
    po = str(po).lower()
    po = re.sub(r"(q\d{3})(onmk)", r"\1 \2", po)
    po = re.sub(r"(onmk|onmark)([a-z]+)", r"\1 \2", po)
    po = re.sub(r"([a-z])(\d+%)", r"\1 \2", po)
    return po.strip()

def extract_features(df):
    # Clean and space PO #
    df = df.copy()
    df["PO #"] = df["PO #"].apply(lambda x: add_spaces(clean_po(x)))
    # Remove blank PO rows
    df = df[df["PO #"].notna() & (df["PO #"] != '')]
    # Extract features
    df["Quarter Key"] = df["PO #"].str.extract(r"^(q\d{3})", expand=False)
    df["Drug Category"] = df["PO #"].str.extract(r"(?:onmk|onmark)\s+(.+?)\s+rbt", expand=False)
    return df

def quarter_sort_key(q):
    try:
        return int(q[1:]) if isinstance(q, str) and len(q) > 1 else 0
    except:
        return 0

def sort_df(df):
    df = df.copy()
    df["Quarter Sort"] = df["Quarter Key"].apply(quarter_sort_key)
    df_sorted = df.sort_values(by=["Drug Category", "Quarter Sort"]).drop(columns=["Quarter Sort"])
    return df_sorted

def compare_bidirectional(df1, df2):
    # Find differences
    missing_in_df2 = df1[~df1["PO #"].isin(df2["PO #"])]
    missing_in_df2 = missing_in_df2.copy()
    missing_in_df2["Missing In"] = "Comparer"

    missing_in_df1 = df2[~df2["PO #"].isin(df1["PO #"])]
    missing_in_df1 = missing_in_df1.copy()
    missing_in_df1["Missing In"] = "Base"

    final_missing = pd.concat([missing_in_df2, missing_in_df1], ignore_index=True)
    # Keep relevant columns
    columns_to_keep = ['PO #', 'DESCRIPTION', 'CREDIT AMT', 'Missing In', 'Drug Category', 'Quarter Key']
    for col in columns_to_keep:
        if col not in final_missing.columns:
            final_missing[col] = ''
    final_missing = final_missing[columns_to_keep]
    return final_missing

# Add UI for automation
st.markdown("---")
st.header("📤 Send Missing Credit Report Automatically")
with st.form("send_report_form"):
    delivery_method = st.radio("How would you like to receive the report?", ["Email", "WhatsApp"], horizontal=True)
    if delivery_method == "Email":
        recipient = st.text_input("Enter your email address:")
    else:
        recipient = st.text_input("Enter your WhatsApp phone number (with country code, e.g. +1234567890):")
    send_btn = st.form_submit_button("Send Report")

# Main logic
if base_file and comparer_file:
    try:
        base_df = pd.read_csv(base_file)
        comparer_df = pd.read_csv(comparer_file)
        # Feature extraction and cleaning
        base_feat = extract_features(base_df)
        comparer_feat = extract_features(comparer_df)
        # Sorting
        base_sorted = sort_df(base_feat)
        comparer_sorted = sort_df(comparer_feat)
        st.markdown("---")
        st.subheader(":blue[Preview: Sorted Base CSV]")
        st.dataframe(base_sorted.head(20), use_container_width=True)
        st.download_button(
            label="⬇️ Download Sorted Base CSV",
            data=base_sorted.to_csv(index=False).encode('utf-8'),
            file_name="sorted_base.csv",
            mime="text/csv"
        )
        st.subheader(":orange[Preview: Sorted Comparer CSV]")
        st.dataframe(comparer_sorted.head(20), use_container_width=True)
        st.download_button(
            label="⬇️ Download Sorted Comparer CSV",
            data=comparer_sorted.to_csv(index=False).encode('utf-8'),
            file_name="sorted_comparer.csv",
            mime="text/csv"
        )
        st.markdown("---")
        if st.button("🔍 Compare and Find Missing Rows (Both Directions)", type="primary"):
            with st.spinner("Comparing files and generating report..."):
                result_df = compare_bidirectional(base_sorted, comparer_sorted)
            st.success(f"Comparison complete! Total missing rows: {len(result_df)}")
            st.dataframe(result_df, use_container_width=True, height=400)
            # Download button
            csv_bytes = result_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download Missing Credit Report CSV",
                data=csv_bytes,
                file_name="Missing_Credit_Report.csv",
                mime="text/csv"
            )
            # Automation: Send report if requested
            if send_btn and recipient:
                try:
                    if delivery_method == "Email":
                        # Send via SendGrid
                        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY", "SENDGRID_API_KEY_PLACEHOLDER"))
                        message = Mail(
                            from_email='your@email.com',
                            to_emails=recipient,
                            subject='Your Missing Credit Report',
                            html_content='Please find your missing credit report attached.'
                        )
                        encoded = base64.b64encode(csv_bytes).decode()
                        attachedFile = Attachment(
                            FileContent(encoded),
                            FileName('Missing_Credit_Report.csv'),
                            FileType('text/csv'),
                            Disposition('attachment')
                        )
                        message.attachment = attachedFile
                        response = sg.send(message)
                        st.success(f"Report sent to {recipient} via Email!")
                    else:
                        # Send via Twilio WhatsApp
                        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "TWILIO_SID_PLACEHOLDER")
                        twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "TWILIO_TOKEN_PLACEHOLDER")
                        twilio_from = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
                        client = TwilioClient(twilio_sid, twilio_token)
                        # WhatsApp does not support file attachments directly, so upload to a file host or send as text/download link
                        # For demo, send as text (first 10 rows)
                        preview = result_df.head(10).to_csv(index=False)
                        client.messages.create(
                            body=f"Your Missing Credit Report (first 10 rows):\n\n{preview}\n\nFor full report, please use the web download.",
                            from_=f"whatsapp:{twilio_from}",
                            to=f"whatsapp:{recipient}"
                        )
                        st.success(f"Report sent to {recipient} via WhatsApp!")
                except Exception as e:
                    st.error(f"Failed to send report: {e}")
    except Exception as e:
        st.error(f"Error processing files: {e}")
else:
    st.info("Please upload both the base and comparer CSV files to begin.") 