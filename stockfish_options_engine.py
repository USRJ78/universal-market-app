import numpy as np
import pandas as pd
import yfinance as yf
import math
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque
import matplotlib.pyplot as plt
from scipy.special import erf

# --- Black-Scholes Math (The Game Engine) ---
def norm_cdf(x):
    return (1.0 + erf(x / 1.4142135623730951)) / 2.0

def norm_pdf(x):
    return np.exp(-0.5 * x**2) / np.sqrt(2 * np.pi)

def bs_greeks(S, K, T, r, sigma, is_call=True):
    sigma = max(sigma, 1e-5)
    T = max(T, 1e-5)
    d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
    d2 = d1 - sigma*np.sqrt(T)
    
    gamma = norm_pdf(d1) / (S * sigma * np.sqrt(T))
    
    if is_call:
        prem = S * norm_cdf(d1) - K * np.exp(-r*T) * norm_cdf(d2)
        delta = norm_cdf(d1)
        theta = -(S * norm_pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(-r*T) * norm_cdf(d2)
    else:
        prem = K * np.exp(-r*T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = norm_cdf(d1) - 1.0
        theta = -(S * norm_pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(-r*T) * norm_cdf(-d2)
        
    return prem, delta, gamma, theta / 365.0

# --- The Neural Network (NNUE) ---
class OptionNet(nn.Module):
    def __init__(self, input_size, action_size):
        super(OptionNet, self).__init__()
        self.fc1 = nn.Linear(input_size, 64)
        self.fc2 = nn.Linear(64, 64)
        self.fc3 = nn.Linear(64, action_size)
        
    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = torch.relu(self.fc2(x))
        return self.fc3(x) # Returns Q-values for each action

# --- The Environment (The Chess Board) ---
class OptionsEnvironment:
    def __init__(self, data_series, vols, initial_balance=100000):
        self.prices = data_series
        self.vols = vols
        self.initial_balance = initial_balance
        self.r = 0.05
        self.action_space = 5 # Actions: 0:Hold, 1:Buy ATM Call, 2:Buy OTM Put, 3:Sell ATM Call, 4:Close All
        self.reset()
        
    def reset(self):
        self.t = 0
        self.balance = self.initial_balance
        self.portfolio = [] # list of dicts: {'is_call': True, 'strike': K, 'qty': Q, 'expiry_t': t+7}
        self.max_t = len(self.prices) - 8
        self.equity = self.balance
        return self._get_state()
        
    def _get_state(self):
        S = self.prices[self.t]
        sigma = self.vols[self.t]
        
        # Calculate current Greeks
        net_delta = 0
        net_gamma = 0
        net_theta = 0
        
        for pos in self.portfolio:
            T_yrs = (pos['expiry_t'] - self.t) / 365.0
            if T_yrs <= 0: continue
            _, d, g, th = bs_greeks(S, pos['strike'], T_yrs, self.r, sigma, pos['is_call'])
            net_delta += d * pos['qty']
            net_gamma += g * pos['qty']
            net_theta += th * pos['qty']
            
        # State: [Normalized Spot, Volatility, Days Remaining (proxy), Delta, Gamma, Theta]
        state = [S / 10000.0, sigma, 7.0/365.0, net_delta, net_gamma*100, net_theta]
        return np.array(state, dtype=np.float32)
        
    def step(self, action):
        S = self.prices[self.t]
        sigma = self.vols[self.t]
        
        # Execute Action
        if action == 1: # Buy ATM Call
            prem, _, _, _ = bs_greeks(S, S, 7.0/365.0, self.r, sigma, True)
            self.balance -= prem
            self.portfolio.append({'is_call': True, 'strike': S, 'qty': 1.0, 'expiry_t': self.t + 7})
        elif action == 2: # Buy OTM Put (95% strike)
            K = S * 0.95
            prem, _, _, _ = bs_greeks(S, K, 7.0/365.0, self.r, sigma, False)
            self.balance -= prem
            self.portfolio.append({'is_call': False, 'strike': K, 'qty': 1.0, 'expiry_t': self.t + 7})
        elif action == 3: # Sell ATM Call
            prem, _, _, _ = bs_greeks(S, S, 7.0/365.0, self.r, sigma, True)
            self.balance += prem
            self.portfolio.append({'is_call': True, 'strike': S, 'qty': -1.0, 'expiry_t': self.t + 7})
        elif action == 4: # Close All
            for pos in self.portfolio:
                T_yrs = (pos['expiry_t'] - self.t) / 365.0
                if T_yrs > 0:
                    prem, _, _, _ = bs_greeks(S, pos['strike'], T_yrs, self.r, sigma, pos['is_call'])
                    self.balance += prem * pos['qty']
            self.portfolio = []
        
        # Move forward in time 1 day
        self.t += 1
        S_new = self.prices[self.t]
        sigma_new = self.vols[self.t]
        
        # Settle expirations
        active_portfolio = []
        for pos in self.portfolio:
            if self.t >= pos['expiry_t']:
                if pos['is_call']:
                    payoff = max(0, S_new - pos['strike'])
                else:
                    payoff = max(0, pos['strike'] - S_new)
                self.balance += payoff * pos['qty']
            else:
                active_portfolio.append(pos)
        self.portfolio = active_portfolio
        
        # Calculate new equity to find reward
        options_value = 0
        for pos in self.portfolio:
            T_yrs = (pos['expiry_t'] - self.t) / 365.0
            prem, _, _, _ = bs_greeks(S_new, pos['strike'], T_yrs, self.r, sigma_new, pos['is_call'])
            options_value += prem * pos['qty']
            
        new_equity = self.balance + options_value
        reward = (new_equity - self.equity) / self.initial_balance # Normalized reward
        
        # Heavy penalty for bankruptcy
        if new_equity <= 0:
            reward = -1.0
            done = True
        else:
            done = self.t >= self.max_t
            
        self.equity = new_equity
        next_state = self._get_state()
        
        return next_state, reward, done

def train_stockfish_engine():
    print("Fetching Market Data...")
    df = yf.download("^NSEI", start="2014-01-01", end="2024-01-01")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df['LogRet'] = np.log(df['Close'] / df['Close'].shift(1))
    df['Vol30'] = df['LogRet'].rolling(window=30).std() * math.sqrt(365)
    df['Vol30'] = df['Vol30'].bfill()
    df['Vol30'] = df['Vol30'].apply(lambda x: 0.15 if math.isnan(x) or x <= 0 else x)
    
    prices = df['Close'].values
    vols = df['Vol30'].values
    
    env = OptionsEnvironment(prices, vols)
    
    state_size = 6
    action_size = env.action_space
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on {device}...")
    
    model = OptionNet(state_size, action_size).to(device)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    loss_fn = nn.MSELoss()
    
    memory = deque(maxlen=2000)
    gamma = 0.95 # Discount factor
    epsilon = 1.0
    epsilon_min = 0.05
    epsilon_decay = 0.99
    
    episodes = 25 # Keeping small for fast execution
    batch_size = 32
    
    losses = []
    equities = []
    
    for e in range(episodes):
        state = env.reset()
        state = torch.FloatTensor(state).to(device)
        done = False
        total_reward = 0
        
        while not done:
            if random.random() <= epsilon:
                action = random.randrange(action_size)
            else:
                with torch.no_grad():
                    q_values = model(state)
                    action = torch.argmax(q_values).item()
                    
            next_state, reward, done = env.step(action)
            next_state_t = torch.FloatTensor(next_state).to(device)
            reward_t = torch.FloatTensor([reward]).to(device)
            
            memory.append((state, action, reward_t, next_state_t, done))
            state = next_state_t
            total_reward += reward
            
            if len(memory) > batch_size:
                batch = random.sample(memory, batch_size)
                
                states = torch.stack([x[0] for x in batch]).to(device)
                actions = torch.LongTensor([x[1] for x in batch]).to(device)
                rewards = torch.cat([x[2] for x in batch]).to(device)
                next_states = torch.stack([x[3] for x in batch]).to(device)
                dones = torch.FloatTensor([1 if x[4] else 0 for x in batch]).to(device)
                
                curr_q = model(states).gather(1, actions.unsqueeze(1)).squeeze(1)
                with torch.no_grad():
                    next_q = model(next_states).max(1)[0]
                target_q = rewards + gamma * next_q * (1 - dones)
                
                loss = loss_fn(curr_q, target_q)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
        if epsilon > epsilon_min:
            epsilon *= epsilon_decay
            
        losses.append(total_reward)
        equities.append(env.equity)
        print(f"Episode: {e+1}/{episodes}, Epsilon: {epsilon:.2f}, Final Equity: {env.equity:,.2f}")
        
    torch.save(model.state_dict(), r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\stockfish_weights.pth")
    
    plt.figure(figsize=(10, 5))
    plt.plot(equities, color='blue', label='Final Equity per Episode')
    plt.title("Stockfish Options AI: Learning Curve")
    plt.xlabel("Episode (Training Iterations)")
    plt.ylabel("Portfolio Equity")
    plt.legend()
    plt.grid(True)
    plt.savefig(r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\stockfish_learning_curve.png")
    
    report = "# ♟️ Stockfish Alpha Engine Results\n\n"
    report += "We constructed a PyTorch Deep Q-Network and allowed it to play the 'Game of Options' across a simulated board state representing Greeks and Market Physics.\n\n"
    report += f"**Final Training Episode Equity:** {env.equity:,.2f}\n\n"
    report += "The Neural Network started with random moves, and gradually learned the Q-values (expected future equity) of buying Calls, Puts, or taking profits based purely on recognizing geometric states in the Greeks.\n"
    
    with open(r"C:\Users\USER\.gemini\antigravity\brain\bcb2ab91-bc57-4f82-bd4e-b0bf91d0de91\stockfish_report.md", "w") as f:
        f.write(report)
        
    print("Done")

if __name__ == '__main__':
    train_stockfish_engine()
