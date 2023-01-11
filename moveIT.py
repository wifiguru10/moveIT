#!ipython3 -i

import meraki
import copy

import os,sys
from time import *

import asyncio
from meraki import aio
import tqdm.asyncio

import get_keys as g
import datetime
import random

import batch_helper
from bcolors import bcolors as bc




log_dir = os.path.join(os.getcwd(), "Logs/")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)


#Main dashboard object
db = meraki.DashboardAPI(
            api_key=g.get_api_key(), 
            base_url='https://api.meraki.com/api/v1/', 
            output_log=True,
            log_file_prefix=os.path.basename(__file__)[:-3],
            log_path='Logs/',
            print_console=False)

#Loads whilelist from disk if it's available, otherwise the script will span ALL organizations your API key has access to
orgs_whitelist = []
file_whitelist = 'org_whitelist.txt'
if os.path.exists(file_whitelist):
    f = open(file_whitelist)
    wl_orgs = f.readlines()
    for o in wl_orgs:
        if len(o.strip()) > 0:
            orgs_whitelist.append(o.strip())

### ASYNC SECTION

async def getOrg_Networks(aio, org_id):
    result = await aio.organizations.getOrganizationNetworks(org_id,perPage=1000, total_pages='all')
    return org_id, "networks", result


async def getOrg_Devices(aio, org_id):
    result = await aio.organizations.getOrganizationDevices(org_id,perPage=1000, total_pages='all')
    return org_id, "devices", result

async def getOrg_Devices_Statuses(aio, org_id):
    result = await aio.organizations.getOrganizationDevicesStatuses(org_id,perPage=1000, total_pages='all')
    return org_id, "devices_statuses", result

async def getOrg_Devices_Inventory(aio, org_id):
    result = await aio.organizations.getOrganizationInventoryDevices(org_id,perPage=1000, total_pages='all')
    return org_id, "devices_inventory", result




async def getOrg_Licenses(aio, org_id):
    try:
        result = await aio.organizations.getOrganizationLicenses(org_id,perPage=1000, total_pages='all')
    except:
        return org_id, "license_inventory", None
    return org_id, "license_inventory", result


async def getOrg_Templates(aio, org_id):
    result = await aio.organizations.getOrganizationConfigTemplates(org_id)
    return org_id, "templates", result

async def getNetworkClients(aio, netid):
    try:
        result = await aio.networks.getNetworkClients(netid,perPage=1000,total_pages='all',timespan=86400)
    except:
        print("Whoops")
        result = []
    return netid, "netClients", result

async def getSwitchStatuses_Device(aio, serial):
    result = await aio.switch.getDeviceSwitchPortsStatuses(serial)
    return serial, "statuses", result

async def getSwitchPorts_Device(aio, serial):
    result = await aio.switch.getDeviceSwitchPorts(serial)
    return serial, "switchports", result

async def getNetworkApplianceVpnSiteToSiteVpn_Network(aio, net_id):
    result = await aio.network.getNetworkApplianceVpnSiteToSiteVpn(net_id)
    return netid, "VPNsit2site", result

async def getOrg_UplinkStatus(aio, org_id):
    result = await aio.organizations.getOrganizationUplinksStatuses(org_id, per_page=1000, total_pages='all')
    return org_id, "uplinkStatus", result


async def getEverything():
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=10,
                maximum_retries= 100,
                nginx_429_retry_wait_time=60,
                wait_on_rate_limit=True,
                print_console=False,
                
        ) as aio:
            orgs_raw = await aio.organizations.getOrganizations()
            orgs = {}
            for o in orgs_raw:
                if len(orgs_whitelist) == 0:
                    if o['api']['enabled']:
                        orgs[o['id']] = o
                elif o['id'] in orgs_whitelist:
                    orgs[o['id']] = o
            
            org_networks = {}
            org_devices = {}
            org_devices_statuses = {}
            org_devices_inventory = {}
            org_licenses = {}
            org_templates = {}
            org_uplinkStatus = {}
            getTasks = []
            for o in orgs:
                getTasks.append(getOrg_Networks(aio, o))
                getTasks.append(getOrg_Devices(aio, o))
                getTasks.append(getOrg_Devices_Statuses(aio, o))
                #getTasks.append(getOrg_Devices_Inventory(aio,o))
                #getTasks.append(getOrg_Licenses(aio,o))
                #getTasks.append(getOrg_Templates(aio, o))
                #getTasks.append(getOrg_UplinkStatus(aio,o))

            for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                oid, action, result = await task
                if action == "devices":
                    org_devices[oid] = result
                elif action == "devices_statuses":
                    org_devices_statuses[oid] = result
                elif action == "devices_inventory":
                    org_devices_inventory[oid] = result
                elif action == "license_inventory":
                    org_licenses[oid] = result
                elif action == "networks":
                    org_networks[oid] = result
                elif action == "templates":
                    org_templates[oid] = result
                elif action == 'uplinkStatus':
                    org_uplinkStatus[oid] = result

            
            print("DONE")
            return org_devices, org_devices_statuses, org_devices_inventory, org_licenses, org_networks, org_templates, org_uplinkStatus
    return

