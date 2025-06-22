import ccxt
import os 
import dotenv

API_SECRET = os.getenv('API_SECRET')
API_KEY = os.getenv('API_KEY')

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'warnOnFetchOpenOrdersWithoutSymbol': False  # Add this line
    },
})
exchange.set_sandbox_mode(True)  # Binance testnet:contentReference[oaicite:7]{index=7}
exchange.load_markets()

def get_available_symbols():
    """
    Get available USDT futures symbols on the exchange, excluding CM symbols.
    """
    try:
        exchange.load_markets()
        usdt_future_symbols = []
        
        # Loop through all markets and filter for USDT futures only
        for symbol, market in exchange.markets.items():
            # Check if it's a future
            is_future = (
                market.get('future', False) or 
                market.get('type') == 'future' or
                market.get('linear', False) or  # For linear futures
                symbol.endswith(('-PERP', '-M', '-W'))  # Common futures suffixes
            )
            
            # Check if it's USDT-based and not containing CM
            is_usdt_settled = '/USDT:' in symbol
            has_cm = 'CM' in symbol
            
            # Only include USDT futures that don't have CM in their name
            if is_future and is_usdt_settled and not has_cm and market.get('active', True):
                usdt_future_symbols.append(symbol)
        
        if not usdt_future_symbols:
            # Fallback method - only get USDT futures, exclude CM
            print("No USDT futures found with primary method, trying fallback...")
            usdt_future_symbols = [s for s in exchange.symbols if '/USDT:' in s and 'CM' not in s]
            
        print(f"Found {len(usdt_future_symbols)} USDT futures symbols (excluding CM)")
        return usdt_future_symbols
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return []

def get_all_open_orders():
    """
    Get all open orders on the exchange.
    """
    try:
        open_orders = exchange.fetch_open_orders()
        return open_orders
    except Exception as e:
        print(f"Error fetching open orders: {e}")
        return []
    
def get_balance():
    """
    Get the balance of the account.
    """
    try:
        balance = exchange.fetch_balance()
        return balance
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None