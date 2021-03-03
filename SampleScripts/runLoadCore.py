"""
runLoadCore.py

Full-core simulation with capturing enabled.
Disable or remove capturing if not needed.

Requirements
   - Load Core Middleware + 2 Load Core Agents
   - Load Core license server
   - Load Core authToken
   - Load Core saved config file: fullcore-simulation.json or use your saved config file
   - Load Core logos for the report: In LoadCoreLogos folder
   - LoadCoreMWAssistant.py
   - LoadcoreAgentAssistant.py

"""

import sys, os, traceback, datetime

from LoadCoreMWAssistant import MW
from LoadCoreAgentAssistant import Agent

# LoadCore middleware IP
mwIp = '10.36.86.40'

licenseServerIp = '10.36.86.74'
agent1Ip = '10.36.86.116'
agent2Ip = '10.36.86.91'

# Get interface from the agent's cli console
agent2CaptureInterface = 'ens160'

# Delete the session.  Set to False if debugging.
deleteSession = True

# Get the user login auth token from the LoadCore GUI by logging in,
# click on the wheel settings icon, help, about
# For security reasons, hide authToken in env or in a file.
# This is shown for demo purpose.
authToken = 'JNNUtp_447aM7DiXG7hBNbVpB3oXGyA7RG-MF0rPtBQ.WVVMzjrkA9l_MVW6IDlxOyjRGUXS2NR6JPyNvDhf0Zc'

# Where the keysight logos are stored for the html report
logoFolder = '/GitLabProjects/LoadCore/PyTest/LoadCoreLogos'

# Where to put the results at the end of the test
resultsFolder = '/GitLabProjects/LoadCore/resultsFolder'

# LoadCore saved config files are in .json format.
configName = "fullcore-simulation.json"

# The path to the saved .json config file to load.
configPath = "/GitLabProjects/LoadCore/PyTest/LoadCoreConfigs/{}".format(configName)

