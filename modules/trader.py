
class PaperTrader:
    def __init__(self,balance):
        self.balance=balance
        self.positions=[]
    def execute_signal(self,s):
        if self.balance>=s["stake"]:
            self.balance-=s["stake"]
            self.positions.append(s)
