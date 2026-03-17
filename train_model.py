import pandas as pd
import numpy as np
import pickle
import os
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

# Ensure directories exist
os.makedirs('data', exist_ok=True)
os.makedirs('models', exist_ok=True)

def generate_data(n_samples=2000):
    np.random.seed(42)
    
    data = {
        'tenure': np.random.randint(1, 72, n_samples),
        'MonthlyCharges': np.random.uniform(18, 118, n_samples),
        'TotalCharges': np.random.uniform(18, 8000, n_samples),
        'Gender': np.random.choice(['Male', 'Female'], n_samples),
        'SeniorCitizen': np.random.choice([0, 1], n_samples),
        'Partner': np.random.choice(['Yes', 'No'], n_samples),
        'Dependents': np.random.choice(['Yes', 'No'], n_samples),
        'PhoneService': np.random.choice(['Yes', 'No'], n_samples),
        'InternetService': np.random.choice(['DSL', 'Fiber optic', 'No'], n_samples),
        'Contract': np.random.choice(['Month-to-month', 'One year', 'Two year'], n_samples),
        'PaperlessBilling': np.random.choice(['Yes', 'No'], n_samples),
        'PaymentMethod': np.random.choice(['Electronic check', 'Mailed check', 'Bank transfer', 'Credit card'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Simple logic for churn (synthetic)
    # Higher churn for month-to-month, high monthly charges, low tenure
    churn_prob = (
        (df['Contract'] == 'Month-to-month').astype(int) * 0.4 +
        (df['MonthlyCharges'] > 80).astype(int) * 0.2 +
        (df['tenure'] < 12).astype(int) * 0.2 +
        np.random.uniform(0, 0.2, n_samples)
    )
    
    df['Churn'] = (churn_prob > 0.5).astype(int)
    
    df.to_csv('data/customer_churn_data.csv', index=False)
    print("Synthetic data generated and saved to data/customer_churn_data.csv")
    return df

def train_model():
    df = generate_data()
    
    # Preprocessing
    categorical_cols = ['Gender', 'Partner', 'Dependents', 'PhoneService', 'InternetService', 'Contract', 'PaperlessBilling', 'PaymentMethod']
    
    # Store encoders for inference
    encoders = {}
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    X = df.drop('Churn', axis=1)
    y = df['Churn']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    print(f"Model Accuracy: {accuracy_score(y_test, y_pred):.2f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Save model and preprocessing objects
    model_data = {
        'model': model,
        'scaler': scaler,
        'encoders': encoders,
        'feature_names': list(X.columns)
    }
    
    with open('models/churn_model.pkl', 'wb') as f:
        pickle.dump(model_data, f)
    
    print("Model and preprocessing objects saved to models/churn_model.pkl")

if __name__ == "__main__":
    train_model()
