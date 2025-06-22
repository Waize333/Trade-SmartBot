# Futures Trading Bot (Ft-Bot)

## Description

Ft-Bot is a Python-based trading bot designed for futures trading. It provides a modern graphical user interface (GUI) built with PyQt6 and integrates with various trading strategies to automate trading decisions. The bot supports real-time price tracking, order placement, position management, and strategy execution, making it a powerful tool for traders.

## Features

- **Modern GUI**: A sleek, dark-themed interface for easy navigation.
- **Real-Time Price Tracking**: Displays live price charts using PyQtGraph.
- **Order Management**: Place market and limit orders with stop-loss and take-profit options.
- **Position Management**: View and manage open positions with SL/TP editing.
- **Trading Strategies**: Includes pre-built strategies like:
  - Market Reversal Strategy
  - Three Strike Strategy
  - Trailing Stop with Partial Profits
  - Stop and Reverse Strategy
- **Customizable Parameters**: Configure strategy parameters directly from the GUI.
- **Three Strike Protection**: Automatically closes all positions after three stop-loss events within a defined time window.

---


Install the required Python packages using the `requirements.txt` file:

```
pip install -r requirements.txt
```

### Dependencies

The following Python libraries are used in this project:

* **PyQt6**: For building the graphical user interface.
* **PyQtGraph**: For real-time charting and visualization.
* **ccxt**: For interacting with cryptocurrency exchanges.
* **time**: For time-based operations.
* **typing**: For type hints and annotations.


Configure the Exchange API keys by by creating a .env file.

```
api_key = "your_api_key"
api_secret = "your_api_secret"
```

## Installation

### Prerequisites

- Python 3.8 or higher
- Pip (Python package manager)

### Clone the Repository

```bash
git clone https://github.com/yourusername/Ft-Bot.git
cd Ft-Bot
```
