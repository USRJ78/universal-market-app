import os
import time
import pandas as pd
import matplotlib.pyplot as plt
from autonomous_llm_env import SyntheticOptionsEnv
from llm_trading_agent import LLMTradingAgent

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

def run_simulation():
    # Only run for a short 3-month window in 2023 to save API costs and time
    start_date = '2023-01-01'
    end_date = '2023-04-01'
    
    print("=======================================")
    print("STARTING AUTONOMOUS LLM TRADING AI")
    print(f"Period: {start_date} to {end_date}")
    print("=======================================")
    
    env = SyntheticOptionsEnv(ticker='TSLA', start_date=start_date, end_date=end_date)
    
    # We will pass the API key manually from the text file we read earlier if not in env
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set. Looking for API_KEYS.txt in the current directory.")
        try:
            with open('API_KEYS.txt', 'r') as f:
                content = f.read()
                # we are not fetching actual gemini key here, but user can set it.
                # if they don't have one, this script will fail later in LLMTradingAgent setup unless we mock it.
        except FileNotFoundError:
            pass
            
    agent = LLMTradingAgent(backend='ollama', model_name='phi3')
    
    obs = env.reset()
    done = False
    
    portfolio_history = []
    dates = []
    price_history = []
    
    log_data = []
    
    while not done and obs is not None:
        print(f"\n--- Date: {obs['date']} | TSLA Price: ${obs['price']} | VIX: {obs['vix']} ---")
        
        # 1. Agent Think & Decide
        print("AI is thinking...")
        start_time = time.time()
        action = agent.get_action(obs)
        elapsed = time.time() - start_time
        
        # Log the thought process
        print(f"Agent Action: {action.get('action_type')} | Strike: {action.get('strike')}")
        print(f"Chain of Thought:\n>> {action.get('chain_of_thought')}\n")
        
        log_data.append({
            'date': obs['date'],
            'price': obs['price'],
            'vix': obs['vix'],
            'chain_of_thought': action.get('chain_of_thought'),
            'action_type': action.get('action_type'),
            'strike': action.get('strike'),
            'portfolio_value': obs['portfolio_value']
        })
        
        # 2. Environment Step
        dates.append(obs['date'])
        portfolio_history.append(obs['portfolio_value'])
        price_history.append(obs['price'])
        
        obs, reward, done = env.step(action)
        
        # Avoid hitting API rate limits too hard (15 RPM for free tier)
        time.sleep(4) 
        
    print("\nSimulation Complete!")
    print(f"Final Portfolio Value: ${portfolio_history[-1]}")
    
    # Save the logs so the user can read the independent thoughts
    df_log = pd.DataFrame(log_data)
    df_log.to_csv('llm_agent_thoughts.csv', index=False)
    print("Saved agent thoughts to llm_agent_thoughts.csv")
    
    # Plotting
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(dates, portfolio_history, color='cyan', label='Agent Portfolio')
    ax1.set_ylabel('Portfolio Value ($)', color='cyan')
    ax1.tick_params(axis='y', labelcolor='cyan')
    
    ax2 = ax1.twinx()
    ax2.plot(dates, price_history, color='orange', alpha=0.6, label='TSLA Price')
    ax2.set_ylabel('TSLA Price ($)', color='orange')
    ax2.tick_params(axis='y', labelcolor='orange')
    
    plt.title('Autonomous LLM Trading Agent Performance')
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    
    plt.savefig('llm_agent_performance.png')
    print("Saved performance chart to llm_agent_performance.png")

if __name__ == "__main__":
    run_simulation()
