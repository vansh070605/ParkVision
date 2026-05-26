import os
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.config.config import settings

class ParkingPredictorLSTM(nn.Module):
    def __init__(self, input_dim=1, hidden_dim=32, num_layers=2, output_dim=3):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        out, _ = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :])
        return out

class LSTMPredictorService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = ParkingPredictorLSTM().to(self.device)
        self.weights_path = "weights/lstm_occupancy.pth"
        os.makedirs(os.path.dirname(self.weights_path), exist_ok=True)
        
        if os.path.exists(self.weights_path):
            try:
                self.model.load_state_dict(torch.load(self.weights_path, map_location=self.device))
                print(f"[LSTM] Loaded weights from {self.weights_path}")
            except Exception as e:
                print(f"[LSTM] Error loading weights: {e}. Reinitializing.")
                self._initialize_dummy_weights()
        else:
            self._initialize_dummy_weights()
            
    def _initialize_dummy_weights(self):
        print("[LSTM] Initializing dummy weights...")
        self.model.train()
        optimizer = optim.Adam(self.model.parameters(), lr=0.01)
        criterion = nn.MSELoss()
        
        # Train on 10 steps of random sequences
        for _ in range(10):
            # Batch of 8, Sequence length 12 (1 hour at 5-min intervals), feature dim 1
            inputs = torch.rand(8, 12, 1).to(self.device)
            targets = torch.rand(8, 3).to(self.device) # Predict next 3 steps
            
            optimizer.zero_grad()
            outputs = self.model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
        torch.save(self.model.state_dict(), self.weights_path)
        self.model.eval()
        print(f"[LSTM] Saved initialized weights to {self.weights_path}")

    def predict_occupancy(self, history: list, capacity: int) -> dict:
        """
        Takes a list of recent occupancy counts (e.g. last 12 values at 5-min intervals).
        Returns: Predictions for +15m, +30m, +60m.
        """
        self.model.eval()
        
        # Ensure we have exactly 12 values; pad with average if too short
        seq_len = 12
        if len(history) < seq_len:
            avg_val = sum(history) / len(history) if history else capacity * 0.5
            history = [avg_val] * (seq_len - len(history)) + history
        elif len(history) > seq_len:
            history = history[-seq_len:]
            
        # Normalize history by capacity (0.0 to 1.0)
        norm_history = [float(x) / capacity for x in history]
        
        input_tensor = torch.tensor(norm_history, dtype=torch.float32).view(1, seq_len, 1).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_tensor)
            predictions = outputs.cpu().numpy()[0]
            
        # Scale back to capacity and constrain within [0, capacity]
        predicted_vals = [int(np.clip(p * capacity, 0, capacity)) for p in predictions]
        
        return {
            "prediction_15m": predicted_vals[0],
            "prediction_30m": predicted_vals[1],
            "prediction_60m": predicted_vals[2]
        }

    async def retrain_on_db(self, db_session):
        """
        Queries DB for OccupancyLogs, constructs sequences, and trains the LSTM.
        """
        # We need historical logs
        from app.database.database import OccupancyLog
        
        # Query last 1000 logs
        stmt = select(OccupancyLog).order_by(OccupancyLog.timestamp.desc()).limit(1000)
        result = await db_session.execute(stmt)
        logs = result.scalars().all()
        
        if len(logs) < 20: # Not enough data to train properly, return
            print("[LSTM] Insufficient database logs to train yet.")
            return False
            
        # Reverse to get chronological order
        logs.reverse()
        
        # Group by 5 min intervals or just use the log values directly
        occupancies = [log.occupied_spots / max(1, log.total_capacity) for log in logs]
        
        # Create sequences (X: 12 steps, y: 3 steps)
        seq_len = 12
        pred_len = 3
        X_data = []
        y_data = []
        
        for i in range(len(occupancies) - seq_len - pred_len + 1):
            X_data.append(occupancies[i : i + seq_len])
            y_data.append(occupancies[i + seq_len : i + seq_len + pred_len])
            
        if not X_data:
            return False
            
        X_arr = np.array(X_data, dtype=np.float32).reshape(-1, seq_len, 1)
        y_arr = np.array(y_data, dtype=np.float32)
        
        X_tensor = torch.tensor(X_arr).to(self.device)
        y_tensor = torch.tensor(y_arr).to(self.device)
        
        # Train
        self.model.train()
        optimizer = optim.Adam(self.model.parameters(), lr=0.001)
        criterion = nn.MSELoss()
        
        epochs = 20
        batch_size = 16
        dataset_size = len(X_arr)
        
        for epoch in range(epochs):
            for i in range(0, dataset_size, batch_size):
                batch_X = X_tensor[i : i + batch_size]
                batch_y = y_tensor[i : i + batch_size]
                
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
        torch.save(self.model.state_dict(), self.weights_path)
        self.model.eval()
        print(f"[LSTM] Retrained on DB data. Updated weights saved.")
        return True