async def getEverythingDevice(device_list):
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=50,
                maximum_retries= 100,
                wait_on_rate_limit=False,
                print_console=False,
                
        ) as aio:
            getTasks = []
            for d in device_list:
                getTasks.append(getSwitchPorts_Device(aio, d['serial']))
                getTasks.append(getSwitchStatuses_Device(aio, d['serial']))

            switches_statuses = {}
            switches_switchports = {}
            for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                serial, action, result = await task
                if action == 'statuses':
                    switches_statuses[serial] = result
                elif action == 'switchports':
                    switches_switchports[serial] = result
                    
                
            
            print("DONE")
            return switches_switchports, switches_statuses

async def getEverythingNetwork(network_list):
    async with meraki.aio.AsyncDashboardAPI(
                api_key=g.get_api_key(),
                base_url="https://api.meraki.com/api/v1",
                output_log=True,
                log_file_prefix=os.path.basename(__file__)[:-3],
                log_path='Logs/',
                maximum_concurrent_requests=50,
                maximum_retries= 100,
                wait_on_rate_limit=True,
                print_console=False,
                
        ) as aio:
            getTasks = []
            for net in network_list:
                #print(net)
                getTasks.append(getNetworkClients(aio, net['id']))
                
            network_clients = {}
            for task in tqdm.tqdm(asyncio.as_completed(getTasks), total=len(getTasks), colour='green'):
                netid, action, result = await task
                if action == 'netClients':
                    network_clients[netid] = result
                    
                
            
            print("DONE")
            return network_clients 


### /ASYNC SECTION   



orgs = db.organizations.getOrganizations()

### This section returns all Devices, Networks and Templates in all the orgs you have access to
start_time = time()
org_devices, org_devices_statuses, org_devices_inventory, org_licenses, org_networks, org_templates, org_uplinkStatus = asyncio.run(getEverything())
end_time = time()
elapsed_time = round(end_time-start_time,2)

print(f"Loaded Everything took [{elapsed_time}] seconds")
print()
### end-of Devices/Networks/Templates

def getDevice(serial):
    for o in org_devices:
        devs = org_devices[o]
        for d in devs:
            if serial == d['serial']:
                return d
    return

def getNetwork(netID):
    for o in org_networks:
        nets = org_networks[o]
        for n in nets:
            if netID == n['id']:
                return n
    return

def getOrg(orgID):
    for o in orgs:
        if orgID == o['id']:
            return o
    return

#same as compare() but strips out ID/networkID for profiles/group policies etc
def soft_compare(A, B):
    t_A = copy.deepcopy(A)
    t_B = copy.deepcopy(B)
    delete_keys1 = ['id', 'networkId', 'groupPolicyId', 'dnsRewrite', 'adultContentFilteringEnabled', 'roles'] # 'radiusServerTimeout', 'radiusServerAttemptsLimit', 'radiusFallbackEnabled', 'radiusAccountingInterimInterval' ]
    for dk in delete_keys1:
        if dk in t_A: t_A.pop(dk)
        if dk in t_B: t_B.pop(dk)

    #This bit of code should "true up" both objects by removing uncomming keys, similar to the static removal of keys above, but dynamic
    toRemove = []
    if len(t_A) > len(t_B) and len(t_B) > 0:
        for k in t_A:
            if not k in t_B:
                toRemove.append(k)
        for tr in toRemove:
            if not type(tr) == dict: t_A.pop(tr)
    elif len(t_B) > len(t_A) and len(t_A) > 0:
        for k in t_B:
            if not k in t_A:
                toRemove.append(k)
        for tr in toRemove:
            if not type(tr) == dict: t_B.pop(tr)

    if not len(t_A) == len(t_B):
        print("Both objects aren't equal.... somethings wrong...")


    delete_keys2 = [ 'id', 'radsecEnabled' , 'openRoamingCertificateId', 'caCertificate']
    #had to add some logic to pop the "id" and "radsecEnabled". 'id' is unique and 'radsecEnabled' is beta for openroaming
    if 'radiusServers' in t_A:
        for radServ in t_A['radiusServers']:
            for dk in delete_keys2:
                if dk in radServ: radServ.pop(dk)
            #radServ.pop('id')
            #if 'radsecEnabled' in radServ: radServ.pop('radsecEnabled')
        #t_A['radiusServers'][0].pop('id')
        #if 'radsecEnabled' in t_A['radiusServers'][0]: t_A['radiusServers'][0].pop('radsecEnabled')

    if 'radiusAccountingServers' in t_A: 
        for radACC in t_A['radiusAccountingServers']:
            for dk in delete_keys2:
                if dk in radACC: radACC.pop(dk)   

    if 'radiusServers' in t_B:
        for radServ in t_B['radiusServers']:
            for dk in delete_keys2:
                if dk in radServ: radServ.pop(dk)

    if 'radiusAccountingServers' in t_B:
        for radACC in t_B['radiusAccountingServers']:
            for dk in delete_keys2:
                if dk in radACC: radACC.pop(dk) 
        
    result = compare(t_A, t_B)
    if not result:
        a = 0 #really just a placeholder for breakpoint
    return result

 #compares JSON objects, directionarys and unordered lists will be equal 
