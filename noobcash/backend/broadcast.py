from Crypto.PublicKey import RSA
from Crypto import Random
from flask import Flask, request, Blueprint, make_response
import requests
import simplejson as json


from block import Block
import state as State
from transaction import Transaction
import config
import time
app = Flask(__name__)
import functools
print = functools.partial(print, flush=True)


#------------------------------------------------------------
# BROADCASTING

def broadcast_block(block,node_id = None) :
    #print('Requesting BROADCAST BLOCK lock', State.state.lock)
    #State.state.lock.acquire()
    json_block = block.to_json()
    #print('Releasing BROADCAST BLOCK lock', State.state.lock)
    #State.state.lock.release()
    return broadcast(json_block,'receive_block',node_id)

def broadcast_transaction(t,node_id = None ) :
    #print('Requesting BROADCAST TRANSACTION lock', State.state.lock)
    #State.state.lock.acquire()
    json_t = t.to_json()
    #print('Releasing BROADCAST TRANSACTION lock', State.state.lock)
    #State.state.lock.release()
    return broadcast(json_t,'receive_transaction',node_id)


def broadcast(json_obj,rest_point,node_id = None):
    """ Broadcast object to network """
    if node_id == None :
        broadcast_nodes = list(State.state.nodes.values()) 
    else :
        broadcast_nodes = [State.state.nodes[node_id]]
    #if (rest_point == 'receive_transaction'):
        #for utxo in State.state.utxos.items():
            #print('For node ',State.state.key_to_id(utxo[0]),': ',end='')
            #for utxo1 in utxo[1]:
                #print(utxo1['amount'], end=' ')
            #print()
    for node in broadcast_nodes:
        #broadcast to everyone except sender
        #print('Sending to node ',State.state.key_to_id(node['pub']))
        if (node['pub'] == State.state.pub):
            continue
        ip = node["ip"]
        response = requests.post('{}/{}'.format(ip,rest_point), json=json_obj)
    return True


def broadcast_nodes_info():
    #print('Requesting BROADCAST NODES lock', State.state.lock)
    #State.state.lock.acquire()
    """
    when all nodes are in the state.nodes dictionary,
    notify all nodes about the others
    """
    json_obj = json.dumps({'chain' : [b.to_json() for b in State.state.chain] , 
                           'utxos' : State.state.utxos, 
                           'transactions' : [t.to_json() for t in State.state.transactions],
                           'nodes' : State.state.nodes})

    #print('Broadcasting info')
    ret = broadcast(json_obj,'receive_info')  
    #print(ret)
    for node in State.state.nodes.values():
        if node['pub'] == State.state.pub : 
            continue 
        ret = new_transaction(node['pub'],100)
        #print(ret)
    #print('Giving command to start')
    # notify everyone to start transactions
    for node in State.state.nodes.values():
        if node['pub'] == State.state.pub : 
            continue 
        ip = node['ip']
        res = requests.post('{}/start'.format(ip))
    config.START = 'yes'    
    #print('Releasing BROADCAST NODES lock', State.state.lock)
    #State.state.lock.release()






def new_transaction(receiver, amount,new_id = None):
    #creates t, the new transaction, and broadcasts it
    #print('Requesting NEW TRANSACTION lock', State.state.lock)
    #State.state.lock.acquire()
    print(len(State.state.transactions),config.CAPACITY)
    if ((len(State.state.transactions) >= config.CAPACITY)):
        print('NEW: I have to mine the block, if this tx is valid, I have to make a new one.')
        ret = State.state.mine_and_broadcast_block()
    t = Transaction.create_transaction(receiver, amount)
    if t == False : 
        #print('Releasing NEW TRANSACTION lock', State.state.lock)
        #State.state.lock.release()
        return False 
    ret = broadcast_transaction(t,new_id)
    #print("Transactions not in block: ", len(State.state.transactions))
    #print('Releasing NEW TRANSACTION lock', State.state.lock)
    #State.state.lock.release()
    return ret
