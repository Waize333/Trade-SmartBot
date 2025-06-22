import exchange
import time
from typing import Dict, List, Optional, Union, Any, Callable

class TradeManager:
    def __init__(self):
        """Initialize the trade manager"""
        self.positions = []            # Store open positions
        self.orders = []               # Store open orders
        self.position_strategies = {}  # Store strategies for positions
        
        # Add Three Strike Strategy by default
        from strategy import ThreeStrikeStrategy
        self.default_strategies = [ThreeStrikeStrategy()]
        print("Three Strike Strategy enabled by default")
        
    def get_open_positions(self):
        """Get all open positions with SL/TP info"""
        try:
            # Fetch positions from exchange
            positions = exchange.exchange.fetch_positions()
            
            # Process positions to include SL/TP information
            processed_positions = []
            
            for pos in positions:
                # Skip positions with zero contracts
                if float(pos.get('contracts', 0)) == 0:
                    continue
                    
                symbol = pos.get('symbol', '')
                
                # Fetch open orders to find SL/TP for this position
                open_orders = exchange.exchange.fetch_open_orders(symbol)
                
                # Initialize SL/TP prices as None
                sl_price = None
                tp_price = None
                
                # Look for SL/TP orders
                for order in open_orders:
                    order_type = order.get('type', '').lower()
                    
                    # Check various properties that might indicate a stop loss
                    if ('stop' in order_type and 'profit' not in order_type) or order_type == 'stop_loss':
                        sl_price = (order.get('stopPrice') or 
                                   order.get('triggerPrice') or 
                                   order.get('info', {}).get('stopPrice'))
                        
                    # Check various properties that might indicate a take profit
                    elif 'take_profit' in order_type or order_type == 'take_profit':
                        tp_price = (order.get('stopPrice') or 
                                   order.get('triggerPrice') or 
                                   order.get('price') or
                                   order.get('info', {}).get('takeProfitPrice'))
                
                # Create position object with SL/TP info
                processed_pos = {
                    'symbol': symbol,
                    'side': pos.get('side', ''),
                    'size': float(pos.get('contracts', 0)),
                    'entry_price': float(pos.get('entryPrice', 0)),
                    'pnl': float(pos.get('unrealizedPnl', 0)),
                    'sl_price': sl_price,
                    'tp_price': tp_price
                }
                
                processed_positions.append(processed_pos)
                
            return processed_positions
        except Exception as e:
            print(f"Error getting open positions: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get a specific position by symbol"""
        try:
            for position in self.get_open_positions():
                if position.get('symbol') == symbol:
                    return position
            return None
        except Exception as e:
            print(f"Error getting position for {symbol}: {e}")
            return None
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   amount: float, price: Optional[float] = None, leverage: int = None,
                   stop_loss_pct: Optional[float] = None, take_profit_pct: Optional[float] = None,
                   strategies: List[Any] = None, reduce_only: bool = False) -> bool:
        """Place an order on the exchange with optional strategies and risk management"""
        try:
            # Set leverage if provided
            if leverage is not None:
                self.set_leverage(symbol, leverage)
            
            # Check if we're in hedge mode
            is_hedge_mode = self.get_position_mode()
            
            # Get current market price if not provided
            market_price = price
            if not market_price or order_type.lower() == 'market':
                ticker = exchange.exchange.fetch_ticker(symbol)
                market_price = ticker['last']
            
            # Create params with proper settings based on mode
            params = {}
            if reduce_only:
                params['reduceOnly'] = True
                
            # In hedge mode, need to specify positionSide
            if is_hedge_mode:
                position_side = "LONG" if side.lower() == 'buy' else "SHORT"
                params['positionSide'] = position_side
                print(f"Hedge mode: Opening {position_side} position")
                
            # Place the main order
            if order_type.lower() == 'market':
                if side.lower() == 'buy':
                    order = exchange.exchange.create_market_buy_order(
                        symbol, amount, params=params
                    )
                else:
                    order = exchange.exchange.create_market_sell_order(
                        symbol, amount, params=params
                    )
            else:
                if not price:
                    print("Price required for limit orders")
                    return False
                    
                if side.lower() == 'buy':
                    order = exchange.exchange.create_limit_buy_order(
                        symbol, amount, price, params=params
                    )
                else:
                    order = exchange.exchange.create_limit_sell_order(
                        symbol, amount, price, params=params
                    )
                    
            if order:
                print(f"Order placed: {order}")
                # Store the order
                self.orders.append(order)
                
                # Calculate and place stop loss and take profit orders if needed
                if stop_loss_pct or take_profit_pct:
                    # Wait briefly for the order to be processed
                    time.sleep(1)
                    
                    # Try to get the position
                    position = self.get_position(symbol)
                    
                    if position:
                        entry_price = position.get('entry_price', market_price)
                        pos_side = position.get('side', side.lower())
                        
                        # Calculate SL/TP prices
                        if pos_side == 'long':
                            sl_price = entry_price * (1 - stop_loss_pct/100) if stop_loss_pct else None
                            tp_price = entry_price * (1 + take_profit_pct/100) if take_profit_pct else None
                        else:  # short
                            sl_price = entry_price * (1 + stop_loss_pct/100) if stop_loss_pct else None
                            tp_price = entry_price * (1 - take_profit_pct/100) if take_profit_pct else None
                        
                        # Place stop loss order
                        if sl_price:
                            try:
                                self._place_stop_loss(symbol, position, sl_price)
                                print(f"Stop Loss set at {sl_price}")
                            except Exception as e:
                                print(f"Error setting stop loss: {e}")
                        
                        # Place take profit order
                        if tp_price:
                            try:
                                self._place_take_profit(symbol, position, tp_price)
                                print(f"Take Profit set at {tp_price}")
                            except Exception as e:
                                print(f"Error setting take profit: {e}")
                
                # Apply strategies to the position
                all_strategies = []
                if strategies:
                    all_strategies.extend(strategies)
                    
                all_strategies.extend(self.default_strategies)
                    
                strategy_names = [s.__class__.__name__ for s in all_strategies]
                print(f"Applying strategies: {', '.join(strategy_names)}")
                
                if not hasattr(self, 'position_strategies'):
                    self.position_strategies = {}
                    
                self.position_strategies[symbol] = all_strategies
                
                return True
            else:
                print("Order placement failed")
                return False
                
        except Exception as e:
            print(f"Error placing order: {e}")
            return False

    def place_order_with_tp(self, symbol, side, order_type, amount=None, price=None, take_profit=None):
        """Place an order with take profit"""
        try:
            # Place the main order
            order = self.place_order(symbol, side, order_type, amount, price)
            if not order or 'id' not in order:
                print(f"Failed to place main order for {symbol}")
                return None
                
            # Wait a short time to ensure order is processed
            time.sleep(1)
            
            # Get the position
            positions = exchange.exchange.fetch_positions([symbol])
            position = next((p for p in positions if float(p.get('contracts', 0)) != 0), None)
            
            if not position:
                print(f"Could not find position for {symbol} after placing order")
                return order
                
            # Get position details
            position_side = position.get('side', '').lower()
            position_size = abs(float(position.get('contracts', 0)))
            
            # Set the take profit
            if take_profit:
                # TP side is opposite of position side
                tp_side = 'sell' if position_side == 'long' else 'buy'
                
                # Create TP order params for a market stop order
                tp_params = {
                    'stopPrice': take_profit,
                    'reduceOnly': True,
                    'closePosition': 'true', # Use string 'true' for consistency if required by exchange
                }
                # If in hedge mode, you might need to add 'positionSide' to tp_params here
                # Example:
                # if self.get_position_mode(): # Assuming get_position_mode() is available and efficient
                #     tp_params['positionSide'] = "LONG" if position_side == "short" else "SHORT" # This needs careful check for TP logic
                                                                                              # For TP, positionSide is same as original position being closed.
                                                                                              # 'LONG' for closing a long, 'SHORT' for closing a short.
                
                try:
                    # Use 'market' type with stopPrice in params, as per the suggested solution
                    # This effectively creates a stop-market order for take profit.
                    tp_order_type = 'market' 
                    
                    tp_order = exchange.exchange.create_order(
                        symbol=symbol,
                        type=tp_order_type, # 'market'
                        side=tp_side,
                        amount=position_size,
                        price=None, # Market orders don't have a limit price; stopPrice is in params.
                        params=tp_params
                    )
                    
                    print(f"Take profit set at {take_profit} for {symbol}")
                    
                except Exception as e:
                    print(f"Error setting take profit: {e}")
            
            return order
            
        except Exception as e:
            print(f"Error in place_order_with_tp: {e}")
            return None

    def _place_stop_loss(self, symbol: str, position: Dict[str, Any], price: float) -> bool:
        """Place a stop loss order for a position"""
        try:
            side = position.get('side', '')
            amount = position.get('size', 0)
            
            sl_side = 'sell' if side == 'long' else 'buy'
            is_hedge_mode = self.get_position_mode()
            
            params = {
                'stopPrice': price,
                'reduceOnly': True,
                'closePosition': 'true' 
            }
            
            if is_hedge_mode:
                # For SL/TP, positionSide should match the side of the position being closed/reduced.
                position_side_param = 'LONG' if side == 'long' else 'SHORT'
                params['positionSide'] = position_side_param
                print(f"Hedge mode: Setting SL for {position_side_param} position at {price}")
            
            # Attempt 1: 'market' type with stopPrice in params (user's suggested pattern)
            try:
                print(f"Placing SL order: symbol={symbol}, type='market', side={sl_side}, amount={amount}, price=None, params={params}")
                order = exchange.exchange.create_order(
                    symbol, 'market', sl_side, amount, None, params
                )
                print(f"Stop loss order (type market with stopPrice) placed: {order}")
                return True
            except Exception as e_market:
                print(f"SL attempt with type 'market' failed: {e_market}")

                # Attempt 2: Try with 'STOP_MARKET'
                try:
                    print(f"Retrying SL with type 'STOP_MARKET', params={params}")
                    order = exchange.exchange.create_order(
                        symbol, 'STOP_MARKET', sl_side, amount, None, params
                    )
                    print(f"Stop loss order (type STOP_MARKET) placed: {order}")
                    return True
                except Exception as e_sm:
                    print(f"SL attempt with type 'STOP_MARKET' failed: {e_sm}")
                    
                    # Attempt 3: Try with 'STOP' (as stop-market)
                    try:
                        print(f"Retrying SL with type 'STOP', price=None, params={params}")
                        order = exchange.exchange.create_order(
                            symbol, 'STOP', sl_side, amount, None, params # price=None for stop-market
                        )
                        print(f"Stop loss order (type STOP) placed: {order}")
                        return True
                    except Exception as e_s:
                        print(f"SL attempt with type 'STOP' failed: {e_s}")
                        
                        # Attempt 4: Direct API call (existing fallback)
                        try:
                            binance_symbol = symbol.split(':')[0].replace('/', '')
                            direct_params = {
                                'symbol': binance_symbol,
                                'side': sl_side.upper(),
                                'type': 'STOP_MARKET',
                                'stopPrice': str(price),
                                'quantity': str(amount),
                                'reduceOnly': 'true',
                                'timeInForce': 'GTC'
                            }
                            if is_hedge_mode and 'positionSide' in params:
                                direct_params['positionSide'] = params['positionSide']
                            
                            print(f"Trying direct API call for SL with params: {direct_params}")
                            result = exchange.exchange.fapiPrivatePostOrder(direct_params)
                            print(f"SL order placed with direct API: {result}")
                            return True
                        except Exception as e_direct:
                            print(f"Direct API SL attempt failed: {e_direct}")
                            print(f"All SL attempts failed.")
                            return False
        except Exception as e_outer:
            print(f"Error placing stop loss: {e_outer}")
            return False

    def _place_take_profit(self, symbol: str, position: Dict[str, Any], price: float) -> bool:
        try:
            side = position.get('side', '')
            amount = position.get('size', 0)
            
            tp_side = 'sell' if side == 'long' else 'buy'
            is_hedge_mode = self.get_position_mode()
            
            params = {
                'stopPrice': price, # This 'price' is the take_profit_price
                'reduceOnly': True,
                'closePosition': 'true'
            }
            
            if is_hedge_mode:
                # For SL/TP, positionSide should match the side of the position being closed/reduced.
                position_side_param = 'LONG' if side == 'long' else 'SHORT'
                params['positionSide'] = position_side_param
                print(f"Hedge mode: Setting TP for {position_side_param} position at {price}")

            # Attempt 1: 'market' type with stopPrice in params (user's suggested pattern)
            try:
                print(f"Placing TP order: symbol={symbol}, type='market', side={tp_side}, amount={amount}, price=None, params={params}")
                order = exchange.exchange.create_order(
                    symbol, 'market', tp_side, amount, None, params
                )
                print(f"Take profit order (type market with stopPrice) placed: {order}")
                return True
            except Exception as e_market:
                print(f"TP attempt with type 'market' failed: {e_market}")

                # Attempt 2: Try with 'TAKE_PROFIT_MARKET'
                try:
                    print(f"Retrying TP with type 'TAKE_PROFIT_MARKET', params={params}")
                    order = exchange.exchange.create_order(
                        symbol, 'TAKE_PROFIT_MARKET', tp_side, amount, None, params
                    )
                    print(f"Take profit order (type TAKE_PROFIT_MARKET) placed: {order}")
                    return True
                except Exception as e_tpm:
                    print(f"TP attempt with type 'TAKE_PROFIT_MARKET' failed: {e_tpm}")
                    
                    # Attempt 3: Try with 'TAKE_PROFIT' (as take_profit_limit)
                    try:
                        print(f"Retrying TP with type 'TAKE_PROFIT', price={price}, params={params}")
                        order = exchange.exchange.create_order(
                            symbol, 'TAKE_PROFIT', tp_side, amount, price, params # price is the limit price for TP
                        )
                        print(f"Take profit order (type TAKE_PROFIT) placed: {order}")
                        return True
                    except Exception as e_tp:
                        print(f"TP attempt with type 'TAKE_PROFIT' failed: {e_tp}")

                        # Attempt 4: Direct API call (existing fallback)
                        try:
                            binance_symbol = symbol.split(':')[0].replace('/', '')
                            direct_params = {
                                'symbol': binance_symbol,
                                'side': tp_side.upper(),
                                'type': 'TAKE_PROFIT_MARKET',
                                'stopPrice': str(price),
                                'quantity': str(amount),
                                'reduceOnly': 'true',
                                'timeInForce': 'GTC'
                            }
                            if is_hedge_mode and 'positionSide' in params:
                                direct_params['positionSide'] = params['positionSide']
                            
                            print(f"Trying direct API call for TP with params: {direct_params}")
                            result = exchange.exchange.fapiPrivatePostOrder(direct_params)
                            print(f"TP order placed with direct API: {result}")
                            return True
                        except Exception as e_direct:
                            print(f"Direct API TP attempt failed: {e_direct}")
                            print(f"All TP attempts failed.")
                            return False
        except Exception as e_outer:
            print(f"Error placing take profit: {e_outer}")
            return False

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order"""
        try:
            # Find the order symbol
            order_symbol = None
            for order in self.orders:
                if order.get('id') == order_id:
                    order_symbol = order.get('symbol')
                    break
            
            if not order_symbol:
                # Try to find order in exchange
                open_orders = exchange.get_all_open_orders()
                for order in open_orders:
                    if order.get('id') == order_id:
                        order_symbol = order.get('symbol')
                        break
            
            if not order_symbol:
                print(f"Could not find order with ID: {order_id}")
                return False
            
            # Cancel the order
            result = exchange.exchange.cancel_order(order_id, order_symbol)
            if result:
                print(f"Order {order_id} cancelled")
                # Remove from local tracking
                self.orders = [o for o in self.orders if o.get('id') != order_id]
                return True
            else:
                print(f"Failed to cancel order {order_id}")
                return False
                
        except Exception as e:
            print(f"Error cancelling order: {e}")
            return False
    
    def close_position(self, symbol: str) -> bool:
        """Close an open position"""
        try:
            # Get the position details
            position = None
            for pos in self.get_open_positions():
                if pos.get('symbol') == symbol:
                    position = pos
                    break
            
            if not position:
                print(f"No open position found for {symbol}")
                return False
            
            print(f"Found position to close: {position}")
            side = position.get('side', '')
            amount = position.get('size', 0)
            
            # Check if we're in hedge mode
            is_hedge_mode = self.get_position_mode()
            
            # Determine the closing side (opposite of position side)
            close_side = 'sell' if side == 'long' else 'buy'
            
            print(f"Closing {side} position with {close_side} order, amount: {amount}")
            
            # Create params with proper settings based on mode
            params = {}
            
            if is_hedge_mode:
                # In hedge mode: DO NOT use reduceOnly, but MUST specify positionSide
                position_side = position.get('positionSide', '').upper()
                if not position_side:
                    position_side = 'LONG' if side == 'long' else 'SHORT'
                params['positionSide'] = position_side
                print(f"Hedge mode: Closing {position_side} position")
            else:
                # In one-way mode: Use reduceOnly
                params['reduceOnly'] = True
            
            # Place the order
            if close_side == 'buy':
                order = exchange.exchange.create_market_buy_order(
                    symbol, amount, params=params
                )
            else:
                order = exchange.exchange.create_market_sell_order(
                    symbol, amount, params=params
                )
                
            print(f"Position closed with order: {order}")
            return True
            
        except Exception as e:
            print(f"Error closing position: {e}")
            return False

    def close_all_positions(self) -> bool:
        """Close all open positions"""
        try:
            success = True
            for position in self.get_open_positions():
                symbol = position.get('symbol')
                if symbol:
                    result = self.close_position(symbol)
                    success = success and result
                    print(f"Closed position for {symbol}: {'Success' if result else 'Failed'}")
            return success
        except Exception as e:
            print(f"Error closing all positions: {e}")
            return False

    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol before placing an order"""
        try:
            # Correct way to set leverage in CCXT
            result = exchange.exchange.set_leverage(leverage, symbol)
            print(f"Leverage set to {leverage}x for {symbol}")
            return True
        except Exception as e:
            print(f"Error setting leverage: {e}")
            return False

    def get_position_mode(self) -> bool:
        """
        Get current position mode
        Returns True if in Hedge Mode, False if in One-Way Mode
        """
        try:
            result = exchange.exchange.fapiPrivateGetPositionSideDual()
            print(f"Current position mode: {result}")
            return result.get('dualSidePosition', False)
        except Exception as e:
            print(f"Error checking position mode: {e}")
            return False

    def set_position_mode(self, hedge_mode: bool) -> bool:
        """
        Set position mode for Binance Futures
        
        Args:
            hedge_mode: True for hedge mode (dual positions), False for one-way mode
        
        Returns:
            bool: Success or failure
        """
        try:
            # Convert boolean to string as required by Binance API
            mode_str = 'true' if hedge_mode else 'false'
            
            # Set position mode
            result = exchange.exchange.fapiPrivatePostPositionSideDual({'dualSidePosition': mode_str})
            
            mode_name = "Hedge Mode" if hedge_mode else "One-Way Mode"
            print(f"Position mode set to {mode_name}: {result}")
            return True
        except Exception as e:
            # If error says "No need to change position side", it's already set correctly
            if "No need to change" in str(e):
                mode_name = "Hedge Mode" if hedge_mode else "One-Way Mode"
                print(f"Position mode already set to {mode_name}")
                return True
            print(f"Error setting position mode: {e}")
            return False

    def check_strategies(self):
        """Check if any strategies should be executed"""
        if not hasattr(self, 'position_strategies'):
            return
            
        for symbol, strategies in self.position_strategies.items():
            try:
                # Get current position
                position = self.get_position(symbol)
                if not position:
                    continue
                    
                # Build context
                context = {
                    'symbol': symbol,
                    'position': position,
                    'timestamp': time.time()
                }
                
                # Check each strategy
                for strat in strategies:
                    if strat.should_execute(context):
                        # Execute strategy
                        result = strat.execute(context)
                        
                        if result and 'action' in result:
                            action = result['action']
                            
                            if action == 'place_order':
                                self.place_order(
                                    result['symbol'],
                                    result['side'],
                                    result.get('order_type', 'market'),
                                    position['size'],  # Use same size as original
                                    None,  # Market price
                                    None,  # Use default leverage
                                )
                            elif action == 'close_position':
                                self.close_position(result['symbol'])
                            elif action == 'partial_close':
                                if hasattr(self, 'close_partial'):
                                    self.close_partial(result['symbol'], result['amount'])
                            elif action == 'close_all_positions':
                                self.close_all_positions()
                                
                            print(f"Strategy action executed: {result.get('comment')}")
                        
            except Exception as e:
                print(f"Error checking strategies for {symbol}: {e}")

    def check_stop_loss_hit(self, symbol: str, position: Dict[str, Any], current_price: float):
        """Check if a stop loss has been hit for a position"""
        # Get position details
        side = position.get('side', '')
        entry_price = position.get('entry_price', 0)
        stop_loss = position.get('stop_loss', 0)
        
        if not stop_loss or stop_loss <= 0:
            return False
            
        stop_loss_hit = False
        
        # Check if stop loss is hit
        if side == 'long' and current_price <= stop_loss:
            stop_loss_hit = True
        elif side == 'short' and current_price >= stop_loss:
            stop_loss_hit = True
            
        if stop_loss_hit:
            # Notify strategies
            context = {
                'symbol': symbol,
                'position': position,
                'stop_loss_hit': True,
                'timestamp': time.time()
            }
            
            for strategy in self.default_strategies:
                if strategy.should_execute(context):
                    result = strategy.execute(context)
                    if result and result.get('action') == 'close_all_positions':
                        self.close_all_positions()
                        print(f"All positions closed due to strategy: {result.get('comment')}")
                        
            return True
            
        return False

    def set_position_sltp(self, symbol, stop_loss_price=None, take_profit_price=None):
        """Set Stop Loss and Take Profit for an existing position"""
        try:
            # Get position details directly from the exchange to ensure accuracy
            positions = exchange.exchange.fetch_positions([symbol])
            if not positions or len(positions) == 0:
                print(f"No open position found for {symbol}")
                return False
                
            position = positions[0]  # Use the first position matching the symbol
            
            # Determine position side and size
            position_size = float(position.get('contracts', 0))
            if position_size == 0:
                print(f"Position size is zero for {symbol}")
                return False
                
            # Determine if long or short (different exchanges represent this differently)
            side = ''
            if 'side' in position:
                side = position['side'].lower()
            else:
                # Alternative determination based on position size
                side = 'long' if position_size > 0 else 'short'
                
            print(f"Position details: Symbol={symbol}, Side={side}, Size={position_size}")
            
            # Cancel existing SL/TP orders for this symbol
            try:
                open_orders = exchange.exchange.fetch_open_orders(symbol)
                print(f"Found {len(open_orders)} open orders for {symbol}")
                for order in open_orders:
                    order_type = order.get('type', '').lower()
                    if 'stop' in order_type or 'take_profit' in order_type:
                        print(f"Cancelling existing {order_type} order ID: {order['id']}")
                        exchange.exchange.cancel_order(order['id'], symbol)
            except Exception as e:
                print(f"Error cancelling existing orders: {e}")
                # Continue anyway as this shouldn't stop new orders
            
            # Place new SL order if provided
            if stop_loss_price is not None:
                # For long positions, stop loss is a sell; for short positions, it's a buy
                sl_side = 'sell' if side == 'long' else 'buy'
                
                # Prepare parameters for stop loss order
                order_type = 'stop_market'  # Use exchange-specific order type 
                
                # Create more robust parameters that work with most exchanges
                sl_params = {
                    'stopPrice': stop_loss_price,
                    'reduceOnly': True,
                    'triggerPrice': stop_loss_price,  # Some exchanges use this name
                    'stopLossPrice': stop_loss_price,  # Some exchanges use this name
                    'type': order_type  # Explicitly set type in params too
                }
                
                try:
                    print(f"Creating SL order: {symbol} {order_type} {sl_side} {abs(position_size)}")
                    print(f"SL params: {sl_params}")
                    
                    sl_order = exchange.exchange.create_order(
                        symbol=symbol,
                        type=order_type,
                        side=sl_side,
                        amount=abs(position_size),
                        price=None,  # Price is null for market orders
                        params=sl_params
                    )
                    
                    print(f"SL order created successfully: {sl_order.get('id', 'Unknown ID')}")
                except Exception as e:
                    print(f"Error setting stop loss: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Continue to try setting TP even if SL fails
            
            # Place new TP order if provided
            if take_profit_price is not None:
                # For long positions, take profit is a sell; for short positions, it's a buy
                tp_side = 'sell' if side == 'long' else 'buy'
                
                # Prepare parameters for take profit order
                order_type = 'take_profit_market'  # Use exchange-specific order type
                
                # Create more robust parameters that work with most exchanges
                tp_params = {
                    'stopPrice': take_profit_price,
                    'reduceOnly': True,
                    'triggerPrice': take_profit_price,  # Some exchanges use this name
                    'takeProfitPrice': take_profit_price,  # Some exchanges use this name
                    'type': order_type  # Explicitly set type in params too
                }
                
                try:
                    print(f"Creating TP order: {symbol} {order_type} {tp_side} {abs(position_size)}")
                    print(f"TP params: {tp_params}")
                    
                    tp_order = exchange.exchange.create_order(
                        symbol=symbol,
                        type=order_type,
                        side=tp_side,
                        amount=abs(position_size),
                        price=None,  # Price is null for market orders
                        params=tp_params
                    )
                    
                    print(f"TP order created successfully: {tp_order.get('id', 'Unknown ID')}")
                except Exception as e:
                    print(f"Error setting take profit: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Continue and return partial success
            
            return True
            
        except Exception as e:
            print(f"Error in set_position_sltp: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