def compare(A, B):
    result = True
    if A == None and B == None: 
        return True

    if A == B:
        return True

    if not type(A) == type(B): 
        #print(f"Wrong type")
        return False

    #try:
    
    if not type(A) == int and not type(A) == str and not type(A) == float and not type(A) == bool and not type(A) == dict and not type(A) == list: 
        print(f'Wierd Compare type of [{type(A)}] Contents[{A}]')
        return False
    
    #except:
    #    print()
    
    if type(A) == dict:
        for a in A:
            #if a in B and not self.compare(A[a],B[a]):
            #    return False
            result = compare(A[a],B[a])
            if a in B and not compare(A[a],B[a]):
                return False
    elif type(A) == list:
        found = 0
        for a in A:
            if type(a) == dict:
                for b in B:
                    if compare(a,b):
                        found += 1
            #elif A == B:
                #return True
            elif not a in B:
                return False
        #if found == len(A) and len(A) > 0:
            #print("YEAH")
        if A == B:
            return True
        elif not found == len(A):
            return False             
        
    else:
        if not A == B:
            return False
    if 'name' in A and 'number' in A:
        print()  
    return result
##END-OF COMPARE

#splits a list into chucks, returns list object
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

#re-wrote this to support dictionaries or lists
def findName(list_of_things, target_name):
    res = []
    if type(list_of_things) == list:
        for thing in list_of_things:
            if target_name in thing['name']:
                res.append(thing)
        return res

    elif type(list_of_things) == dict: #it's a list, make it a dict
        for o in list_of_things:
            stuffs = list_of_things[o]
            for s in stuffs:
                #print(f"Looking for [{target_name}] in [{s['name']}]")
                if target_name in s['name']:
                    res.append(s)
        return res

def getSerialOrgID(s):
    if len(s) == 0: return
    try: 
        device = db.devices.getDevice(s)
        sn_orgid = db.networks.getNetwork(device['networkId'])['organizationId']
        return sn_orgid
    except Exception as e:
        print(f"Error with Serial#[{s}] ... it couldn't process")
        print(e)
        return
    
def claimSerial_toNet(db, serial, netid):
    claimed = True
    dev = None
    try:
        dev = db.devices.getDevice(serial)
        if dev['networkId'] == netid:
            print(f"Device[{serial}] already claimed in network[{netid}]")
            print(dev)
            print()
            return
    except:
        claimed = False
        print(f"Device isn't reachable, might already be removed from the network")
        return
    
    
    claims = { 'serials': []}
    claims['serials'].append(serial)
    
    if claimed:
        db.networks.removeNetworkDevices(dev['networkId'],dev['serial'])
        print(f"Device[{serial}] Removed from network[{dev['networkId']}]")
        dev_oid = db.networks.getNetwork(dev['networkId'])['organizationId']
        db.organizations.releaseFromOrganizationInventory(dev_oid,**claims)
        claimed = False
        
    keep = [ 'name','address','tags','lat','lng','notes']
    new_dev = {}
    for d in dev: #this filters out everthing but the key/value pairs in keep
        if d in keep:
            new_dev[d] = dev[d]

    done = False
    loop_count = 0
    while True:
        loop_count += 1
        if not claimed: #which should be on first run
            try:
                db.organizations.claimIntoOrganizationInventory(orgid_provisioning,**claims)
                sleep(5)
            except Exception as e:
                print(f"Not ready to claim into org yet...waiting 60 seconds...")
                print(f"\t{e}")
                sleep(60)
                print()
                continue
            db.networks.claimNetworkDevices(netid, serials=[serial])
            claimed = True #so this only does it once if the "update" command triggers an exception
            print(f"Device[{serial}] Successfully claimed into network[{netid}]")
        try:
            db.devices.updateDevice(serial,**new_dev) #this will error if it's too soon
            done = True
            print(f"Device[{serial}] Updated with [{new_dev}]")
        except:
            print(f"Nope, not ready yet. Device[{serial}] is still in transition...sleeping 30...")
            sleep(30)
            
        if done or loop_count > 10:
            break
    
    print()    
    return

