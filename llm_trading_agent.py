import json
import os
import time
import requests
import re
import google.generativeai as genai

class LLMTradingAgent:
    def __init__(self, backend='gemini', model_name='gemini-2.5-flash'):
        self.backend = backend
        self.model_name = model_name
        self.system_prompt = """
You are an elite quantitative options trader. You possess independent thinking and deep reasoning capabilities.
At each time step, you are given the current market state, including the asset price, VIX (volatility index), option chain, and your current portfolio.

Your goal is to maximize portfolio value by intelligently trading options.
You must output a JSON object containing your deep reasoning ("chain_of_thought") and your chosen action.
Valid actions:
1. BUY_CALL
2. BUY_PUT
3. CLOSE_ALL
4. HOLD

Format your response EXACTLY as valid JSON:
{
    "chain_of_thought": "I observe that the price has dropped sharply, but VIX is elevated. I expect a bounce. I will buy a Call option.",
    "action_type": "BUY_CALL",
    "strike": 150
}

If your action_type is "CLOSE_ALL" or "HOLD", you may set "strike": null.
"""
        self.mock_mode = False
        if self.backend == 'gemini':
            self._setup_genai()
        elif self.backend == 'ollama':
            print(f"Initialized Ollama backend with model: {self.model_name}")

    def _setup_genai(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("WARNING: GEMINI_API_KEY environment variable not set. Running in MOCK mode to simulate independent thinking.")
            self.mock_mode = True
            return
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name, system_instruction=self.system_prompt)
        
    def _parse_json_robust(self, text):
        try:
            if text.startswith('```json'):
                text = text.strip('```json').strip('```').strip()
            elif text.startswith('```'):
                text = text.strip('```').strip()
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback for local models that might hallucinate extra text around JSON
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
            raise Exception("Could not parse JSON from LLM output")

    def _get_ollama_action(self, prompt):
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": f"{self.system_prompt}\n\n{prompt}",
            "stream": False,
            "format": "json" # Ollama supports forcing JSON format
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=120)
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "")
                return self._parse_json_robust(text)
            except Exception as e:
                print(f"Ollama Error (Attempt {attempt+1}/3): {e}")
                time.sleep(2)
                
        return {
            "chain_of_thought": "Ollama failed to generate a valid response. Holding.",
            "action_type": "HOLD",
            "strike": None
        }
        
    def get_action(self, obs):
        if self.mock_mode:
            time.sleep(1)
            vix = obs['vix']
            if vix > 25:
                return {
                    "chain_of_thought": f"VIX is high at {vix}. Fear is driving premiums up. I'll hold or look for a put.",
                    "action_type": "BUY_PUT",
                    "strike": obs['option_chain'][0]['strike']
                }
            else:
                return {
                    "chain_of_thought": f"VIX is stable at {vix}. The market is steady. I will buy a call slightly out of the money.",
                    "action_type": "BUY_CALL",
                    "strike": obs['option_chain'][-1]['strike']
                }
                
        prompt = f"""
Current Date: {obs['date']}
Current Price: {obs['price']}
Current VIX: {obs['vix']}
Cash: {obs['cash']}
Portfolio Value: {obs['portfolio_value']}
Open Positions: {json.dumps(obs['open_positions'], indent=2)}

Option Chain:
{json.dumps(obs['option_chain'], indent=2)}

Analyze the market and choose an action. Output ONLY a valid JSON object.
"""
        if self.backend == 'ollama':
            return self._get_ollama_action(prompt)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                return self._parse_json_robust(response.text)
            except Exception as e:
                print(f"Gemini Error (Attempt {attempt+1}/{max_retries}): {e}")
                time.sleep(2)
                
        # Fallback action
        return {
            "chain_of_thought": "Failed to generate or parse response. Holding.",
            "action_type": "HOLD",
            "strike": None
        }
