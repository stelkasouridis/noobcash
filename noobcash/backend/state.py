from Crypto.PublicKey import RSA
from Crypto import Random

#from blockchain import Blockchain
from blockchain import Blockchain

class State :
    def __init__(self):
        generate_wallet()
        # we need to communicate with the bootstrap node 
        self.blockchain = Blockchain()
        self.utxos = [] # all utxos for all wallets 
        self.nodes = {}
        # contains {'ip' : '', 'port' : '', 'pub' : ''}

    def generate_wallet(self,):
        """ generate wallet """ 
        random_generator = Random.new().read 
        self.key  = RSA.generate(2048,random_generator)
        #key is an RSA key object, the private key is not visible
        self.pub = self.key.publickey

    def add_participant(self,pubkey, ip, port, id):
        nodes[id] = {'ip' : ip , 'port' : port, 'pub' : pubkey}
 
    def remove_utxo(self,utxo):
        utxos.remove(utxo)
    
    def wallet_balance(self,public_key): 
        balance=0
        for utxo in utxos:
            if utxo.sender == public_key: 
                balance+=utxo.amount
        return balance 

# this is the global state exposed to all modules
state = State()


