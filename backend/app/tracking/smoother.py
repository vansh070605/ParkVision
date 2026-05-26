from collections import deque
from app.config.config import settings

class TemporalSmoother:
    def __init__(self, window_size: int = None, occupied_threshold: float = None, empty_threshold: float = None):
        self.window_size = window_size or settings.SMOOTHING_WINDOW
        self.occupied_threshold = occupied_threshold or settings.OCCUPIED_THRESHOLD
        self.empty_threshold = empty_threshold or settings.EMPTY_THRESHOLD
        
        # Maps spot_id -> deque of booleans (occupied=True, empty=False)
        self.spot_history = {}
        # Maps spot_id -> current stable occupancy state (bool)
        self.spot_states = {}

    def update(self, spot_id: int, instant_occupied: bool) -> bool:
        """
        Updates the history for a spot and returns its smoothed occupancy state.
        """
        if spot_id not in self.spot_history:
            self.spot_history[spot_id] = deque(maxlen=self.window_size)
            # Default state is empty
            self.spot_states[spot_id] = False
            
        self.spot_history[spot_id].append(instant_occupied)
        
        history = list(self.spot_history[spot_id])
        num_occupied = sum(1 for x in history if x)
        ratio_occupied = num_occupied / len(history)
        
        current_state = self.spot_states[spot_id]
        
        # Apply threshold rules to change state
        if not current_state and ratio_occupied >= self.occupied_threshold:
            # Change from Empty -> Occupied
            self.spot_states[spot_id] = True
        elif current_state and (1.0 - ratio_occupied) >= self.empty_threshold:
            # Change from Occupied -> Empty
            self.spot_states[spot_id] = False
            
        return self.spot_states[spot_id]
        
    def reset(self):
        self.spot_history.clear()
        self.spot_states.clear()
