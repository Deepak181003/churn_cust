// DOM Elements
const churnForm = document.getElementById('churnForm');
const predictBtn = document.getElementById('predictBtn');
const loading = document.getElementById('loading');
const resultContent = document.getElementById('resultContent');
const resultOutput = document.getElementById('resultOutput');
const probabilityFill = document.getElementById('probabilityFill');
const probabilityText = document.getElementById('probabilityText');
const statusMsg = document.getElementById('statusMsg');
const recommendation = document.getElementById('recommendation');

// 1. Animated Counter for Probability
function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = (progress * (end - start) + start).toFixed(1) + "%";
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// 2. Form Submission Handler
if (churnForm) {
    churnForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // UI State: Loading
        predictBtn.disabled = true;
        const originalBtnText = predictBtn.innerHTML;
        predictBtn.innerHTML = `
            <span class="spinner-small"></span> 
            <span class="btn-text">Consulting AI Model...</span>
        `;
        
        loading.classList.remove('hidden');
        resultContent.classList.add('hidden');
        resultOutput.classList.add('hidden');

        // Gather Data
        const formData = new FormData(churnForm);
        const data = Object.fromEntries(formData.entries());
        
        // Convert numeric fields
        data.tenure = parseInt(data.tenure);
        data.MonthlyCharges = parseFloat(data.MonthlyCharges);
        data.TotalCharges = parseFloat(data.TotalCharges);
        data.SeniorCitizen = parseInt(data.SeniorCitizen);

        try {
            const response = await fetch('/predict', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data),
            });

            const result = await response.json();

            if (response.ok) {
                displayResult(result);
            } else {
                alert('Error: ' + (result.error || 'Server error occurred'));
            }
        } catch (error) {
            console.error('Fetch error:', error);
            alert('Connection failed. Make sure the backend is running.');
        } finally {
            predictBtn.disabled = false;
            predictBtn.innerHTML = originalBtnText;
            loading.classList.add('hidden');
        }
    });
}

function displayResult(data) {
    const probValue = data.probability * 100;
    
    // Update Gauge and Text
    resultOutput.classList.remove('hidden');
    
    // Rotation for gauge fill (0% = -90deg, 100% = 90deg)
    const rotation = (data.probability * 180) - 90;
    probabilityFill.style.transform = `rotate(${rotation}deg)`;
    
    // Color coding based on risk
    if (probValue > 70) {
        probabilityFill.style.background = 'var(--danger)';
        statusMsg.innerText = 'High Churn Risk';
        statusMsg.style.color = 'var(--danger)';
        recommendation.innerText = 'Urgent intervention recommended. Customer shows strong intent to leave.';
    } else if (probValue > 30) {
        probabilityFill.style.background = 'var(--warning)';
        statusMsg.innerText = 'Moderate Churn Risk';
        statusMsg.style.color = 'var(--warning)';
        recommendation.innerText = 'Keep a close watch. Offer loyalty credits or survey the customer.';
    } else {
        probabilityFill.style.background = 'var(--success)';
        statusMsg.innerText = 'Low Churn Risk';
        statusMsg.style.color = 'var(--success)';
        recommendation.innerText = 'Customer is likely to stay. Engagement is healthy.';
    }

    // Animate percentage text
    animateValue(probabilityText, 0, probValue, 1000);
}

// 3. Integrated Flow: Load Batch Results
async function loadBatchResults() {
    const highRiskCard = document.getElementById('highRiskCard');
    const highRiskList = document.getElementById('highRiskList');
    
    if (!highRiskList) return;

    try {
        const response = await fetch('/latest-stats');
        const data = await response.json();
        
        if (data && data.high_risk_users && data.high_risk_users.length > 0) {
            highRiskCard.classList.remove('hidden');
            highRiskList.innerHTML = '';
            
            data.high_risk_users.forEach(user => {
                const prob = (user.churn_probability || 0) * 100;
                const riskClass = prob > 70 ? 'risk-high' : 'risk-med';
                
                const item = document.createElement('div');
                item.className = 'user-item';
                item.innerHTML = `
                    <div class="user-info">
                        <h4>Customer ID: ${user.customerID || 'Unknown'}</h4>
                        <p>${user.tenure}m Tenure • $${user.MonthlyCharges}/mo</p>
                    </div>
                    <div class="user-risk">
                        <span class="risk-badge ${riskClass}">${prob.toFixed(1)}% Risk</span>
                    </div>
                `;
                
                item.onclick = () => fillForm(user);
                highRiskList.appendChild(item);
            });
        }
    } catch (e) {
        console.error('Error loading high risk users:', e);
    }
}

function fillForm(user) {
    // Fill each field from user data
    const fields = [
        'tenure', 'MonthlyCharges', 'TotalCharges', 'Contract', 
        'InternetService', 'PaymentMethod', 'Gender', 'SeniorCitizen', 
        'Partner', 'Dependents', 'PhoneService', 'PaperlessBilling'
    ];
    
    fields.forEach(field => {
        const input = document.getElementById(field);
        if (input && user[field] !== undefined) {
            input.value = user[field];
        }
    });

    // Handle SeniorCitizen special case (0/1 vs No/Yes)
    const scSelect = document.getElementById('SeniorCitizen');
    if (scSelect && user.SeniorCitizen !== undefined) {
        scSelect.value = user.SeniorCitizen.toString();
    }
    
    // Smooth scroll to form
    document.getElementById('churnForm').scrollIntoView({ behavior: 'smooth' });
    
    // UI feedback: Highlight manual form
    const formCard = document.querySelector('.form-card');
    formCard.style.boxShadow = '0 0 20px var(--primary)';
    setTimeout(() => formCard.style.boxShadow = '', 1500);
}

// Initialize
window.addEventListener('DOMContentLoaded', loadBatchResults);