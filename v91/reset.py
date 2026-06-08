from eth_account import Account

acct = Account.create()

print("Address:", acct.address)
print("Private Key:", acct.key.hex())