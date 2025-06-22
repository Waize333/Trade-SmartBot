from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod
import exchange
import time

class Strategy(ABC):
    """Abstract base class for trading strategies"""
    @property
    def name(self) -> str:
        """Return strategy name"""
        return self.__class__.__name__
        
    @property
    def description(self) -> str:
        """Return strategy description"""
        return "Base strategy class"
    
    @abstractmethod
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Determine if strategy should execute given the context"""
        pass
        
    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the strategy"""
        pass

class MarketReversalStrategy(Strategy):
    """Strategy that takes a reverse position after hitting SL if market reverses"""
    
    def __init__(self, reversal_percentage: float = 2.0):
        """
        Initialize the strategy with the reversal percentage
        
        Args:
            reversal_percentage: Percentage move in opposite direction to trigger reversal
        """
        self.reversal_percentage = reversal_percentage
        self.stopped_positions = {}  # Track positions that hit stop loss
    
    @property
    def description(self) -> str:
        return f"Takes reverse position if market reverses by {self.reversal_percentage}% after hitting stop loss"
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if position hit SL and market reversed enough"""
        position = context.get('position')
        symbol = context.get('symbol')
        
        if not position or not symbol:
            return False
            
        # If a stop loss was hit
        if context.get('stop_loss_hit', False):
            # Store the position that hit stop loss with its last price
            self.stopped_positions[symbol] = {
                'side': position['side'],
                'exit_price': position['last_price'],
                'timestamp': context.get('timestamp')
            }
            return False  # Not executing immediately, just tracking
        
        # If we previously recorded this symbol hitting SL
        if symbol in self.stopped_positions:
            stopped_data = self.stopped_positions[symbol]
            original_side = stopped_data['side']
            exit_price = stopped_data['exit_price']
            
            # Get current price
            try:
                ticker = exchange.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Check for reversal
                if original_side == 'long':
                    # Price fell (hit SL) and now rising again
                    price_change_pct = ((current_price / exit_price) - 1) * 100
                    return price_change_pct >= self.reversal_percentage
                else:
                    # Price rose (hit SL) and now falling again
                    price_change_pct = ((exit_price / current_price) - 1) * 100
                    return price_change_pct >= self.reversal_percentage
            except Exception as e:
                print(f"Error checking reversal: {e}")
                
        return False
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Take a position in the opposite direction"""
        symbol = context.get('symbol')
        
        if not symbol or symbol not in self.stopped_positions:
            return {}
            
        stopped_data = self.stopped_positions[symbol]
        original_side = stopped_data['side']
        
        # Reverse the position
        new_side = 'sell' if original_side == 'long' else 'buy'
        
        # Remove from tracking
        del self.stopped_positions[symbol]
        
        # Return the action to take
        return {
            'action': 'place_order',
            'symbol': symbol,
            'side': new_side,
            'order_type': 'market',
            'comment': 'Market reversal strategy'
        }

