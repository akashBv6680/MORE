# ✅ Full Agentic + Multi-Agent AutoML System with Chat + EDA Email Notifications

import streamlit as st
import pandas as pd
import numpy as np
import requests
import pickle
import smtplib
import seaborn as sns
import matplotlib.pyplot as plt

from email.message import EmailMessage
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import LabelEncoder, StandardScaler, PolynomialFeatures
from sklearn.metrics import accuracy_score, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LinearRegression, Lasso, Ridge, ElasticNet, LogisticRegression
from sklearn.tree import DecisionTreeRegressor, DecisionTreeClassifier
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier, AdaBoostClassifier, AdaBoostRegressor
from sklearn.neighbors import KNeighborsRegressor, KNeighborsClassifier
from sklearn.svm import SVR, SVC
from sklearn.naive_bayes import GaussianNB, MultinomialNB, ComplementNB
from imblearn.over_sampling import SMOTE
import xgboost as xgb

from langchain_community.llms import Together
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# === Together AI ===
together_api_keys = [
    "tgp_v1_ecSsk1__FlO2mB_gAaaP2i-Affa6Dv8OCVngkWzBJUY",
    "tgp_v1_4hJBRX0XDlwnw_hhUnhP0e_lpI-u92Xhnqny2QIDAIM"
]

client_email = st.sidebar.text_input("Enter Client Email")

# === AI Prompt Functions ===
def ask_agent(prompt, model, key=0):
    response = requests.post(
        "https://api.together.xyz/v1/chat/completions",
        headers={"Authorization": f"Bearer {together_api_keys[key]}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
    )
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return f"Error: {response.text}"

def ask_data_scientist_agent(prompt):
    return ask_agent(f"[DATA SCIENTIST] {prompt}", "mistralai/Mistral-7B-Instruct-v0.1", key=0)

def ask_ml_engineer_agent(prompt):
    return ask_agent(f"[ML ENGINEER] {prompt}", "mistralai/Mistral-7B-Instruct-v0.1", key=1)

def ask_langchain_agent(prompt):
    llm = Together(model="mistralai/Mixtral-8x7B-Instruct-v0.1", api_key=together_api_keys[0])
    chain = LLMChain(
        llm=llm,
        prompt=PromptTemplate(input_variables=["query"], template="You are a smart agent. {query}")
    )
    return chain.run(prompt)

def send_email_report(subject, body, to, attachment_path=None):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = st.secrets["EMAIL_ADDRESS"]
    msg['To'] = to
    msg.set_content(body)

    if attachment_path:
        with open(attachment_path, 'rb') as f:
            img_data = f.read()
        msg.add_attachment(img_data, maintype='image', subtype='png', filename='visual.png')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(st.secrets["EMAIL_ADDRESS"], st.secrets["EMAIL_PASSWORD"])
        smtp.send_message(msg)
        msg['From'] = st.secrets["EMAIL_ADDRESS"]
# === Agent Class ===
class AutoMLAgent:
    def __init__(self, X, y):
        self.X_raw = X.copy()
        self.X = pd.get_dummies(X)
        self.y = y
        self.classification = self._detect_task_type()
        self.models = self._load_models()
        self.scaler = StandardScaler()
        self.best_model = None
        self.best_score = -np.inf
        self.best_info = {}
        self.results = []

    def _detect_task_type(self):
        return self.y.dtype == 'object' or len(np.unique(self.y)) <= 20

    def _load_models(self):
        return {
            "classification": {
                "Logistic Regression": LogisticRegression(max_iter=1000),
                "Decision Tree": DecisionTreeClassifier(),
                "Random Forest": RandomForestClassifier(),
                "Gradient Boosting": GradientBoostingClassifier(),
                "Extra Trees": ExtraTreesClassifier(),
                "AdaBoost": AdaBoostClassifier(),
                "KNN": KNeighborsClassifier(),
                "SVC": SVC(),
                "Naive Bayes (Gaussian)": GaussianNB(),
                "Naive Bayes (Multinomial)": MultinomialNB(),
                "Naive Bayes (Complement)": ComplementNB(),
                "XGBoost": xgb.XGBClassifier(use_label_encoder=False, eval_metric='mlogloss')
            },
            "regression": {
                "Linear Regression": LinearRegression(),
                "Lasso": Lasso(),
                "Ridge": Ridge(),
                "ElasticNet": ElasticNet(),
                "Decision Tree": DecisionTreeRegressor(),
                "Random Forest": RandomForestRegressor(),
                "Gradient Boosting": GradientBoostingRegressor(),
                "Extra Trees": ExtraTreesRegressor(),
                "AdaBoost": AdaBoostRegressor(),
                "KNN": KNeighborsRegressor(),
                "SVR": SVR(),
                "XGBoost": xgb.XGBRegressor(),
                "Polynomial Linear Regression": make_pipeline(PolynomialFeatures(2), LinearRegression())
            }
        }["classification" if self.classification else "regression"]

    def run(self):
        for test_size in [0.1, 0.2, 0.3]:
            X_train, X_test, y_train, y_test = train_test_split(self.X, self.y, test_size=test_size, random_state=42)

            if self.classification and len(np.unique(y_train)) > 2:
                sampler = SMOTE()
                X_train, y_train = sampler.fit_resample(X_train, y_train)

            X_train = self.scaler.fit_transform(X_train)
            X_test = self.scaler.transform(X_test)

            for name, model in self.models.items():
                try:
                    model.fit(X_train, y_train)
                    preds = model.predict(X_test)
                    score = accuracy_score(y_test, preds) if self.classification else r2_score(y_test, preds)

                    info = {
                        "Model": name,
                        "Score": round(score, 4),
                        "Test Size": test_size,
                        "Type": "Classification" if self.classification else "Regression"
                    }

                    self.results.append(info)
                    if score > self.best_score:
                        self.best_score = score
                        self.best_model = model
                        self.best_info = info
                except Exception:
                    continue

        return pd.DataFrame(self.results).sort_values(by="Score", ascending=False), self.best_info

    def save_best_model(self):
        with open("best_model.pkl", "wb") as f:
            pickle.dump(self.best_model, f)

# === Streamlit UI ===
st.set_page_config(page_title="Agentic AutoML AI", layout="wide")
st.title("🤖 Multi-Agent AutoML System with Email Intelligence")

uploaded_file = st.file_uploader("📁 Upload CSV Dataset", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.subheader("📊 Dataset Preview")
    st.dataframe(df.head())

    # Basic EDA
    st.subheader("📉 Basic EDA")
    st.write(df.describe())
    st.write("Missing Values:")
    st.write(df.isnull().sum())

    fig, ax = plt.subplots()
    sns.heatmap(df.isnull(), cbar=False, cmap="viridis", ax=ax)
    plt.title("Missing Data Visualization")
    plt.tight_layout()
    plt.savefig("eda_missing.png")
    st.pyplot(fig)

    problem_detected = df.isnull().sum().any() or df.select_dtypes(include=np.number).apply(lambda x: ((x - x.mean())/x.std()).abs().gt(3).sum()).sum() > 0

    if problem_detected and client_email:
        eda_summary = """
Dear Client,

Our system has completed the initial analysis of your dataset. Here are the key observations:

- ❗ Potential data quality issues found (missing values or outliers)
- 🧹 Visuals attached for your review (see heatmap of missing data)

Please confirm if you'd like us to proceed with data cleaning and model training.

Regards,
Akash
        """
        send_email_report("Initial Data Quality Report", eda_summary, client_email, "eda_missing.png")
        st.warning("Initial report emailed to client for confirmation before continuing.")