# ------------------------------------------



API_communication = Blueprint('API_communication',__name__)

@API_communication.route('/start',methods=['POST'])
def start():
    config.START = 'yes'
    return make_response("OK",200)
    
@API_communication.route('/receive_block', methods=['POST'])
def receive_block():
    #print('Requesting RECEIVE BLOCK lock', State.state.lock)
    #State.state.lock.acquire()
    #time.sleep(0.1)
    json_string = request.get_json()
    block =  Block(**json.loads(json_string))
    block.hash = str(block.hash).encode()
    block.previous_hash = str(block.previous_hash).encode()
    block.nonce = str(block.nonce).encode()
    
    # pass to Blockchain to add block
    block.transactions = [Transaction(**json.loads(t)) for t in block.transactions]
    #print('received a block')
    ret = State.state.add_block(block) 
    #print('Releasing RECEIVE BLOCK lock', State.state.lock)
    #State.state.lock.release()
    return make_response("OK",200)

@API_communication.route('/receive_transaction', methods=['POST'])
def receive_transaction():
    #print('Requesting RECEIVE TRANSACTION lock', State.state.lock)
    # Call static method, object creation is handled in function
    #State.state.lock.acquire()
    #time.sleep(0.1)
    if (len(State.state.transactions) >= config.CAPACITY):
        #print('RECEIVE: I have to mine the block, if this tx is valid, I have to make a new one.')
        State.state.mine_and_broadcast_block()
    json_string = request.get_json()
    t = Transaction(**json.loads(json_string)) 

    return_val = Transaction.validate_transaction(t)
    
    #print('Transactions not in block:', len(State.state.transactions))
  
    #print('Received Transaction and is : ',return_val,flush=True)
    #print('Releasing RECEIVE TRANSACTION lock', State.state.lock)
    #State.state.lock.release()
    return make_response("OK",200)
    

# We receive a chain, this is in a different senario than the request_chain function
@API_communication.route('/receive_info',methods=['POST'])
def receive_info():
    json_obj = request.get_json()
    obj_dict = json.loads(json_obj)
    block_list = obj_dict['chain']
    # we also receive transactions we might have missed 
    # this is the init so we do not validate!

    if State.state.chain != [] and State.state.transactions != []:
        return make_response('Bad Init',500)

    transactions = obj_dict['transactions']
    utxos = obj_dict['utxos']
    nodes = obj_dict['nodes']
    State.state.nodes = nodes
    for utxo in utxos.keys():
        utxos[utxo] = list(utxos[utxo])

    State.state.transactions =  [Transaction(**json.loads(t)) for t in transactions]
    State.state.chain = [Block(**json.loads(block)) for block in block_list]
    for b in State.state.chain :
        b.transactions = [Transaction(**json.loads(t)) for t in b.transactions]
        b.nonce = str(b.nonce).encode()
        b.hash = str(b.hash).encode()
        b.previous_hash = str(b.previous_hash).encode()
    State.state.utxos = utxos 

    return make_response('OK',200)

# All necessary communication for a new node to enter the network 
@API_communication.route('/register_node', methods=['POST'])
def register_node():
    
        '''
        An incoming node posts a request to enter the network 
        - Handle request and post in return 
        '''
        data = json.loads(request.get_json())
        node_ip = data['ip']
        node_pubkey = data['pub']
        if (not node_ip or not node_pubkey):
            return "Invalid", 400

        new_id = State.state.last_id + 1 #
        #print('new node id is:',new_id)
        State.state.last_id = new_id
        new_id = str(new_id)
        State.state.utxos[node_pubkey] = []

        State.state.nodes[new_id] = {}
        State.state.nodes[new_id]['ip'] = node_ip
        State.state.nodes[new_id]['pub'] = node_pubkey

        if (int(new_id) == config.NODE_CAPACITY - 1) :
            #print('Broadcasting info')
            broadcast_nodes_info()
        return make_response(json.dumps({'id' : new_id}),200)