class ThreeStrikeStrategy(Strategy):
    """Strategy that closes all positions after 3 stop losses in a time window"""
    
    def __init__(self, strike_limit: int = 3, time_window: float = 4 * 60 * 60):
        """
        Initialize with configurable strike limit and time window
        
        Args:
            strike_limit: Number of stop losses before action is taken
            time_window: Time window in seconds (default: 4 hours)
        """
        self.strike_limit = strike_limit
        self.time_window = time_window
        self.stop_loss_events = []
    
    @property
    def description(self) -> str:
        return f"Closes all positions after {self.strike_limit} stop losses within {self.time_window / 3600} hours"
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if we've hit the strike limit"""
        # If a stop loss was just hit, record it
        if context.get('stop_loss_hit', False):
            position = context.get('position', {})
            symbol = context.get('symbol', '')
            timestamp = context.get('timestamp', time.time())
            
            # Record this stop loss
            self.stop_loss_events.append({
                'symbol': symbol,
                'timestamp': timestamp,
                'side': position.get('side', ''),
                'size': position.get('size', 0)
            })
            
            print(f"ThreeStrike: SL triggered for {symbol}, " 
                  f"total strikes: {len(self.stop_loss_events)}")
        
        # Clean up old events outside the time window
        current_time = time.time()
        self.stop_loss_events = [
            event for event in self.stop_loss_events 
            if current_time - event['timestamp'] <= self.time_window
        ]
        
        # Check if we've hit the limit
        return len(self.stop_loss_events) >= self.strike_limit
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send instruction to close all positions"""
        return {
            'action': 'close_all_positions',
            'comment': f'Three Strike Protection: {len(self.stop_loss_events)} stop losses triggered within time window'
        }

class TrailingStopWithPartialProfits(Strategy):
    """Strategy that implements trailing stop loss and takes partial profits at specified levels"""
    
    def __init__(self, trailing_distance_pct: float = 1.0, 
                profit_levels: List[Dict[str, float]] = None):
        """
        Initialize strategy
        
        Args:
            trailing_distance_pct: How far price can retrace before stop triggers (percentage)
            profit_levels: List of dictionaries with 'percentage' and 'amount_percentage' keys
                           e.g. [{'percentage': 5, 'amount_percentage': 20}, ...]
        """
        self.trailing_distance_pct = trailing_distance_pct
        self.profit_levels = profit_levels or [
            {'percentage': 5, 'amount_percentage': 20},
            {'percentage': 10, 'amount_percentage': 30},
            {'percentage': 20, 'amount_percentage': 50}
        ]
        self.position_data = {}  # Track position high/low prices and profit taking
        
    @property
    def description(self) -> str:
        return f"Uses {self.trailing_distance_pct}% trailing stop and takes profits at specified levels"
    
    def update_position_tracking(self, symbol: str, position: Dict[str, Any], 
                              current_price: float) -> None:
        """Update tracking data for a position"""
        if symbol not in self.position_data:
            self.position_data[symbol] = {
                'entry_price': position.get('entry_price', current_price),
                'side': position.get('side', 'long'),
                'highest_price': current_price if position.get('side') == 'long' else float('inf'),
                'lowest_price': current_price if position.get('side') == 'short' else 0,
                'profits_taken': []
            }
        else:
            # Update highest/lowest seen price
            if position.get('side') == 'long':
                self.position_data[symbol]['highest_price'] = max(
                    current_price, 
                    self.position_data[symbol]['highest_price']
                )
            else:
                self.position_data[symbol]['lowest_price'] = min(
                    current_price, 
                    self.position_data[symbol]['lowest_price']
                )
    
    def calculate_trailing_stop(self, symbol: str) -> Optional[float]:
        """Calculate trailing stop price based on position data"""
        if symbol not in self.position_data:
            return None
            
        position_data = self.position_data[symbol]
        entry_price = position_data['entry_price']
        
        if position_data['side'] == 'long':
            # Long position - trail below highest price
            highest = position_data['highest_price']
            trail_distance = highest * (self.trailing_distance_pct / 100)
            return highest - trail_distance
        else:
            # Short position - trail above lowest price
            lowest = position_data['lowest_price']
            trail_distance = lowest * (self.trailing_distance_pct / 100)
            return lowest + trail_distance
    
    def check_partial_profits(self, symbol: str, position: Dict[str, Any], 
                           current_price: float) -> Optional[Dict[str, Any]]:
        """Check if we should take partial profits"""
        if symbol not in self.position_data:
            return None
            
        position_data = self.position_data[symbol]
        entry_price = position_data['entry_price']
        profits_taken = position_data['profits_taken']
        
        # Calculate current profit percentage
        if position_data['side'] == 'long':
            profit_pct = ((current_price / entry_price) - 1) * 100
        else:
            profit_pct = ((entry_price / current_price) - 1) * 100
            
        # Check all profit levels
        for level in self.profit_levels:
            target_pct = level['percentage']
            amount_pct = level['amount_percentage']
            
            # If we've hit this profit target and haven't taken profit at this level yet
            if profit_pct >= target_pct and target_pct not in profits_taken:
                profits_taken.append(target_pct)
                position_data['profits_taken'] = profits_taken
                
                # Calculate amount to sell
                position_size = position.get('size', 0)
                amount_to_sell = position_size * (amount_pct / 100)
                
                return {
                    'action': 'partial_close',
                    'symbol': symbol,
                    'amount': amount_to_sell,
                    'profit_pct': target_pct,
                    'comment': f"Taking {amount_pct}% profit at {target_pct}% gain"
                }
                
        return None
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if we should execute either a trailing stop or partial profit taking"""
        position = context.get('position')
        symbol = context.get('symbol')
        
        if not position or not symbol:
            return False
            
        try:
            ticker = exchange.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Update tracking data
            self.update_position_tracking(symbol, position, current_price)
            
            # Check trailing stop
            trailing_stop_price = self.calculate_trailing_stop(symbol)
            if trailing_stop_price:
                position_data = self.position_data[symbol]
                
                if position_data['side'] == 'long' and current_price <= trailing_stop_price:
                    context['trailing_stop_hit'] = True
                    return True
                    
                if position_data['side'] == 'short' and current_price >= trailing_stop_price:
                    context['trailing_stop_hit'] = True
                    return True
                    
            # Check partial profits
            partial_profit = self.check_partial_profits(symbol, position, current_price)
            if partial_profit:
                context['partial_profit'] = partial_profit
                return True
                
            return False
                
        except Exception as e:
            print(f"Error in trailing stop strategy: {e}")
            return False
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute either trailing stop or partial profit taking"""
        if context.get('trailing_stop_hit'):
            symbol = context.get('symbol')
            if symbol and symbol in self.position_data:
                del self.position_data[symbol]  # Clean up tracking
                
            return {
                'action': 'close_position',
                'symbol': context.get('symbol'),
                'comment': 'Trailing stop triggered'
            }
            
        if context.get('partial_profit'):
            return context.get('partial_profit')
            
        return {}

class StopAndReverseStrategy(Strategy):
    """Strategy that opens a position in the opposite direction after a stop loss,
    with a defined take profit percentage"""
    
    def __init__(self, tp_percentage: float = 2.0):
        """
        Initialize the strategy with take profit percentage
        
        Args:
            tp_percentage: Take profit percentage for the reversed position
        """
        self.tp_percentage = tp_percentage
        self.stopped_positions = {}  # Track positions that hit stop loss
    
    @property
    def description(self) -> str:
        return f"Opens a reverse position when SL is hit with {self.tp_percentage}% TP target"
    
    def should_execute(self, context: Dict[str, Any]) -> bool:
        """Check if position hit SL and should open reverse position"""
        position = context.get('position')
        symbol = context.get('symbol')
        
        if not position or not symbol:
            return False
            
        # If a stop loss was hit, we should execute immediately
        if context.get('stop_loss_hit', False):
            print(f"StopAndReverseStrategy: Stop loss hit on {symbol}, preparing to reverse position")
            return True
            
        return False
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Open a position in the opposite direction with TP set"""
        position = context.get('position')
        symbol = context.get('symbol')
        
        if not position or not symbol:
            return {}
            
        # Get the original position side and exit price
        original_side = position.get('side', '')
        exit_price = position.get('last_price')
        
        if not original_side or not exit_price:
            print("Missing position information, cannot reverse position")
            return {}
            
        # Reverse the position
        new_side = 'sell' if original_side == 'long' else 'buy'
        
        # Calculate take profit price based on percentage
        if new_side == 'sell':  # Short position, TP is below entry
            tp_price = exit_price * (1 - (self.tp_percentage / 100))
        else:  # Long position, TP is above entry
            tp_price = exit_price * (1 + (self.tp_percentage / 100))
            
        print(f"StopAndReverseStrategy: Opening {new_side} position at {exit_price} with TP at {tp_price}")
        
        # Return the action to take with TP set
        return {
            'action': 'place_order_with_tp',
            'symbol': symbol,
            'side': new_side,
            'order_type': 'market',
            'take_profit': tp_price,
            'comment': f'Stop and Reverse with {self.tp_percentage}% TP'
        }

# Factory function to get all available strategies
def get_all_strategies() -> List[Strategy]:
    """Return list of all available strategy instances"""
    return [
        MarketReversalStrategy(),
        ThreeStrikeStrategy(),
        TrailingStopWithPartialProfits(),
        StopAndReverseStrategy()
    ]

# Factory function to create strategy by name with parameters
def create_strategy(name: str, params: Dict[str, Any] = None) -> Optional[Strategy]:
    """Create and return a strategy instance by name"""
    params = params or {}
    
    if name == "MarketReversalStrategy":
        return MarketReversalStrategy(
            reversal_percentage=params.get('reversal_percentage', 2.0)
        )
    elif name == "ThreeStrikeStrategy":
        return ThreeStrikeStrategy(
            strike_limit=params.get('strike_limit', 3),
            time_window=params.get('time_window', 4 * 60 * 60)
        )
    elif name == "TrailingStopWithPartialProfits":
        return TrailingStopWithPartialProfits(
            trailing_distance_pct=params.get('trailing_distance_pct', 1.0),
            profit_levels=params.get('profit_levels')
        )
    elif name == "StopAndReverseStrategy":
        return StopAndReverseStrategy(
            tp_percentage=params.get('tp_percentage', 2.0)
        )
    else:
        return None