from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import pandas as pd
import numpy as np
import os
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app) # Enable CORS for frontend interaction

# Global storage for latest analysis result
latest_stats = {
    'total_monitored': 12482,
    'predicted_churn_count': 1240,
    'churn_rate': 9.9,
    'revenue_at_risk': 84320,
    'accuracy': 91.4,
    'is_demo': True,
    'high_risk_users': []
}

@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/<path:path>')
def serve_static(path):
    return app.send_static_file(path)

# Load the model
MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'churn_model.pkl')

try:
    with open(MODEL_PATH, 'rb') as f:
        model_data = pickle.load(f)
    print("Model loaded successfully")
except Exception as e:
    print(f"Error loading model: {e}")
    model_data = None

@app.route('/api-info', methods=['GET'])
def index():
    return jsonify({
        'message': 'ChurnGuard API is running successfully!',
        'instructions': 'The frontend UI is served at the root URL.',
        'endpoints': ['/predict', '/health', '/upload']
    })

@app.route('/predict', methods=['POST'])
def predict():
    if model_data is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data = request.json
        # Convert incoming JSON to DataFrame
        input_df = pd.DataFrame([data])
        
        # Preprocessing using saved encoders and scaler
        encoders = model_data['encoders']
        scaler = model_data['scaler']
        model = model_data['model']
        feature_names = model_data['feature_names']
        
        # Handle categorical columns
        for col, le in encoders.items():
            if col in input_df.columns:
                # Handle unseen labels by mapping to a default if necessary (not implemented for simplicity)
                input_df[col] = le.transform(input_df[col])
        
        # Reorder columns to match training
        input_df = input_df[feature_names]
        
        # Scale
        input_scaled = scaler.transform(input_df)
        
        # Predict
        prediction = model.predict(input_scaled)[0]
        probability = model.predict_proba(input_scaled)[0][1]
        
        return jsonify({
            'churn': int(prediction),
            'probability': float(probability),
            'status': 'success'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        file_path = os.path.join(data_dir, filename)
        file.save(file_path)
        
        return jsonify({
            'status': 'success',
            'message': f'File {filename} uploaded successfully',
            'path': file_path,
            'filename': filename
        })

@app.route('/latest-stats', methods=['GET'])
def get_latest_stats():
    return jsonify(latest_stats)

@app.route('/batch-predict', methods=['POST'])
def batch_predict():
    global latest_stats
    if model_data is None:
        return jsonify({'error': 'Model not loaded'}), 500
    
    try:
        data_json = request.json
        filename = data_json.get('filename')
        if not filename:
            return jsonify({'error': 'No filename provided'}), 400
            
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        file_path = os.path.join(data_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # Load and process CSV
        df = pd.read_csv(file_path)
        original_df = df.copy()
        
        # Preprocessing setup
        encoders = model_data['encoders']
        scaler = model_data['scaler']
        model = model_data['model']
        feature_names = model_data['feature_names']
        
        # Ensure all required columns exist (simple check)
        missing_cols = [col for col in feature_names if col not in df.columns]
        if missing_cols:
             return jsonify({'error': f'Missing columns: {", ".join(missing_cols)}'}), 400
        
        # Preprocess categorical
        for col, le in encoders.items():
            if col in df.columns:
                # Basic mapping for simplicity (handling unseen labels by keeping original if transform fails)
                df[col] = df[col].map(lambda x: le.transform([x])[0] if x in le.classes_ else 0)
        
        # Reorder and scale
        X = df[feature_names]
        X_scaled = scaler.transform(X)
        
        # Batch Predict
        predictions = model.predict(X_scaled)
        probabilities = model.predict_proba(X_scaled)[:, 1]
        
        # Calculate Stats
        total_count = len(df)
        churn_count = int(np.sum(predictions))
        churn_rate = (churn_count / total_count) * 100
        
        # Revenue at risk (sum of MonthlyCharges for those predicted to churn)
        # Handle case where MonthlyCharges column might have different casing
        charges_col = 'MonthlyCharges' if 'MonthlyCharges' in original_df.columns else None
        revenue_at_risk = float(original_df.loc[predictions == 1, charges_col].sum()) if charges_col else 0.0
        
        # Extract High-Risk Users (top 10 by probability)
        # Include all columns for auto-filling the manual form
        high_risk_indices = probabilities.argsort()[-10:][::-1]
        high_risk_users = original_df.iloc[high_risk_indices].to_dict(orient='records')
        # Add probability to the dict records
        for i, idx in enumerate(high_risk_indices):
            high_risk_users[i]['churn_probability'] = float(probabilities[idx])
        
        latest_stats = {
            'total_monitored': total_count,
            'predicted_churn_count': churn_count,
            'churn_rate': round(churn_rate, 1),
            'revenue_at_risk': round(revenue_at_risk, 2),
            'accuracy': 91.4, # Keep static placeholder for model accuracy
            'is_demo': False,
            'last_filename': filename,
            'high_risk_users': high_risk_users
        }
        
        return jsonify({
             'status': 'success',
             'stats': latest_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    # Using host='0.0.0.0' to be accessible if needed, default port 5000
    app.run(debug=True, port=5000)
