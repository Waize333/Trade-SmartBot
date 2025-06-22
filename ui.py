import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QComboBox, QPushButton, QTableWidget, 
                           QTableWidgetItem, QLineEdit, QGridLayout, QGroupBox,
                           QHeaderView, QDoubleSpinBox, QMessageBox, QSlider, QCheckBox,
                           QListWidget, QListWidgetItem, QFormLayout, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt
from PyQt6 import QtGui, QtCore
import exchange
import tradeManager
import strategy
import time

# Install PyQtGraph if not already installed: pip install pyqtgraph
import pyqtgraph as pg

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futures Trading Bot")
        self.setGeometry(100, 100, 1200, 800)
        self.trade_manager = tradeManager.TradeManager()
        
        self.initUI()
        self.loadData()
        
    def initUI(self):
        # Apply a modern dark theme stylesheet
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background: #1e1e1e;
            }
            QTabBar::tab {
                background: #444;
                color: #fff;
                padding: 10px;
                border: 1px solid #444;
                border-radius: 5px;
            }
            QTabBar::tab:selected {
                background: #2b2b2b;
                border-bottom: 2px solid #00aaff;
            }
            QPushButton {
                background-color: #444;
                color: #fff;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QLabel {
                color: #ffffff;
            }
            QComboBox {
                background-color: #444;
                color: #fff;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QLineEdit {
                background-color: #444;
                color: #fff;
                border: 1px solid #555;
                border-radius: 5px;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
                background-color: #2b2b2b;
                color: #00aaff;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: #fff;
                border: 1px solid #555;
            }
            QHeaderView::section {
                background-color: #444;
                color: #fff;
                padding: 5px;
                border: 1px solid #555;
            }
        """)

        # Create main tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create individual tabs
        self.trade_tab = QWidget()
        self.orders_tab = QWidget()
        self.position_tab = QWidget()

        # Add tabs to widget with icons
        self.tabs.addTab(self.trade_tab, QtGui.QIcon("icons/trade.png"), "Trade")
        self.tabs.addTab(self.orders_tab, QtGui.QIcon("icons/orders.png"), "Orders")
        self.tabs.addTab(self.position_tab, QtGui.QIcon("icons/positions.png"), "Positions")

        # Add strike status button with modern styling
        self.strike_status_button = QPushButton("Three Strike Status: 0/3")
        self.strike_status_button.clicked.connect(self.showStrikeStatus)
        self.strike_status_button.setStyleSheet("""
            QPushButton {
                background-color: green;
                color: white;
                font-weight: bold;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #00cc00;
            }
        """)

        # Set up each tab
        self.setupTradeTab()
        self.setupOrdersTab()
        self.setupPositionTab()


    
    def setupTradeTab(self):
        layout = QVBoxLayout()

        # Add a real-time price chart
        self.price_chart = pg.PlotWidget()
        self.price_chart.setBackground('#1e1e1e')
        self.price_chart.setTitle("Real-Time Price Chart", color="#ffffff", size="12pt")
        self.price_chart.setLabel('left', 'Price', color="#ffffff")
        self.price_chart.setLabel('bottom', 'Time', color="#ffffff")
        self.price_chart.showGrid(x=True, y=True)
        layout.addWidget(self.price_chart)
        
        # Symbol selection with search
        symbol_group = QGroupBox("Symbol Selection")
        symbol_layout = QVBoxLayout()
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.symbol_search = QLineEdit()
        self.symbol_search.setPlaceholderText("Type to search symbols...")
        self.symbol_search.textChanged.connect(self.filterSymbols)
        search_layout.addWidget(self.symbol_search)
        symbol_layout.addLayout(search_layout)
        
        # Symbol dropdown
        dropdown_layout = QHBoxLayout()
        dropdown_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.currentTextChanged.connect(self.symbolChanged)
        dropdown_layout.addWidget(self.symbol_combo)
        symbol_layout.addLayout(dropdown_layout)
        
        # Live price display
        price_layout = QHBoxLayout()
        price_layout.addWidget(QLabel("Current Price:"))
        self.current_price_label = QLabel("---")
        price_layout.addWidget(self.current_price_label)
        self.refresh_price_button = QPushButton("Refresh")
        self.refresh_price_button.clicked.connect(self.updateCurrentPrice)
        price_layout.addWidget(self.refresh_price_button)
        symbol_layout.addLayout(price_layout)
        
        symbol_group.setLayout(symbol_layout)
        layout.addWidget(symbol_group)
        
        # Balance information
        balance_group = QGroupBox("Account Balance")
        balance_layout = QGridLayout()
        self.balance_label = QLabel("Loading...")
        balance_layout.addWidget(self.balance_label, 0, 0)
        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)
        
        # Strategy section (moved here after symbol selection)
        strat_group = self.setupStrategySection()
        layout.addWidget(strat_group)
        
        # Order placement controls
        order_group = QGroupBox("Place Order")
        order_layout = QFormLayout()
        
        # Order side (buy/sell)
        self.order_side_combo = QComboBox()
        self.order_side_combo.addItems(["Buy", "Sell"])
        order_layout.addRow("Side:", self.order_side_combo)
        
        # Order type
        self.order_type_combo = QComboBox()
        self.order_type_combo.addItems(["Market", "Limit"])
        order_layout.addRow("Type:", self.order_type_combo)
        
        # Price input (for limit orders)
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.000001, 1000000)
        self.price_input.setDecimals(8)
        price_input_row = QHBoxLayout()
        price_input_row.addWidget(self.price_input)
        self.use_market_button = QPushButton("Use Market")
        self.use_market_button.clicked.connect(self.useMarketPrice)
        price_input_row.addWidget(self.use_market_button)
        order_layout.addRow("Price:", price_input_row)
        
        # Margin and leverage
        self.margin_input = QDoubleSpinBox()
        self.margin_input.setRange(1, 10000)
        self.margin_input.setValue(100)
        self.margin_input.valueChanged.connect(self.updateTotal)
        order_layout.addRow("Margin (USDT):", self.margin_input)
        
        leverage_layout = QHBoxLayout()
        self.leverage_slider = QDoubleSpinBox()
        self.leverage_slider.setRange(1, 125)
        self.leverage_slider.setValue(10)
        self.leverage_slider.valueChanged.connect(self.updateTotal)
        leverage_layout.addWidget(self.leverage_slider)
        self.leverage_value = QLabel("10x")
        leverage_layout.addWidget(self.leverage_value)
        order_layout.addRow("Leverage:", leverage_layout)
        
        # Total amount display
        self.total_amount = QLabel("1000 USDT")
        order_layout.addRow("Total Position:", self.total_amount)
        
        # Stop Loss and Take Profit
        self.enable_sltp_checkbox = QCheckBox("Enable Stop Loss/Take Profit")
        self.enable_sltp_checkbox.toggled.connect(self.toggleSLTP)
        order_layout.addRow(self.enable_sltp_checkbox)
        
        # SL/TP inputs
        self.sl_input = QDoubleSpinBox()
        self.sl_input.setRange(0.1, 50)
        self.sl_input.setValue(5)
        self.sl_input.setSuffix("%")
        self.sl_input.setEnabled(False)
        order_layout.addRow("Stop Loss (%):", self.sl_input)
        
        self.tp_input = QDoubleSpinBox()
        self.tp_input.setRange(0.1, 200)
        self.tp_input.setValue(10)
        self.tp_input.setSuffix("%")
        self.tp_input.setEnabled(False)
        order_layout.addRow("Take Profit (%):", self.tp_input)
        
        # Place order button
        self.place_order_button = QPushButton("Place Order")
        self.place_order_button.clicked.connect(self.placeOrder)
        order_layout.addRow("", self.place_order_button)
        
        order_group.setLayout(order_layout)
        layout.addWidget(order_group)
        layout.addStretch()
        
        self.trade_tab.setLayout(layout)
        
        # Store original symbols list
        self.all_symbols = []
    
    def setupStrategySection(self):
        strategy_group = QGroupBox("Trading Strategies")
        strategy_layout = QVBoxLayout()
        
        # Selected symbol info (uses the current trading tab symbol)
        symbol_info = QHBoxLayout()
        symbol_info.addWidget(QLabel("Selected Symbol:"))
        self.strategy_symbol_label = QLabel("No symbol selected")
        self.strategy_symbol_label.setStyleSheet("font-weight: bold;")
        symbol_info.addWidget(self.strategy_symbol_label)
        strategy_layout.addLayout(symbol_info)
        
        # Enable strategy checkbox
        self.strategy_enabled = QCheckBox("Enable Strategy for This Symbol")
        self.strategy_enabled.toggled.connect(self.toggleStrategyControls)
        strategy_layout.addWidget(self.strategy_enabled)
        
        # Strategy controls container (initially hidden)
        self.strategy_controls = QWidget()
        self.strategy_controls.setVisible(False)
        strategy_controls_layout = QVBoxLayout()
        self.strategy_controls.setLayout(strategy_controls_layout)
        
        # Strategy selection
        strategy_select_layout = QHBoxLayout()
        strategy_select_layout.addWidget(QLabel("Select Strategy:"))
        self.strategy_combo = QComboBox()
        
        # Get all strategies
        all_strategies = strategy.get_all_strategies()
        
        # Add strategies to combo box (excluding ThreeStrike which is always active)
        for strat in all_strategies:
            if strat.name != "ThreeStrikeStrategy":  # Don't show ThreeStrike in dropdown
                self.strategy_combo.addItem(strat.name, strat.name)
        
        self.strategy_combo.currentIndexChanged.connect(self.strategyChanged)
        strategy_select_layout.addWidget(self.strategy_combo)
        strategy_controls_layout.addLayout(strategy_select_layout)
        
        # Strategy description
        self.strategy_description = QLabel()
        self.strategy_description.setWordWrap(True)
        strategy_controls_layout.addWidget(self.strategy_description)
        
        # Strategy parameters widget
        self.strategy_params_widget = QWidget()
        self.strategy_params_layout = QFormLayout()
        self.strategy_params_widget.setLayout(self.strategy_params_layout)
        strategy_controls_layout.addWidget(self.strategy_params_widget)
        
        # Apply strategy button
        self.apply_strategy_button = QPushButton("Apply Strategy")
        self.apply_strategy_button.clicked.connect(self.applyStrategy)
        strategy_controls_layout.addWidget(self.apply_strategy_button)
        
        # Remove strategy button
        self.remove_strategy_button = QPushButton("Remove Strategy")
        self.remove_strategy_button.clicked.connect(self.removeStrategy)
        self.remove_strategy_button.setVisible(False)  # Initially hidden
        strategy_controls_layout.addWidget(self.remove_strategy_button)
        
        # Add the controls container to main layout
        strategy_layout.addWidget(self.strategy_controls)
        
        # Active strategies section
        strategy_layout.addWidget(QLabel("Active Strategies:"))
        self.active_strategies_list = QListWidget()
        strategy_layout.addWidget(self.active_strategies_list)
        
        # ThreeStrike status (always active)
        three_strike_info = QLabel("ThreeStrike Strategy is always active")
        three_strike_info.setStyleSheet("color: blue;")
        strategy_layout.addWidget(three_strike_info)
        
        # Add the strike status button here too for convenience
        strategy_layout.addWidget(self.strike_status_button)
        
        strategy_group.setLayout(strategy_layout)
        
        # Initial update of strategy description and params
        self.strategyChanged()
        
        # Initialize dictionary to track strategy-symbol mappings
        self.symbol_strategy_map = {}
        
        return strategy_group

    def toggleStrategyControls(self, enabled):
        """Show/hide strategy controls based on checkbox state"""
        symbol = self.symbol_combo.currentText()
        
        if enabled and not symbol:
            # If enabled but no symbol selected
            self.strategy_enabled.setChecked(False)
            self.showError("Please select a symbol first")
            return
        
        self.strategy_controls.setVisible(enabled)
        
        if enabled:
            # Update symbol label
            self.strategy_symbol_label.setText(symbol)
            
            # Check if this symbol already has a strategy
            if symbol in self.symbol_strategy_map:
                strat_info = self.symbol_strategy_map[symbol]
                # Set the combo to the active strategy
                index = self.strategy_combo.findData(strat_info['name'])
                if index >= 0:
                    self.strategy_combo.setCurrentIndex(index)
                    
                # Show the remove button
                self.remove_strategy_button.setVisible(True)
                self.apply_strategy_button.setText("Update Strategy")
            else:
                # No strategy for this symbol yet
                self.remove_strategy_button.setVisible(False)
                self.apply_strategy_button.setText("Apply Strategy")
        else:
            # Reset symbol label when disabled
            self.strategy_symbol_label.setText("No symbol selected")

    def applyStrategy(self):
        """Apply the configured strategy to the currently selected symbol"""
        symbol = self.symbol_combo.currentText()
        strategy_name = self.strategy_combo.currentData()
        
        if not strategy_name or not symbol:
            return
        
        # Get parameters based on selected strategy
        params = {}
        
        if strategy_name == "MarketReversalStrategy":
            params['reversal_percentage'] = self.reversal_pct_input.value()
            
        elif strategy_name == "TrailingStopWithPartialProfits":
            params['trailing_distance_pct'] = self.trailing_pct_input.value()
            
        elif strategy_name == "StopAndReverseStrategy":
            params['tp_percentage'] = self.tp_pct_input.value()
        
        # Create the strategy
        strat = strategy.create_strategy(strategy_name, params)
        
        if not strat:
            self.showError(f"Failed to create strategy {strategy_name}")
            return
            
        # Store strategy info
        self.symbol_strategy_map[symbol] = {
            'name': strategy_name,
            'strategy': strat,
            'params': params
        }
        
        # Update active strategies list
        self.updateActiveStrategiesList()
        
        # Update UI
        self.remove_strategy_button.setVisible(True)
        self.apply_strategy_button.setText("Update Strategy")
        
        QMessageBox.information(
            self,
            "Strategy Applied",
            f"Strategy '{strategy_name}' has been applied to {symbol}"
        )

    def symbolChanged(self, symbol):
        """Update price and strategy controls when symbol selection changes"""
        if symbol:
            self.updateCurrentPrice()
            
            # Update strategy symbol label if strategy is enabled
            if self.strategy_enabled.isChecked():
                self.strategy_symbol_label.setText(symbol)
                
                # Update strategy controls based on whether this symbol has a strategy
                if symbol in self.symbol_strategy_map:
                    strat_info = self.symbol_strategy_map[symbol]
                    # Set the combo to the active strategy
                    index = self.strategy_combo.findData(strat_info['name'])
                    if index >= 0:
                        self.strategy_combo.setCurrentIndex(index)
                        
                    # Show the remove button
                    self.remove_strategy_button.setVisible(True)
                    self.apply_strategy_button.setText("Update Strategy")
                else:
                    # No strategy for this symbol yet
                    self.remove_strategy_button.setVisible(False)
                    self.apply_strategy_button.setText("Apply Strategy")

    def removeStrategy(self):
        """Remove strategy for the current symbol"""
        symbol = self.symbol_combo.currentText()
        
        if not symbol or symbol not in self.symbol_strategy_map:
            self.showError(f"No active strategy for {symbol}")
            return
            
        # Remove from map
        del self.symbol_strategy_map[symbol]
        
        # Update list
        self.updateActiveStrategiesList()
        
        # Update UI
        self.remove_strategy_button.setVisible(False)
        self.apply_strategy_button.setText("Apply Strategy")
        
        QMessageBox.information(
            self,
            "Strategy Removed",
            f"Strategy for {symbol} has been removed"
        )

    def updateActiveStrategiesList(self):
        """Update the list of active strategies"""
        self.active_strategies_list.clear()
        
        for symbol, strat_info in self.symbol_strategy_map.items():
            item_text = f"{symbol}: {strat_info['name']}"
            
            # Add parameter info if available
            if strat_info['params']:
                params_str = ", ".join(f"{k}={v}" for k, v in strat_info['params'].items())
                item_text += f" ({params_str})"
                
            self.active_strategies_list.addItem(item_text)

    def strategyChanged(self):
        """Update UI when strategy selection changes"""
        # Clear existing params widgets
        while self.strategy_params_layout.count():
            item = self.strategy_params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        strategy_name = self.strategy_combo.currentData()
        if not strategy_name:
            return
            
        # Create a temporary instance to get description and default params
        temp_strategy = strategy.create_strategy(strategy_name)
        if not temp_strategy:
            return
            
        # Update description
        self.strategy_description.setText(temp_strategy.description)
        
        # Add strategy-specific parameters
        if strategy_name == "MarketReversalStrategy":
            # Add reversal percentage parameter
            self.reversal_pct_input = QDoubleSpinBox()
            self.reversal_pct_input.setRange(0.1, 20.0)
            self.reversal_pct_input.setSingleStep(0.1)
            self.reversal_pct_input.setValue(2.0)
            self.strategy_params_layout.addRow("Reversal %:", self.reversal_pct_input)
            
        elif strategy_name == "TrailingStopWithPartialProfits":
            # Add trailing stop parameter
            self.trailing_pct_input = QDoubleSpinBox()
            self.trailing_pct_input.setRange(0.1, 10.0)
            self.trailing_pct_input.setSingleStep(0.1)
            self.trailing_pct_input.setValue(1.0)
            self.strategy_params_layout.addRow("Trailing %:", self.trailing_pct_input)
            
        elif strategy_name == "StopAndReverseStrategy":
            # Add take profit percentage parameter
            self.tp_pct_input = QDoubleSpinBox()
            self.tp_pct_input.setRange(0.1, 20.0)
            self.tp_pct_input.setSingleStep(0.1)
            self.tp_pct_input.setValue(2.0)
            self.strategy_params_layout.addRow("Take Profit %:", self.tp_pct_input)

    def getActiveStrategy(self):
        """Get the configured strategy based on UI settings"""
        if not self.strategy_enabled.isChecked():
            return None
            
        strategy_name = self.strategy_combo.currentData()
        if not strategy_name:
            return None
            
        # Get parameters based on selected strategy
        params = {}
        
        if strategy_name == "MarketReversalStrategy":
            params['reversal_percentage'] = self.reversal_pct_input.value()
            
        elif strategy_name == "TrailingStopWithPartialProfits":
            params['trailing_distance_pct'] = self.trailing_pct_input.value()
            
        elif strategy_name == "StopAndReverseStrategy":
            params['tp_percentage'] = self.tp_pct_input.value()
        
        # Create and return the strategy
        return strategy.create_strategy(strategy_name, params)

    def updateLeverage(self, value):
        """Update the leverage value label when slider is moved"""
        self.leverage_value.setText(f"{value}x")
        self.updateTotal()
    
    def updateTotal(self):
        """Calculate and update the total amount (margin × leverage)"""
        margin = self.margin_input.value()
        leverage = self.leverage_slider.value()
        total = margin * leverage
        self.total_amount.setText(f"{total:.2f} USDT")
    
    def updateStrategyParams(self):
        """Show/hide strategy parameters based on selection"""
        selected_items = self.strategy_list.selectedItems()
        selected_names = [item.text() for item in selected_items]
        
        # Show parameters widget if any strategies are selected
        if selected_items:
            self.strategy_params_widget.show()
        else:
            self.strategy_params_widget.hide()
            
        # Show/hide specific parameters
        has_reversal = "MarketReversalStrategy" in selected_names
        has_trailing = "TrailingStopWithPartialProfits" in selected_names
        
        self.reversal_percentage.setVisible(has_reversal)
        self.strategy_params_layout.labelForField(self.reversal_percentage).setVisible(has_reversal)
        
        self.trailing_stop_distance.setVisible(has_trailing)
        self.strategy_params_layout.labelForField(self.trailing_stop_distance).setVisible(has_trailing)
        self.profit_levels_button.setVisible(has_trailing)
        self.strategy_params_layout.labelForField(self.profit_levels_button).setVisible(has_trailing)

    def configureProfitLevels(self):
        """Open dialog to configure profit taking levels"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Profit Levels")
        layout = QVBoxLayout()
        
        # Table for profit levels
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Profit %", "Amount %"])
        
        # Default values
        default_levels = [
            {'percentage': 5, 'amount_percentage': 20},
            {'percentage': 10, 'amount_percentage': 30},
            {'percentage': 20, 'amount_percentage': 50}
        ]
        
        # Fill table
        table.setRowCount(len(default_levels))
        for i, level in enumerate(default_levels):
            profit_spin = QDoubleSpinBox()
            profit_spin.setRange(0.5, 100.0)
            profit_spin.setValue(level['percentage'])
            
            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(1.0, 100.0)
            amount_spin.setValue(level['amount_percentage'])
            
            table.setCellWidget(i, 0, profit_spin)
            table.setCellWidget(i, 1, amount_spin)
        
        # Add/remove buttons
        button_layout = QHBoxLayout()
        add_button = QPushButton("Add Level")
        remove_button = QPushButton("Remove Selected")
        
        def add_row():
            row = table.rowCount()
            table.insertRow(row)
            
            profit_spin = QDoubleSpinBox()
            profit_spin.setRange(0.5, 100.0)
            profit_spin.setValue(5.0)
            
            amount_spin = QDoubleSpinBox()
            amount_spin.setRange(1.0, 100.0)
            amount_spin.setValue(20.0)
            
            table.setCellWidget(row, 0, profit_spin)
            table.setCellWidget(row, 1, amount_spin)
        
        def remove_row():
            selected = table.selectedIndexes()
            rows = set()
            for index in selected:
                rows.add(index.row())
            
            # Remove rows in reverse order to avoid index shifting
            for row in sorted(rows, reverse=True):
                table.removeRow(row)
        
        add_button.clicked.connect(add_row)
        remove_button.clicked.connect(remove_row)
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        
        # OK/Cancel buttons
        dialog_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        dialog_buttons.accepted.connect(dialog.accept)
        dialog_buttons.rejected.connect(dialog.reject)
        
        layout.addWidget(QLabel("Configure profit taking levels:"))
        layout.addWidget(table)
        layout.addLayout(button_layout)
        layout.addWidget(dialog_buttons)
        
        dialog.setLayout(layout)
        
        # Store the table for later access if dialog is accepted
        self.profit_levels_table = table
        
        dialog.exec()

    def placeOrder(self):
        try:
            symbol = self.symbol_combo.currentText()
            order_type = self.order_type_combo.currentText().lower()
            side = self.order_side_combo.currentText().lower()
            
            # Get current price
            try:
                ticker = exchange.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
            except Exception as e:
                self.showError(f"Failed to fetch current price: {e}")
                return
            
            # Calculate quantity
            margin = self.margin_input.value()
            leverage = self.leverage_slider.value()
            position_value = margin * leverage
            quantity = position_value / current_price
            
            price = self.price_input.value() if order_type == "limit" else None
            
            # Get stop loss and take profit percentages ONLY if enabled
            sl_pct = None
            tp_pct = None
            
            if self.enable_sltp_checkbox.isChecked():
                sl_pct = self.sl_input.value()
                tp_pct = self.tp_input.value()
                print(f"SL/TP enabled - Using SL: {sl_pct}%, TP: {tp_pct}%")
            else:
                print("SL/TP disabled - No stop loss or take profit will be set")
                
            # Place the order with all the parameters
            result = self.trade_manager.place_order(
                symbol, side, order_type, quantity, price, leverage,
                stop_loss_pct=sl_pct, take_profit_pct=tp_pct,
                reduce_only=False
            )
            
            if result:
                QMessageBox.information(self, "Order Placed", "Order placed successfully!")
                self.loadOrders()
                self.loadBalance()
            else:
                self.showError("Failed to place order")
        except Exception as e:
            self.showError(f"Failed to place order: {e}")

    def showStrikeStatus(self):
        """Show the current Three Strike Strategy status"""
        try:
            # Get the strategy from trade manager
            three_strike = None
            for strategy in self.trade_manager.default_strategies:
                if strategy.__class__.__name__ == "ThreeStrikeStrategy":
                    three_strike = strategy
                    break
                    
            if three_strike:
                # Clean up old events
                current_time = time.time()
                three_strike.stop_loss_events = [
                    event for event in three_strike.stop_loss_events 
                    if current_time - event['timestamp'] <= three_strike.time_window
                ]
                
                # Count recent events
                strike_count = len(three_strike.stop_loss_events)
                
                # Get details about each strike
                details = []
                for i, event in enumerate(three_strike.stop_loss_events):
                    time_ago = (current_time - event['timestamp']) / 60  # Minutes
                    details.append(f"Strike {i+1}: {event['symbol']} ({time_ago:.1f} min ago)")
                
                # Format the message
                if details:
                    details_str = "\n".join(details)
                    message = f"Three Strike Status: {strike_count}/3\n\n{details_str}\n\nResets in: {(three_strike.time_window - (current_time - three_strike.stop_loss_events[0]['timestamp']) if strike_count > 0 else 0) / 60:.1f} minutes"
                else:
                    message = "No stop losses recorded in the last 4 hours"
                    
                QMessageBox.information(self, "Three Strike Status", message)
            else:
                QMessageBox.information(self, "Three Strike Status", "Three Strike Strategy not enabled")
                
            # Update the status button
            self.updateStrikeStatus()
        except Exception as e:
            self.showError(f"Error showing strike status: {e}")

    def resetStrikes(self):
        """Reset the strike counter"""
        try:
            for strategy in self.trade_manager.default_strategies:
                if strategy.__class__.__name__ == "ThreeStrikeStrategy":
                    strategy.stop_loss_events = []
                    QMessageBox.information(self, "Strikes Reset", "Strike counter has been reset to 0")
                    self.updateStrikeStatus()
                    return
                    
            QMessageBox.information(self, "Three Strike Status", "Three Strike Strategy not enabled")
        except Exception as e:
            self.showError(f"Error resetting strikes: {e}")

    def updateStrikeStatus(self):
        """Update the strike status button appearance"""
        try:
            # Find the Three Strike Strategy
            three_strike = None
            for strategy in self.trade_manager.default_strategies:
                if strategy.__class__.__name__ == "ThreeStrikeStrategy":
                    three_strike = strategy
                    break
                    
            if three_strike:
                # Clean up old events
                current_time = time.time()
                three_strike.stop_loss_events = [
                    event for event in three_strike.stop_loss_events 
                    if current_time - event['timestamp'] <= three_strike.time_window
                ]
                
                # Count recent events
                strike_count = len(three_strike.stop_loss_events)
                
                # Update button text and color
                self.strike_status_button.setText(f"Three Strike Status: {strike_count}/3")
                
                if strike_count == 0:
                    self.strike_status_button.setStyleSheet("background-color: green;")
                elif strike_count == 1:
                    self.strike_status_button.setStyleSheet("background-color: yellow; color: black;")
                elif strike_count == 2:
                    self.strike_status_button.setStyleSheet("background-color: orange;")
                else:
                    self.strike_status_button.setStyleSheet("background-color: red;")
        except Exception as e:
            print(f"Error updating strike status: {e}")

    def setupOrdersTab(self):
        layout = QVBoxLayout()
        
        # Open orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(7)
        self.orders_table.setHorizontalHeaderLabels(["Symbol", "Side", "Type", "Price", "Quantity", "Time", "Cancel"])
        self.orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        refresh_button = QPushButton("Refresh Orders")
        refresh_button.clicked.connect(self.loadOrders)
        
        layout.addWidget(QLabel("Open Orders"))
        layout.addWidget(self.orders_table)
        layout.addWidget(refresh_button)
        
        self.orders_tab.setLayout(layout)
    
    def setupPositionTab(self):
        layout = QVBoxLayout()
        
        # Open positions table
        self.positions_table = QTableWidget()
        # Add columns for SL/TP buttons
        self.positions_table.setColumnCount(9)  # Increased from 7 to 9
        self.positions_table.setHorizontalHeaderLabels([
            "Symbol", "Side", "Size", "Entry Price", "PnL", "ROI %", "SL/TP", "Edit", "Close"
        ])
        self.positions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        refresh_button = QPushButton("Refresh Positions")
        refresh_button.clicked.connect(self.loadPositions)
        
        layout.addWidget(QLabel("Open Positions"))
        layout.addWidget(self.positions_table)
        layout.addWidget(refresh_button)
        
        self.position_tab.setLayout(layout)
    
    def loadData(self):
        # Load available symbols
        self.loadSymbols()
        # Load account balance
        self.loadBalance()
        # Load open orders
        self.loadOrders()
        # Load positions
        self.loadPositions()
    
    def loadSymbols(self):
        try:
            symbols = exchange.get_available_symbols()
            self.all_symbols = symbols  # Store all symbols for filtering
            self.symbol_combo.clear()
            self.symbol_combo.addItems(symbols)
            # Select first symbol and update price
            if symbols:
                self.symbol_combo.setCurrentIndex(0)
                self.updateCurrentPrice()
        except Exception as e:
            self.showError(f"Failed to load symbols: {e}")
    
    def filterSymbols(self, search_text):
        """Filter symbols based on search text"""
        self.symbol_combo.clear()
        filtered_symbols = [s for s in self.all_symbols if search_text.lower() in s.lower()]
        self.symbol_combo.addItems(filtered_symbols)
    
    def updateCurrentPrice(self):
        """Fetch and display the current price for the selected symbol"""
        try:
            symbol = self.symbol_combo.currentText()
            if not symbol:
                return
                
            ticker = exchange.exchange.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                price = ticker['last']
                self.current_price_label.setText(f"{price:.8f}")
                
                # Format the price with appropriate precision
                if price < 0.1:
                    formatted_price = f"{price:.8f}"
                elif price < 1:
                    formatted_price = f"{price:.6f}"
                elif price < 1000:
                    formatted_price = f"{price:.4f}"
                else:
                    formatted_price = f"{price:.2f}"
                    
                self.current_price_label.setText(formatted_price)
                
                # Set font color based on price change
                if 'change' in ticker:
                    if ticker['change'] > 0:
                        self.current_price_label.setStyleSheet("color: green;")
                    elif ticker['change'] < 0:
                        self.current_price_label.setStyleSheet("color: red;")
                    else:
                        self.current_price_label.setStyleSheet("")
            else:
                self.current_price_label.setText("Price unavailable")
        except Exception as e:
            self.current_price_label.setText("Error")
            print(f"Error updating price: {e}")
    
    def useMarketPrice(self):
        """Set the price input to current market price"""
        try:
            symbol = self.symbol_combo.currentText()
            ticker = exchange.exchange.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                self.price_input.setValue(ticker['last'])
        except Exception as e:
            self.showError(f"Failed to fetch current price: {e}")
    
    def loadBalance(self):
        try:
            balance = exchange.get_balance()
            if balance:
                balance_text = f"Total Balance: {balance.get('total', {}).get('USDT', 0)} USDT<br>"
                balance_text += f"Available: {balance.get('free', {}).get('USDT', 0)} USDT<br>"
                balance_text += f"In Use: {balance.get('used', {}).get('USDT', 0)} USDT"
                self.balance_label.setText(balance_text)
        except Exception as e:
            self.showError(f"Failed to load balance: {e}")
    
    def loadOrders(self):
        try:
            orders = exchange.get_all_open_orders()
            self.orders_table.setRowCount(len(orders))
            
            for row, order in enumerate(orders):
                self.orders_table.setItem(row, 0, QTableWidgetItem(order.get('symbol', '')))
                self.orders_table.setItem(row, 1, QTableWidgetItem(order.get('side', '')))
                self.orders_table.setItem(row, 2, QTableWidgetItem(order.get('type', '')))
                self.orders_table.setItem(row, 3, QTableWidgetItem(str(order.get('price', ''))))
                self.orders_table.setItem(row, 4, QTableWidgetItem(str(order.get('amount', ''))))
                self.orders_table.setItem(row, 5, QTableWidgetItem(str(order.get('datetime', ''))))
                
                cancel_button = QPushButton("Cancel")
                cancel_button.clicked.connect(lambda checked, order_id=order.get('id'): self.cancelOrder(order_id))
                self.orders_table.setCellWidget(row, 6, cancel_button)
        except Exception as e:
            self.showError(f"Failed to load orders: {e}")
    
    def loadPositions(self):
        try:
            positions = self.trade_manager.get_open_positions()
            self.positions_table.setRowCount(len(positions))
            
            for row, pos in enumerate(positions):
                # Get position data
                symbol = pos.get('symbol', '')
                side = pos.get('side', '')
                size = pos.get('size', 0)
                entry_price = pos.get('entry_price', 0)
                pnl = pos.get('pnl', 0)
                
                # Get SL/TP status if available
                has_sl = pos.get('sl_price') is not None
                has_tp = pos.get('tp_price') is not None
                
                # Calculate ROI
                roi = 0
                if entry_price > 0 and size > 0:
                    # For long positions: (Current PnL / (Entry Price * Size)) * 100
                    position_value = entry_price * size
                    if position_value > 0:
                        roi = (pnl / position_value) * 100
                
                # Add to table
                self.positions_table.setItem(row, 0, QTableWidgetItem(symbol))
                self.positions_table.setItem(row, 1, QTableWidgetItem(side))
                self.positions_table.setItem(row, 2, QTableWidgetItem(str(size)))
                self.positions_table.setItem(row, 3, QTableWidgetItem(str(entry_price)))
                self.positions_table.setItem(row, 4, QTableWidgetItem(str(pnl)))
                
                # Add ROI with formatting
                roi_item = QTableWidgetItem(f"{roi:.2f}%")
                if roi > 0:
                    roi_item.setForeground(QtGui.QColor("green"))
                elif roi < 0:
                    roi_item.setForeground(QtGui.QColor("red"))
                self.positions_table.setItem(row, 5, roi_item)
                
                # Add SL/TP status indicator
                sl_tp_status = ""
                if has_sl and has_tp:
                    sl_tp_status = "SL & TP"
                elif has_sl:
                    sl_tp_status = "SL only"
                elif has_tp:
                    sl_tp_status = "TP only"
                else:
                    sl_tp_status = "None"
                    
                self.positions_table.setItem(row, 6, QTableWidgetItem(sl_tp_status))
                
                # Add edit SL/TP button
                edit_button = QPushButton("Edit SL/TP")
                edit_button.clicked.connect(self.createEditSLTPCallback(symbol, pos))
                self.positions_table.setCellWidget(row, 7, edit_button)
                
                # Close position button
                close_button = QPushButton("Close")
                close_button.setProperty("symbol", symbol)
                close_button.clicked.connect(self.createClosePositionCallback(symbol))
                self.positions_table.setCellWidget(row, 8, close_button)
        except Exception as e:
            self.showError(f"Failed to load positions: {e}")

    def createClosePositionCallback(self, symbol):
        """Create a callback function for the close button that correctly passes the symbol"""
        def callback():
            print(f"Closing position for {symbol}")  # Debug print
            self.closePosition(symbol)
        return callback
    
    def createEditSLTPCallback(self, symbol, position):
        """Create a callback function for editing SL/TP of a position"""
        def callback():
            self.editPositionSLTP(symbol, position)
        return callback

    def editPositionSLTP(self, symbol, position):
        """Open a dialog to edit Stop Loss and Take Profit for an open position"""
        try:
            # Get current market price for reference
            ticker = exchange.exchange.fetch_ticker(symbol)
            current_price = ticker['last'] if ticker and 'last' in ticker else 0
            
            # Create dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit SL/TP for {symbol}")
            layout = QVBoxLayout()
            
            # Position info
            position_info = QLabel(f"Symbol: {symbol}\nSide: {position.get('side', '')}\n" +
                                  f"Entry Price: {position.get('entry_price', 0)}\n" +
                                  f"Current Price: {current_price}")
            layout.addWidget(position_info)
            
            # Form for SL/TP
            form_layout = QFormLayout()
            
            # Calculate default values (5% for SL, 10% for TP from current price)
            entry_price = position.get('entry_price', current_price)
            side = position.get('side', '').lower()
            
            # Default SL/TP values based on position side
            if side == 'long':
                default_sl = entry_price * 0.95  # 5% below entry for long
                default_tp = entry_price * 1.10  # 10% above entry for long
            else:  # short
                default_sl = entry_price * 1.05  # 5% above entry for short
                default_tp = entry_price * 0.90  # 10% below entry for short
            
            # Get existing SL/TP values if available
            existing_sl = position.get('sl_price')
            existing_tp = position.get('tp_price')
            
            # Stop Loss input
            sl_enable = QCheckBox("Enable Stop Loss")
            sl_enable.setChecked(existing_sl is not None)
            form_layout.addRow(sl_enable)
            
            sl_price = QDoubleSpinBox()
            sl_price.setRange(0.000001, 1000000)
            sl_price.setDecimals(8)
            sl_price.setValue(existing_sl if existing_sl else default_sl)
            sl_price.setEnabled(existing_sl is not None)
            form_layout.addRow("Stop Loss Price:", sl_price)
            
            # Connect checkbox to enable/disable SL input
            sl_enable.toggled.connect(sl_price.setEnabled)
            
            # Take Profit input
            tp_enable = QCheckBox("Enable Take Profit")
            tp_enable.setChecked(existing_tp is not None)
            form_layout.addRow(tp_enable)
            
            tp_price = QDoubleSpinBox()
            tp_price.setRange(0.000001, 1000000)
            tp_price.setDecimals(8)
            tp_price.setValue(existing_tp if existing_tp else default_tp)
            tp_price.setEnabled(existing_tp is not None)
            form_layout.addRow("Take Profit Price:", tp_price)
            
            # Connect checkbox to enable/disable TP input
            tp_enable.toggled.connect(tp_price.setEnabled)
            
            layout.addLayout(form_layout)
            
            # Add warning about market conditions
            warning = QLabel("Warning: SL/TP orders may be affected by market volatility.")
            warning.setStyleSheet("color: #FF6700;")
            layout.addWidget(warning)
            
            # Buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
            )
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)
            
            dialog.setLayout(layout)
            
            # Execute dialog
            if dialog.exec():
                # Process the result
                sl_price_value = sl_price.value() if sl_enable.isChecked() else None
                tp_price_value = tp_price.value() if tp_enable.isChecked() else None
                
                # Debug logging
                print(f"Setting SL/TP for {symbol}:")
                print(f"  SL: {sl_price_value}")
                print(f"  TP: {tp_price_value}")
                
                # Apply SL/TP to position
                result = self.trade_manager.set_position_sltp(
                    symbol, sl_price_value, tp_price_value
                )
                
                if result:
                    QMessageBox.information(self, "SL/TP Updated", 
                                           f"Stop Loss and Take Profit updated for {symbol}")
                    
                    # Ensure positions are fully refreshed from the exchange
                    time.sleep(1)  # Give exchange time to process the orders
                    self.loadPositions()  # Refresh positions
                else:
                    self.showError("Failed to update SL/TP - Check console for details")
                    
        except Exception as e:
            self.showError(f"Error setting SL/TP: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def cancelOrder(self, order_id):
        try:
            result = self.trade_manager.cancel_order(order_id)
            if result:
                QMessageBox.information(self, "Order Cancelled", "Order has been cancelled.")
                self.loadOrders()
        except Exception as e:
            self.showError(f"Failed to cancel order: {e}")
    
    def closePosition(self, symbol):
        """Close an open position by its symbol"""
        try:
            print(f"Attempting to close position for {symbol}")  # Debug print
            result = self.trade_manager.close_position(symbol)
            if result:
                QMessageBox.information(self, "Position Closed", f"Position for {symbol} closed successfully!")
                self.loadPositions()  # Refresh the positions display
                self.loadBalance()    # Update account balance
            else:
                self.showError(f"Failed to close position for {symbol}")
        except Exception as e:
            self.showError(f"Error closing position: {e}")
    
    def showError(self, message):
        QMessageBox.critical(self, "Error", message)
    
    def checkStrategies(self):
        """Check if any active strategies should execute"""
        # Get all open positions
        positions = self.trade_manager.get_open_positions()
        current_time = time.time()
        
        # Always check ThreeStrike strategy first (global strategy)
        three_strike = next(
            (s for s in self.trade_manager.default_strategies 
            if s.__class__.__name__ == "ThreeStrikeStrategy"), 
            None
        )
        
        # Process each position
        for position in positions:
            symbol = position.get('symbol', '')
            if not symbol:
                continue
                
            # Build context for strategy evaluation
            context = {
                'position': position,
                'symbol': symbol,
                'timestamp': current_time
            }
            
            # Check ThreeStrike strategy first (always active)
            if three_strike and three_strike.should_execute(context):
                action = three_strike.execute(context)
                if action and action.get('action') == 'close_all_positions':
                    print("ThreeStrike strategy triggered - closing all positions")
                    self.closeAllPositions()
                    # Show alert
                    QMessageBox.warning(
                        self,
                        "Three Strike Protection Activated",
                        "Three stop losses have been hit within the time window. "
                        "All positions have been closed for protection."
                    )
                    return  # Exit early as all positions are being closed
            
            # Check symbol-specific strategy if one exists
            if symbol in self.symbol_strategy_map:
                active_strategy = self.symbol_strategy_map[symbol]['strategy']
                
                if active_strategy and active_strategy.should_execute(context):
                    action = active_strategy.execute(context)
                    
                    if not action:
                        continue
                        
                    action_type = action.get('action')
                    
                    # Handle different action types
                    if action_type == 'place_order':
                        self.trade_manager.place_order(
                            symbol=action.get('symbol'),
                            side=action.get('side'),
                            order_type=action.get('order_type', 'market'),
                            amount=action.get('amount')
                        )
                        
                    elif action_type == 'place_order_with_tp':
                        self.trade_manager.place_order_with_tp(
                            symbol=action.get('symbol'),
                            side=action.get('side'),
                            order_type=action.get('order_type', 'market'),
                            amount=action.get('amount'),
                            take_profit=action.get('take_profit')
                        )
                        
                    # Handle other action types as needed

    def closeAllPositions(self):
        """Close all open positions"""
        positions = self.trade_manager.get_open_positions()
        
        for position in positions:
            symbol = position.get('symbol', '')
            if symbol:
                try:
                    self.trade_manager.close_position(symbol)
                    print(f"Closed position for {symbol}")
                except Exception as e:
                    print(f"Error closing position for {symbol}: {e}")
                    
        # Refresh UI
        self.loadPositions()
        self.loadBalance()
    
    def toggleHedgeMode(self, checked):
        """Toggle between hedge mode and one-way mode"""
        try:
            result = self.trade_manager.set_position_mode(checked)
            if result:
                mode = "Hedge Mode" if checked else "One-Way Mode"
                QMessageBox.information(self, "Position Mode Changed", f"Successfully switched to {mode}")
            else:
                self.showError("Failed to change position mode")
        except Exception as e:
            self.showError(f"Error changing position mode: {e}")

    def toggleSLTP(self, state):
        """Enable or disable SL/TP inputs based on checkbox state"""
        # In PyQt6, state is an integer: 0 (unchecked), 2 (checked)
        # The comparison with Qt.CheckState.Checked isn't working correctly
        enabled = (state == 2)
        
        print(f"Toggle SLTP called with state value: {state}, enabled: {enabled}")
        
        self.sl_input.setEnabled(enabled)
        self.tp_input.setEnabled(enabled)
        
        # Show visual feedback
        if enabled:
            self.sl_input.setStyleSheet("background-color: rgba(144, 238, 144, 0.2);")  # Light green background
            self.tp_input.setStyleSheet("background-color: rgba(144, 238, 144, 0.2);")  # Light green background
            print("Stop Loss & Take Profit enabled")
        else:
            self.sl_input.setStyleSheet("")  # Reset to default
            self.tp_input.setStyleSheet("")  # Reset to default
            print("Stop Loss & Take Profit disabled")

class OrderForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.form_layout = QFormLayout()
        
        # Add Stop Loss and Take Profit fields
        self.sl_label = QLabel("Stop Loss:")
        self.sl_input = QLineEdit()
        self.sl_input.setPlaceholderText("Optional")
        
        self.tp_label = QLabel("Take Profit:")
        self.tp_input = QLineEdit()
        self.tp_input.setPlaceholderText("Optional")
        
        # Add to layout
        self.form_layout.addRow(self.sl_label, self.sl_input)
        self.form_layout.addRow(self.tp_label, self.tp_input)
        
        self.setLayout(self.form_layout)
    
    def get_order_data(self):
        data = {
            'stop_loss': self.sl_input.text() if self.sl_input.text() else None,
            'take_profit': self.tp_input.text() if self.tp_input.text() else None
        }
        return data

# In your TradeManager.__init__ method
def __init__(self):
    # Existing code...
    
    # Check current position mode and inform the user
    hedge_mode = self.get_position_mode()
    mode_name = "Hedge Mode" if hedge_mode else "One-Way Mode"
    print(f"Account is currently in {mode_name}")

# This would be added to the TradeManager class in tradeManager.py
