import pandas_datareader as pdr
import numpy as np
import datetime
import bisect
from flask import current_app

def getTrades(oneissue:dict, data:str="local", remoterefresh:bool=False) -> dict:
    file_path = current_app.config["CSVTMP"]
    data_source = current_app.config["SOURCE"]
    apikey = current_app.config["API_KEY"]
    debug = current_app.config["DEBUG"]
    issue = oneissue["issue"]
    fromdate = oneissue["fromdate"]
    todate = oneissue["todate"]
    pnl = np.array([])
    try:
        pnl = np.loadtxt(file_path, delimiter=",")
        if debug and 1+1 == 3:
            print("Trades array: ")
            print(pnl)
            print("Array size: %d " % (pnl.size))
    except Exception as e:
        print("Error occurred while reading the file:")
        print(e)

    if data == "remote" and (pnl.size == 0 or remoterefresh): 
        #start_date = datetime.datetime.strptime(fromdate, '%Y-%m-%d')
        #end_date = datetime.datetime.strptime(todate, '%Y-%m-%d')
        qt = pdr.DataReader(issue, data_source, fromdate, todate, api_key=apikey)
        
        if debug and 1+1 == 3: #print result
            print (qt.shape)
            print (qt.head())
            nrows = qt.shape[0]
            print ("Number Rows: %d " % (nrows))
        
        qtC = np.array(qt.close)
        #pnl = np.diff(qtC)
        pnl = (qtC[1:] - qtC[:-1]) / qtC[:-1]     
        np.savetxt(file_path, pnl, fmt="%f", delimiter=",")
                
    return {'pnl_d':pnl,'close_d':qtC}

def calCAR(pnl:np.array, oneissue:dict) -> dict:
    debug = current_app.config["DEBUG"]
    fromdate = oneissue["fromdate"]
    todate = oneissue["todate"]
    nrand = 100
    dd95_limit = 0.10 # drawdown limit at 5% risk
    randreplace = True
    adaptive = True
    fractionstep = 2
    fractionlimt = 401
    accuracy_tolerance = 0.05 # default 5% risk tolerance
    twr25 = list()
    ddlist = list()
    count = pnl.size
    if count == 0:
        return False

    f = 0
    prodd = 0
    if adaptive:
        exhaustive = lambda x: x < accuracy_tolerance
    else:
        exhaustive = lambda x: True and f < fractionlimt
    while exhaustive(prodd):
        twr = list()
        countdd =0
        f += fractionstep
        data = list()
        for iseq in range(nrand): # loop over # of random sequences
            # Randomly reorder trades             
            randtrades = np.random.RandomState(seed=None).choice(pnl,size=count,replace=randreplace)
            # Calculate account balance and drawdown for current sequence of trades
            equity = 1
            equityhigh = equity
            ddmax = 0
            line = [1]         
            for i in range(count):
                newequity = equity * (1+((f/100)*randtrades[i]))
                #hold = equity * (f/100)
                #profit = hold * randtrades[i]
                #cash = equity - hold
                #newequity = hold + profit + cash
                # Calculate closed trade percent drawdown
                if (newequity > equityhigh):
                    equityhigh = newequity
                else:
                    dd = (equityhigh - newequity) / equityhigh
                    if (dd > ddmax):
                        ddmax = dd
                equity = newequity
                line.append(equity)
                
            # Accumulate results for probability calculations
            twr.append(equity)
            if ddmax > dd95_limit:
                countdd += 1
            safef = f
            data.append(line)
            if debug and 1+1 == 3: #print result
                print ("ddmax: ", ddmax,"countdd: ", countdd,"f: ", f,)
        
        twr25.append(np.percentile(twr,25))
        prodd = countdd / nrand
        ddlist.append(prodd)
        if debug and 1+1 == 3: #print result
            print ("twr: ", twr)
        #np.savetxt("debug.csv", twr, fmt="%f", delimiter=",")

    #start_date = datetime.datetime.strptime(fromdate, '%Y-%m-%d')
    #end_date = datetime.datetime.strptime(todate, '%Y-%m-%d')            
    time_delta = todate - fromdate
    days = time_delta.days
    # Calculate the number of years by dividing the number of days by 365 (approximation)
    years_in_hist = days / 365
    if debug and 1+1 == 3: #print result
        print ("years_in_hist: ", years_in_hist) 
                                
    safef_index = bisect.bisect_left(ddlist, accuracy_tolerance)
    if safef_index > len(twr25) - 1:
        safef_index = len(twr25) - 1
    car25 = (twr25[safef_index] ** (1/years_in_hist) - 1) * 100
    if debug and 1+1 == 3: #print result
        print ("twr25: ", twr25[safef_index]-1)
        
    # calculate base eq curve
    return {'safef':safef,'car25':car25,'eq':data}

def calPnl_fixfrac(pnl_d:np.array, oneissue:dict, f:int) -> list:
    debug = current_app.config["DEBUG"]    
    count = pnl_d.size
    if count == 0:
        return False
    # Calculate account balance current sequence of trades
    equity = 1
    equityhigh = equity
    ddmax = 0
    pnl = [1]       
    for i in range(count):
        newequity = equity * (1+(f/100*(pnl_d[i])))
        # Calculate closed trade percent drawdown
        if (newequity > equityhigh):
            equityhigh = newequity
        else:
            dd = (equityhigh - newequity) / equityhigh
            if (dd > ddmax):
                ddmax = dd
        equity = newequity
        pnl.append(equity)

    return pnl

def truncate_lists(list1, list2):
    if len(list1) > len(list2):
        list1 = list1[:len(list2)]
    elif len(list2) > len(list1):
        list2 = list2[:len(list1)]
    
    return list1, list2

def calCCxy(x:list, y:list) -> float:
    x, y = truncate_lists(x, y)
    
    # Compute correlation coefficient
    correlation_matrix = np.corrcoef(x, y)
    correlation = correlation_matrix[0, 1]
    return correlation