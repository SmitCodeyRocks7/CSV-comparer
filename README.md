# Missing Credit Report Comparator

A beautiful, user-friendly Streamlit app to compare two CSV files and generate a missing credit report. Upload your base and comparer CSVs, preview them, compare, and download the results—all in your browser!

## Features
- Upload two CSV files (base and comparer)
- Preview both files
- Compare and find rows present in comparer but missing in base
- Download the missing credit report as CSV
- Modern, attractive UI

## How to Run Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   streamlit run missing_credit_app.py
   ```
3. Open the link shown in your terminal (usually http://localhost:8501)

## How to Deploy on Streamlit Community Cloud

1. Push your code (`missing_credit_app.py` and `requirements.txt`) to a GitHub repository.
2. Go to [Streamlit Community Cloud](https://streamlit.io/cloud) and sign in with GitHub.
3. Click "New app", select your repo and branch, and set the main file to `missing_credit_app.py`.
4. Click "Deploy". Your app will be live and shareable!

## How to Deploy on Hugging Face Spaces

1. Create a Hugging Face account and a new Space (choose Streamlit as the SDK).
2. Upload your code and `requirements.txt`.
3. Your app will be live instantly.

## Example requirements.txt
```
streamlit
pandas
```

---

**Enjoy your easy, beautiful CSV comparison app!** 