try:
    loadCoreObj = MW(host=mwIp, port=443, authToken=authToken, licenseServer=licenseServerIp,
                     protocol='https', enablehttp2=False)
    
    # select config from configs folder
    config = loadCoreObj.selectConfig(configPath)   

    # The following section is used to remap a config file with new agents.
    # If the plan is to run on the same agents on which the config was saved, you
    # can comment from line 25 to line 40 and upload the original config.

    # get current Agents Info - IP, NodeID, test interfaces and MAC information
    agentsInfo = loadCoreObj.getAgentsInfo()

    # get Agent1 details: agent node id, Interface Name, Interface MAC
    agent1 = loadCoreObj.getAgentDetails(agentsInfo, agent1Ip)   

    # get Agent2 details: agent node id, Interface Name, Interface MAC
    agent2 = loadCoreObj.getAgentDetails(agentsInfo, agent2Ip)   

    # assign agent1 details to agentRan variable
    agentRan = agent1['id'], agent1['Interfaces'][0]['Name'], agent1['Interfaces'][0]['Mac']  
    # assign agent2 details to agentNodes variable
    agentNodes = agent2['id'], agent2['Interfaces'][0]['Name'], agent2['Interfaces'][0]['Mac']  

    # Enable filtering interface for capturing on Agent2    
    agent2Capture = Agent(agentIp=agent2Ip)
    agent2Capture.enableFilter(interface=agent2CaptureInterface)
    
    # simulated nodes in the selected config
    simulatedNodes = ['ran', 'amf', 'nrf', 'ausf', 'udm', 'pcf', 'udr', 'smf', 'upf', 'dn', 'nssf']   
    agentsDict = {}
    # update all emulated nodes with current agents
    for node in simulatedNodes:   
        if node == 'ran':
            # Use first agent for RAN node
            agentsDict[node] = agentRan  
        else:
            # Use second agent for the rest of the nodes
            agentsDict[node] = agentNodes  

    # update configuration with current agents                    
    updatedConfig = loadCoreObj.RemapAgents(config, agentsDict)   

    # upload the modified config or use the selected config if the remap is not needed.
    # For example: uploadedConfig = loadCoreObj.uploadConfig(config=config)
    uploadedConfig = loadCoreObj.uploadConfig(config=updatedConfig)
        
    # start session using the modified config
    sessionId = loadCoreObj.newSession(configID=uploadedConfig[0]['id'])  
    loadCoreObj.configSustainTime(10)

    loadCoreObj.logInfo("Starting test")
    loadCoreObj.startTest()
    # take current time. Will be used inside HTML report
    startTime = datetime.datetime.now()     

    state = loadCoreObj.checkSessionState(status='STARTED')
    loadCoreObj.logInfo(loadCoreObj.getSessionStatus())

    # Start capturing
    agent2Capture.startCapture()
    
    # get test Id from current session
    testId = loadCoreObj.getTestId()   

    # wait until test finishes
    loadCoreObj.checkSessionState(status='STOPPED', waitTime=loadCoreObj.getTestDuration())   
    loadCoreObj.logInfo(loadCoreObj.getSessionStatus())

    # Stop capturing
    agent2Capture.stopCapture()

    # take time after test ends. Will be used inside HTML report
    endTime = datetime.datetime.now()   

    # check REST statistics

    loadCoreObj.logInfo('Extracting REST Stats')
    # extract all statistics from RegisteredUEs view
    statsRegisteredUEs = loadCoreObj.getAllStats(testId, 'RegisteredUEs')   

    for x in sorted(statsRegisteredUEs):
        loadCoreObj.logInfo('%s = %s\nMax - %s : %s' % (x,statsRegisteredUEs[x], x, loadCoreObj.getMaxStat(statsRegisteredUEs[x])))
        
    # extract all statistics from ProcedureRates view
    statsProcedureRates = loadCoreObj.getAllStats(testId, 'NGRANRegistrationprocedure')   
    for x in statsProcedureRates:
        loadCoreObj.logInfo('%s = %s\nAvg Non Zero - %s : %s' % (x, statsProcedureRates[x], x, loadCoreObj.getAvgNonZeroStat(statsProcedureRates[x])))

    # extract all statistics from PDUSessionEstablishment view                
    statsPDUSessionEstablishment = loadCoreObj.getAllStats(testId, 'PDUSessionEstablishment')  
    for x in statsPDUSessionEstablishment:
        loadCoreObj.logInfo('%s = %s\nMax - %s : %s' % (x, statsPDUSessionEstablishment[x], x, loadCoreObj.getMaxStat(statsPDUSessionEstablishment[x])))

    # extract all statistics from NGRANRegistration view
    statsNGRANRegistration = loadCoreObj.getAllStats(testId, 'NGRANRegistration')   
    for x in statsNGRANRegistration:
        loadCoreObj.logInfo('%s = %s\nMax - %s : %s' % (x, statsNGRANRegistration[x], x, loadCoreObj.getMaxStat(statsNGRANRegistration[x])))

    # create HTML report based on a list of statistics. The same statistics from above
    listOfStatistics = ["RegisteredUEs", "NGRANRegistrationprocedure", "PDUSessionEstablishment", "NGRANRegistration"]
    htmlReport = loadCoreObj.createHTMLreport(listOfStatistics, configName,
                                              startTime, endTime, logoFolder, resultsFolder)
    loadCoreObj.logInfo('htmlReport: {htmlReport}')

    pdfFile = loadCoreObj.getPDFreport(configName, startTime, resultsFolder)
    loadCoreObj.logInfo(f'pdfFile: {pdfFile}')

    csvFile = loadCoreObj.getCSVs(configName, startTime, resultsFolder)
    loadCoreObj.logInfo(f'csvFile: {csvFile}')

    capturedLogs = loadCoreObj.getCapturedLogs(resultsFolder)
    loadCoreObj.logInfo(f'capturedLogs: {capturedLogs}')

    if deleteSession:
        loadCoreObj.deleteSession()
        loadCoreObj.getSessionInfo(statusCode=404)

except (AssertionError, Exception) as errMsg:
    loadCoreObj.logError('\n{}'.format(traceback.format_exc(None, errMsg)))
    if deleteSession:
        loadCoreObj.deleteSession()
        

