import numpy as np
import pandas as pd
import statsmodels.api as sm

def generate_impact_data(n_samples=1000):
    """
    Generate synthetic trade data with some noise around a true impact model.
    True model: impact = 0.5 * (size/ADV)^0.6 * volatility
    We assume constant volatility = 0.01 for simplicity in fitting size/ADV.
    """
    np.random.seed(42)
    
    true_alpha = 0.5
    true_beta = 0.6
    volatility = 0.01
    
    # Randomly generated size/ADV fractions (e.g., 0.01% to 10% of ADV)
    size_adv_ratio = np.random.uniform(0.0001, 0.1, n_samples)
    
    # Theoretical impact without noise (fraction of price, i.e., basis points / 10000)
    theoretical_impact = true_alpha * (size_adv_ratio ** true_beta) * volatility
    
    # Add some lognormal noise because impact is strictly positive
    # Noise mean 1.0, std 0.2
    noise = np.random.lognormal(mean=0, sigma=0.2, size=n_samples)
    observed_impact = theoretical_impact * noise
    
    df = pd.DataFrame({
        'size_adv_ratio': size_adv_ratio,
        'observed_impact': observed_impact
    })
    
    return df, true_alpha, true_beta, volatility

def fit_impact_model(df):
    """
    Fits the impact model: impact = alpha * (size/ADV)^beta * vol
    Which transforms to: log(impact) = log(alpha * vol) + beta * log(size/ADV)
    We will fit this as: log(impact) = intercept + beta * log(size/ADV)
    Then alpha = exp(intercept) / vol (assuming known vol or normalized into alpha)
    """
    # Transform variables to log-space
    y_log = np.log(df['observed_impact'])
    X_log = np.log(df['size_adv_ratio'])
    
    # Add constant for the intercept: statsmodels requires this for OLS
    X_log_sm = sm.add_constant(X_log)
    
    # Fit OLS
    model = sm.OLS(y_log, X_log_sm)
    results = model.fit()
    
    intercept = results.params['const']
    beta = results.params['size_adv_ratio']
    
    # We return the intercept directly as 'log_alpha_vol' 
    # Or assuming we want pure alpha and beta and we know vol = 0.01:
    alpha = np.exp(intercept) / 0.01
    
    return alpha, beta, results.summary()

if __name__ == "__main__":
    df, t_alpha, t_beta, vol = generate_impact_data()
    alpha, beta, summary = fit_impact_model(df)
    
    print("--- True Parameters ---")
    print(f"Alpha: {t_alpha}")
    print(f"Beta: {t_beta}")
    
    print("\n--- Fitted Parameters ---")
    print(f"Alpha: {alpha:.4f}")
    print(f"Beta: {beta:.4f}")
    
    print("\n--- Regression Summary ---")
    print(summary)
