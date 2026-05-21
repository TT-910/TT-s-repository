class Order:
    def __init__(self, order_id, symbol, order_type, direction, price, amount, audio_name):
        self.order_id = order_id
        self.symbol = symbol
        self.order_type = order_type   # 'limit'
        self.direction = direction
        self.price = price
        self.amount = amount
        self.audio_name = audio_name
        self.status = 'pending'

class TradingEngine:
    def __init__(self, account):
        self.account = account
        self.order_book = []
        self.next_id = 1

    def limit_order(self, symbol, price, amount, direction, audio_name):
        """提交限价单，挂入订单簿"""
        order = Order(self.next_id, symbol, 'limit', direction, price, amount, audio_name)
        self.next_id += 1
        self.order_book.append(order)
        print(f"  限价单已挂单: {direction} {symbol} {amount}股 @ {price}元")
        return order.order_id

    def update_price(self, symbol, new_price):
        """外部行情推送，触发限价单撮合"""
        for order in self.order_book[:]:
            if order.symbol != symbol or order.status != 'pending':
                continue
            if order.direction == 'buy' and new_price <= order.price:
                self._execute_order(order, new_price)
            elif order.direction == 'sell' and new_price >= order.price:
                self._execute_order(order, new_price)

    def _execute_order(self, order, fill_price):
        if order.direction == 'buy':
            success = self.account.buy(order.symbol, fill_price, order.amount, order.audio_name)
        else:
            success = self.account.sell(order.symbol, fill_price, order.amount, order.audio_name)
        if success:
            order.status = 'filled'
            self.order_book.remove(order)
            print(f"  限价单 {order.order_id} 已成交 @ {fill_price}")