def isSerial(t_serial):
    if len(t_serial) == 14 and t_serial[4] == '-' and t_serial[9] == '-': return True
    return False

    
db = meraki.DashboardAPI(api_key=g.get_api_key(), base_url='https://api.meraki.com/api/v1/', maximum_retries=50, print_console=False)

orgs = db.organizations.getOrganizations()

provisioning = findName(orgs, "Provisioning Test Network")
orgid_provisioning = provisioning[0]['id']
RMA_NetworkName = "RMA Network"
RMA_networkID = ""

nets = db.organizations.getOrganizationNetworks(orgid_provisioning)
RMA_obj = findName(nets, RMA_NetworkName)
if type(RMA_obj) == list and len(RMA_obj) > 0:
    RMA_obj = RMA_obj[0]
    print(f"Found RMA Network[{RMA_NetworkName}] NetID[{RMA_obj['id']}] in organization[{orgid_provisioning}]")
else:
    RMA_obj = None
    
if not RMA_obj:
    print(f"Error, RMA Network[{RMA_NetworkName}] not available in organization[{orgid_provisioning}] ")
    RMA_obj = db.organizations.createOrganizationNetwork(orgid_provisioning,name=RMA_NetworkName, productTypes=['appliance','cellularGateway','wireless','switch','sensor'])
    print(f"Created NetworkID[{RMA_obj['id']}] ... Completed")
    print()
    
if RMA_obj == None:
    print(f"Trying to exit.....")
    exit()
    

try:
    if 'id' in RMA_obj: RMA_networkID = RMA_obj['id']
except:
    print("WHY!?!?")
    exit()

f = open('input_serials.txt','r')
raw = f.readlines()
f.close()

data = []
for r in raw:
    t_serial = r.strip().split('#')[0].strip()
    if len(t_serial) == 14 and t_serial[4] == '-' and t_serial[9] == '-':
        data.append(t_serial)

devices_to_move = []
devices_to_move_obj = {}
for d in data:
    print(f"Processing [{d}]")
    devOID = getSerialOrgID(d)
    if devOID != None:
        if orgid_provisioning != devOID:
            devices_to_move.append(d)
            devices_to_move_obj[d]= db.devices.getDevice(d)
            device_network_obj = db.networks.getNetwork(devices_to_move_obj[d]['networkId'])
            #print(f"Network {device_network_obj[d]}")
            
            print(f"Device[{d}] needs to be moved from orgID[{devOID}] to target[{orgid_provisioning}]")
            dev = devices_to_move_obj[d]
            try:
                prod = dev['productType']
            except:
                prod = "BARF" #none obj
                
            if prod == "wireless":
                claimSerial_toNet(db,d,RMA_networkID)
                #db.devices.updateDevice(d,**new_dev)
                
            elif prod == "switch":
                if not isSerial(d):
                    print(f"WHAAAAT? {d}")
                else:
                    switchports = db.switch.getDeviceSwitchPorts(d)
                claimSerial_toNet(db,d,RMA_networkID)
                #db.devices.updateDevice(d,**new_dev)
                
            elif prod == "appliance":
                #create new network - RMA + network name
                #nets = db.organizations.getOrganizationNetworks(orgid_provisioning)
                
                new_name = "Blah"
                #RMA_obj = db.organizations.createOrganizationNetwork(orgid_provisioning,name=RMA_NetworkName, productTypes=['appliance','cellularGateway','wireless','switch','sensor'])

                #move MX
                #copy / sync VLANs + subnets
                #group / policies?
                 
            else:
                
                #print(f"BOOO! Can't find product type, moving anyway")
                claimSerial_toNet(db,d,RMA_networkID)
            
            


            