# A node requests the chain via a GET request , we return the chain
@API_communication.route('/request_chain',methods=['GET'])
def request_chain():
    #print('Requesting REQUEST CHAIN lock', State.state.lock)
    #State.state.lock.acquire()
    block_list = [block.to_json() for block in State.state.chain]        
    json_chain = json.dumps({"chain": block_list})
    #print('Releasing REQUEST CHAIN lock', State.state.lock)
    #State.state.lock.release()
    return json_chain 




# ------------------- CLI COMMANDS --------------------- 

@API_communication.route('/start_coordinator', methods=['POST'])
def start_coordinator():
    
    json_string = request.get_json()
    d = json.loads(json_string)
    config.DIFFICULTY = int(d['DIFFICULTY'])
    config.CAPACITY = int(d['CAPACITY'])
    config.NODE_CAPACITY = int(d['NODE_CAPACITY'])
    #print(int(d['NODE_CAPACITY']))
    State.state.id = '0'
    State.state.nodes['0'] = {'ip': d['host'], 'pub': State.state.pub}
    State.state.genesis() # Create genesis block and transaction
    
    return make_response(json.dumps({"id" : State.state.id}), 201)

@API_communication.route('/new_transaction', methods=['POST'])
def cli_new_transaction():
    #print('Requesting CLI NEW TRANSACTION lock', State.state.lock)
    #State.state.lock.acquire()
    json_string = request.get_json()
    d = json.loads(json_string)
    try:
        amount = int(d['amount'])
    except:
        #print('Releasing CLI NEW TRANSACTION lock', State.state.lock)
        #State.state.lock.release()
        return make_response('Transaction Failed',400)
    node_id = d['recipient_address']
    node = State.state.nodes[node_id]
    if (new_transaction(node['pub'], amount)):
        #print('Releasing CLI NEW TRANSACTION lock', State.state.lock)
        #State.state.lock.release()
        return make_response('OK',200)
    else:
        #print('Releasing CLI NEW TRANSACTION lock', State.state.lock)
        #State.state.lock.release()
        return make_response('Transaction Failed',400)
        

#! DONE
# Please read the exercise report before chaning stuff
@API_communication.route('/view_transactions', methods=['GET'])
def view_transactions():
    #print('Requesting VIEW LAST BLOCK TRANSACTIONS lock', State.state.lock)
    #State.state.lock.acquire()
    # there is always a last block so no need to check for empty chain
    last_block = State.state.chain[-1]
    json_trans = [t.to_json() for t in last_block.transactions]
    res = json.dumps({'transactions' : json_trans})
    #print('Releasing VIEW LAST BLOCK TRANSACTIONS lock', State.state.lock)
    #State.state.lock.release()
    return res

#! DONE 
@API_communication.route('/balance', methods=['GET'])
def show_balance():
    return json.dumps(State.state.wallet_balance())

@API_communication.route('/start_client', methods=['POST'])
def start_client():

    json_string = request.get_json()
    data = json.loads(json_string)
    COORDINATOR_IP = data['coordinator_host']
    State.state.nodes[0] = {'ip': data['coordinator_host']}
    config.DIFFICULTY = int(data['DIFFICULTY'])
    config.CAPACITY = int(data['CAPACITY'])


    # give coordinator 
    json_data = json.dumps({'ip' : data['host'], 'pub' : State.state.pub})
    response = requests.post('{}/register_node'.format(COORDINATOR_IP), json=json_data)
    State.state.id = response.json()['id']
    #print('Our very own id is :',State.state.id)
    return make_response(json.dumps({"id" : State.state.id}),200)

@API_communication.route('/notify_start', methods=['GET'])
def notify_start():
    return make_response(json.dumps({"resp" : config.START}),200)