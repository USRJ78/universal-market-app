import torch
import torch.nn as nn
import torch.nn.functional as F

class CorrelationOptionsNN(nn.Module):
    def __init__(self, seq_len=10, geom_input_dim=11, macro_input_dim=2):
        super(CorrelationOptionsNN, self).__init__()
        
        # Fast/Slow Sensory Processing: Handles multi-timeframe returns, ratio Z-scores, and rolling correlations
        self.sensory_layer = nn.Linear(geom_input_dim, 64)
        self.bn_sensory = nn.BatchNorm1d(64)
        
        # Macro context processing: Fear (VIX) and Interest Rates (TNX)
        self.macro_layer = nn.Linear(macro_input_dim, 32)
        self.bn_macro = nn.BatchNorm1d(32)
        
        # Memory / Sequence processing (Hippocampus): Capture temporal correlation breakdowns
        self.lstm = nn.LSTM(
            input_size=64 + 32,
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.40
        )
        
        # Executive Decision Cortex (Prefrontal Cortex): Predict relative strength divergence
        self.prefrontal_cortex = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.40),
            nn.Linear(64, 3) # 3 Output Classes: 0=HOLD, 1=BTC_CALL_ETH_PUT, 2=BTC_PUT_ETH_CALL
        )
        
    def forward(self, geom_seq, macro_seq):
        # geom_seq shape: (batch, seq_len, geom_input_dim)
        # macro_seq shape: (batch, seq_len, macro_input_dim)
        
        batch_size, seq_len, _ = geom_seq.shape
        
        # 1. Process geom features through sensory layer
        g_flat = geom_seq.contiguous().view(-1, geom_seq.shape[-1])
        s_out = F.relu(self.sensory_layer(g_flat))
        s_out = self.bn_sensory(s_out)
        s_out = s_out.view(batch_size, seq_len, -1)
        
        # 2. Process macro features
        m_flat = macro_seq.contiguous().view(-1, macro_seq.shape[-1])
        m_out = F.relu(self.macro_layer(m_flat))
        m_out = self.bn_macro(m_out)
        m_out = m_out.view(batch_size, seq_len, -1)
        
        # 3. Fuse features (Corpus Callosum)
        fused = torch.cat((s_out, m_out), dim=2)
        
        # 4. Process through sequence memory (LSTM)
        lstm_out, (hn, cn) = self.lstm(fused)
        
        # Extract the last state in the sequence
        final_memory = lstm_out[:, -1, :]
        
        # 5. Output decision
        decision = self.prefrontal_cortex(final_memory)
        return decision
