import requests, os, json, time, platform
import datetime, shutil
from pprint import pformat

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# Disable non http connections.
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Logger:
    def logMsg(self, msgType, msg):
        """
        This is a private function for sdloAssistant use only.
        Formatting the stdout log messages with a timestamp

        Parameter
           msgType <str>: info|debug|error
           msg <str>: The message for stdout.
        """
        timestamp = str(datetime.datetime.now()).split(' ')[1]
        stdout = f'\n{timestamp}: [{msgType}]: {msg}'
        print(stdout)
        self.writeToLogFile(stdout+'\n', logType='a')

        if msgType == 'error':
            raise Exception(msg)

    def logInfo(self, msg):
        self.logMsg('info', msg)

    def logDebug(self, msg):
        self.logMsg('debug', msg)

    def logError(self, msg):
        self.logMsg('error', msg)

    def writeToLogFile(self, msg, logType='a'):
        currentDir = os.path.dirname(os.path.abspath(__file__))
        debugLogFile = f'{currentDir}/loadCoreAssistantDebug.log'
        with open(debugLogFile, logType) as logFile:
            logFile.write(msg)

class Requests(Logger):
    def get_requests(self):
        if self.httpv2:
            s = requests.Session()
            s.mount(self.baseurl, HTTP20Adapter())
            s.verify = False
            return s
        else:
            return requests

    def get(self, url, params=None, headers=None, stream=False):
        self.logInfo(f'\nGET: {self.baseurl}{url}\nPARAMS: {params}')
        return self.get_requests().get('%s%s' % (self.baseurl, url), params=params, headers=headers, verify=False,
                                       stream=stream)

    def getInfoFromURL(self, url, params=None, headers=None):
        self.logInfo(f'\nGetInforFromUrl: {self.baseurl}{url}\nPARAMS: {params}')
        return self.get_requests().get('%s' % url, params=params, headers=headers, verify=False)

    def put(self, url, data, headers=None):
        self.logInfo(f'\nPUT: {self.baseurl}{url}\nDATA: {data}')
        return self.get_requests().put('%s%s' % (self.baseurl, url), data=(None if data is None else json.dumps(data)),
                                       headers=headers, verify=False)

    def putText(self, url, data, headers=None):
        self.logInfo(f'\nPUTTEXT: {self.baseurl}{url}\nDATA: {data}')
        return self.get_requests().put('%s%s' % (self.baseurl, url), data=data, headers=headers, verify=False)

    def post(self, url, data=None, headers=None):
        self.logInfo(f'\nPOST: {self.baseurl}{url}\nDATA: {data}')
        return self.get_requests().post('%s%s' % (self.baseurl, url), data=(None if data is None else json.dumps(data)),
                                        headers=headers, verify=False)

    def patch(self, url, data, headers=None):
        self.logInfo(f'\nPATCH: {self.baseurl}{url}\nDATA: {data}')
        return self.get_requests().patch('%s%s' % (self.baseurl, url),
                                         data=(None if data is None else json.dumps(data)), headers=headers,
                                         verify=False)

    def delete(self, url, headers=None):
        self.logInfo(f'\nDELETE: {self.baseurl}{url}')
        return self.get_requests().delete('%s%s' % (self.baseurl, url), headers=headers, verify=False)


class Utils(Requests):
    def waitForState(self, what, equalToWhat, timeout):
        while timeout > 0:
            try:
                self.logInfo(f'Utils:waitForState:  what={what}  equalToWhat={equalToWhat}')
                #self.assertEqual(what, equalToWhat)
                if what != equalToWhat:
                    raise Exception('Utils:waitForState: %s != %s'.format(what, equalToWhat))
                return True
            except:
                timeout -= 0.2
                time.sleep(0.2)
        else:
            print("Timed out after %s seconds" % (10 - timeout))
            return False

    def createFolder(self, fullPath):
        """
        Create a folder if it doesn't exists

        Parameter
           fullPath <str>: The full path and the folder name
        """
        if not os.path.exists(fullPath):
            os.makedirs(resultsFolder)

class MW(Utils):
    def __init__(self, host='localhost', port=443, authToken=None, licenseServer=None, protocol='https', enablehttp2=False, logLevel='debug'):

        self.host = host
        self.port = port
        self.protocol = protocol
        self.process = None
        self.baseurl = '%s://%s:%d' % (self.protocol, self.host, self.port)
        self.httpv2 = enablehttp2
        self.cookie = authToken
        self.headers = {'authorization': self.cookie}
        self.licenseServer = licenseServer
        self.logLevel = logLevel
        self.sessionId = None
        self.setLicenseServer()

        # Initiate a log file
        today = str(datetime.datetime.now()).split(' ')[0]
        self.writeToLogFile(f'Log date: {today}\n\n', logType='w+')

    def newSession(self, configName=None, configID=None, configJson=None, statusCode=201, sessionType='fullCore'):
        """
        :param configName:
        :param configID: specify a configID to create a new config and load the config with configID
        :param config: config in json format that will be uploaded and attached to the new session
        :return: new session ID
        """
        if sessionType == "fullCore":
            configType = "wireless-fullcore-config"

        if (configName == None and configJson == None and configID == None):
            config = {"ConfigUrl": configType}
        elif configID != None:
            config = {"ConfigUrl": configID}
        elif (configName != None):
            # in this case create a new config by loading a specified config name
            config = self.selectConfig(configName)
            uploadedConfig = self.uploadConfig(config=config)
            config = {"ConfigUrl": 'configs/' + uploadedConfig[0]['id']}
        elif (configJson != None):
            uploadedConfig = self.uploadConfig(config=configJson)
            config = {"ConfigUrl": 'configs/' + uploadedConfig[0]['id']}
        else:
            self.logError("NewSession: Unhandled case")

        response = self.post('/api/v2/sessions', config, headers=self.headers)

        assert response.status_code == statusCode
        if statusCode == 201:
            self.logDebug(pformat(response.json()))
            self.sessionId = response.json()[0]['id']
            if 'wireless' not in self.sessionId:
                raise Exception('Failed to create new session: {}'.format(self.sessionId))

            return self.sessionId
        else:
            return response.json()

    def deleteSession(self,  statusCode=204):
        if self.sessionId is None:
            return
        
        response = self.delete('/api/v2/sessions/{0}'.format(self.sessionId), headers=self.headers)
        # print response
        assert response.status_code == statusCode
        if '200' in str(response.status_code):
            assert (True if self.sessionId not in self.getAllSessions() else False)
            return response
        
        elif '204' in str(response.status_code):
            assert (True if self.sessionId not in self.getAllSessions() else False)
            return response
        
        else:
            self.logDebug(pformat(response))
            return response.status_code

    def getAllSessions(self):
        response = self.get('/api/v2/sessions', headers=self.headers)
        assert response.status_code == 200
        sessions = []
        for item in response.json():
            sessions.append(item['id'])

        return sessions

    def getSessionInfo(self,  statusCode=200):
        response = self.get('/api/v2/sessions/{0}'.format(self.sessionId), headers=self.headers)
        assert response.status_code == statusCode
        return response.json()

    def getSessionStatus(self):
        response = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
        assert response.status_code == 200
        return response.json()['status']

    def isSessionStarted(self):
        response = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
        assert response.status_code == 200
        return True if response.json()['status'] == 'Started' else False

    def pickExistingSession(self, wildcard):
        try:
            self.assertGreater(self.newSessionID, 0)
            return self.newSessionID
        except:
            allSessions = self.getAllSessions()
            for session in allSessions:
                if wildcard in session:
                    return session

    def getAllAgents(self):
        """
        :return: a list of agents
        """
        response = self.get('/api/v2/agents', headers=self.headers)
        assert response.status_code == 200
        return response.json()

    def getAgentInfo(self, agentID):
        response = self.get('/api/v2/agents/{0}'.format(agentID), headers=self.headers)
        assert response.status_code == 200
        if len(response.json()['id']) > 0:
            return response.json()
        else:
            return None

    def getSessionConfig(self,  statusCode=200):
        response = self.get('/api/v2/sessions/{0}/config?include=all'.format(self.sessionId), headers=self.headers)
        assert response.status_code == statusCode
        return response.json()['Config']

    def selectConfig(self, configName):
        #configFileName = 'configs/{0}.json'.format(configName)
        if '.json' in configName:
            configFileName = configName
        else:
            configFileName = '{0}.json'.format(configName)

        self.logInfo('Selected config file to load: {}'.format(configFileName))
        assert os.path.isfile(configFileName)

        file = open(configFileName)
        config = file.read()
        file.close()

        configJson = json.loads(config)
        #self.logDebug(pformat(configJson))
        return configJson

    def setSessionConfig(self, config, statusCode=200):
        self.headers.update({'Content-Type': 'application/json',
                             'Accept': '*/*',
                             'Cache-Control': 'no-cache',
                             'Host': '{0}'.format(self.host),
                             'Accept-Encoding': 'gzip, deflate',
                             'Referer': 'http://{0}/api/v2/sessions'.format(self.host),
                             'Postman-Token': '009256e4-5703-4564-8526-adfe3567fecd',
                             'User-Agent': 'PostmanRuntime/7.16.3',
                             'Connection': 'keep-alive'})

        if 'configData' in config:
            config = config['configData']['Config']

        response = self.put('/api/v2/sessions/{0}/config/config'.format(self.sessionId), data=config,
                            headers=self.headers)
        self.logDebug(pformat(response.content))
        self.logDebug(pformat(response.reason))
        assert response.status_code == statusCode
        try:
            return response.json()
        except:
            return response

    def startTest(self,  result='SUCCESS', wait=40, statusCode=202):
        response = self.post('/api/v2/sessions/{0}/test-run/operations/start'.format(self.sessionId), headers=self.headers)
        self.logDebug(pformat(response.content))
        self.logDebug(pformat(response.json()))

        assert response.status_code == statusCode
        waitTime = wait
        rest_url = '/api/v2/sessions/{0}/test-run/operations/start/{1}'.format(self.sessionId, response.json()['id'])

        while wait > 0:
            try:
                state = self.get(rest_url, headers=self.headers)
                # self.logDebug(pformat(state))
                # self.logDebug(pformat(state.content))

                if state.json()['state'] == result:
                    return state.json()

                if state.json()['state'] == 'ERROR':  # break when start goes to ERROR state
                    break

                wait -= 1
                time.sleep(2)
                self.logDebug(pformat(state.json()))

            except:
                return response.json()

        else:
            msg='Test failed to start in {} sec'.format(waitTime)
            self.logError(msg)

        # if state is ERROR, stop the test and print the error message.
        #assert (False, msg='State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message']))
        msg = 'State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message'])
        self.logError(msg)

    def stopTest(self,  result='SUCCESS', wait=40, statusCode=202):
        response = self.post('/api/v2/sessions/{0}/test-run/operations/stop'.format(self.sessionId), headers=self.headers)
        self.logDebug(pformat(response.content))
        self.logDebug(pformat(response.status_code))

        assert response.status_code == statusCode
        rest_url = '/api/v2/sessions/{0}/test-run/operations/stop/{1}'.format(self.sessionId, response.json()['id'])

        while wait > 0:
            try:
                state = self.get(rest_url, headers=self.headers)
                # self.logDebug(pformat(state))
                # self.logDebug(pformat(state.content))

                if state.json()['state'] == result:
                    return state.json()

                if state.json()['state'] == 'ERROR':  # break when start goes to ERROR state
                    break

                wait -= 1
                time.sleep(2)
                self.logDebug(pformat(state.json()))

            except:
                return response.json()

        else:
            #assert(False, msg='Test failed to stop')
            msg='Test failed to stop'
            self.logError(msg)

        # if state is ERROR, stop the test and print the error message.
        #assert(False, msg='State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message']))
        msg = 'State: {} - Error MSG: {}'.format(state.json()['state'], state.json()['message'])
        self.logError(msg)

    def uploadConfig(self, config, statusCode=201):
        """
        :param config: in json format
        :return:
        """
        response = self.post('/api/v2/configs', data=config, headers=self.headers)
        self.logDebug(pformat(response.content))
        self.logDebug(pformat(response.reason))
        assert response.status_code == statusCode
        return response.json()

    def getUploadedConfig(self, configID, statusCode=200):
        response = self.get('/api/v2/configs/{0}'.format(configID), headers=self.headers)
        assert response.status_code == statusCode
        return response.json()

    def checkSessionState(self,  status, waitTime=300):
        elapsedTime = 0
        testResponse = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
        while elapsedTime < waitTime and testResponse.json()['status'] != status:
            try:
                testResponse = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
            except ConnectionError as e:
                break
            
            time.sleep(5)
            elapsedTime += 5

        if testResponse.json()['status'] == False:
            # logError will raise an exception
            self.logError('The test failed to start')
            
        return True if testResponse.json()['status'] == status else False

    def setLicenseServer(self):
        response = self.get('/api/v2/globalsettings', headers=self.headers)
        #global licenseServer

        if response.json()["licenseServer"] == self.licenseServer:
            return 0
        payload = {"licenseServer": self.licenseServer}
        response = self.put('/api/v2/globalsettings', payload, headers=self.headers)

    def getTestId(self, statusCode=200):
        response = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
        assert response.status_code == statusCode
        return response.json()['testId']

    def getAllStats(self, testId, statName, statusCode=200):
        response = self.get('/api/v2/results/{0}/stats/{1}'.format(testId, statName), headers=self.headers)
        assert response.status_code == statusCode
        col = {}
        statList = []

        if response.json()['columns'][0] == "timestamp":
            try:
                for i in range(len(response.json()['columns']) - 1):
                    n = response.json()['columns'][i+1]
                    for j in range(len(response.json()['snapshots'])):
                        statList.append(float(response.json()['snapshots'][j]['values'][0][i+1]))
                    col[n] = statList
                    statList = []

                # returns a dictionary. The keys are the statistics.
                # The value for each key is a list of values with the polling interval 2 seconds.
                return col   
            except:
                self.logError("Exception raised: No stats available for {}. Test didn't run as expected".format(statName))
                pass

        else:
            try:
                # this is used for SBI stats.
                for i in range(len(response.json()['columns'])-1):      
                    n = response.json()['columns'][i+1]
                    for j in range(len(response.json()['snapshots'][0]['values'])):
                        statList.append(float(response.json()['snapshots'][0]['values'][j][i+1]))
                    col[n] = sum(statList)
                    statList = []
                return col
            except:
                self.logDebug("Exception raised: No stats available for {}. Test didn't run as expected".format(statName))
                pass

    def getMaxStat(self, stat):
        return max(stat)

    def getAvgNonZeroStat(self, stat):
        statList = []
        for i in stat:
            if i != 0:
                statList.append(i)
        if len(statList) == 0:
            # if all values are zero, return 0 - For Failed/Timeout stats
            return 0                                        
        else:
            # Returns AVG on non-zero values
            return round(sum(statList) / len(statList), 2)    

    def getTestDuration(self,  multiplier=2):
        # return total test duration x multiplier (when test takes longer because of retries)
        response = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)
        assert response.status_code == 200
        total_duration = response.json()['testDuration'] * multiplier

        return total_duration

    def getAgentsInfo(self):
        response = self.get('/api/v2/agents', headers=self.headers)
        assert response.status_code == 200
        agents=response.json()
        agents_list = []
        for agent in agents:
            interface_list = []
            for interface in agent['Interfaces']:
                interface_list.append({'Name': interface['Name'], 'Mac': interface['Mac']})
            interface_list.sort(key=lambda x: x['Name'])
            # interfaces are stored in a list.
            agents_list.append({'id':agent['id'], 'IP':agent['IP'], 'Interfaces': interface_list})  

        return agents_list

    def getAgentDetails(self, agentsInfo, agentIP):
        for agent in agentsInfo:
            if agent['IP'] == agentIP:
                return agent

    def RemapAgents(self, configToModify, agentsDict, sbaTesterTopology=False):
        import copy
        newConfig = copy.deepcopy(configToModify)
        topology = 'Config' if sbaTesterTopology is False else 'SBAConfig'

        for node in agentsDict:
            if newConfig['configData'][topology]['nodes'][node]['settings']['enable'] == True:
                path = newConfig['configData'][topology]['nodes'][node]['settings']['mappedAgents'][0]
                path['agentId'] = agentsDict[node][0]
                for i in range(len(path['interfaceMappings'])):
                    if path['interfaceMappings'][i]['agentInterface'] != 'none':
                        path['interfaceMappings'][i]['agentInterface'] = agentsDict[node][1]
                        path['interfaceMappings'][i]['agentInterfaceMac'] = agentsDict[node][2]
        return newConfig

    def getStartEndTestTimestamp(self):
        response = self.get('/api/v2/sessions/{0}/test'.format(self.sessionId), headers=self.headers)

        return response.json()['testStarted']*1000, response.json()['testStopped']*1000

    def configSustainTime(self,  sustainTime):
        # https://192.168.129.154/api/v1/sessions/1/appsec/sessions/wireless-70d29f83-cd12-414b-9c6e-e52993684ee2/config/config/nodes/ue/ranges/1/controlPlane/primaryObjective/activeSubscribers

        response = self.patch('/api/v2/sessions/{0}/config/config/nodes/ue/ranges/1/controlPlane/primaryObjective/activeSubscribers'.format(self.sessionId),
                             data={'sustain': 34}, headers=self.headers)
        assert response.status_code == 204

    def getSustainTime(self):
        response = self.get('/api/v2/sessions/{0}/config/config/nodes/ue/ranges/1/controlPlane/primaryObjective/activeSubscribers'.format(self.sessionId),
                    headers=self.headers)
        assert response.status_code == 200
        return response.json()['sustain']

    def createHTMLreport(self,  listOfStatistics, reportName, startTime, endTime,
                         logoFolder=None, resultFolder=None):
        if resultFolder:
            self.createFolder(resultFolder)
            
        html = self.getHTML(listOfStatistics, reportName, startTime, endTime)
        foldername = 'LoadCore_{}_{}/'.format(reportName, startTime.strftime('%Y%m%d_%H%M%S'))
        destinationPath = '{}/{}/'.format(resultFolder, foldername)
        os.makedirs(destinationPath, exist_ok=True)
        filename = destinationPath + 'LoadCore_{}_{}'.format(reportName, startTime.strftime('%Y%m%d_%H%M%S'))
        filename = '{}.html'.format(filename)
        self.logInfo('\ncreateHTMLreport: filename: {}'.format(filename))
        
        with open(filename, 'w') as f:
            f.write(html)

        shutil.copy("{}/keysightlogo.png".format(logoFolder), destinationPath)
        shutil.copy("{}/loadcorelogo.PNG".format(logoFolder), destinationPath)

        return filename
    
    def getHTML(self, statsList, reportName, startTime, endTime):
        testId = self.getTestId()
        t1, t2 = self.getStartEndTestTimestamp()
        data = {}
        l = []
        start = startTime.strftime('%Y-%m-%d %H:%M:%S')
        end = endTime.strftime('%Y-%m-%d %H:%M:%S')

        html = """<html><head>
                <style>
                .collapsible {
                background-color: #282828;
                color: white;
                cursor: pointer;
                padding: 18px;
                width: 100%;
                border: none;
                text-align: left;
                outline: none;
                font-size: 15px;
                }

                .active, .collapsible:hover {
                background-color: #808080;
                }
                .collapsible:after {
                content: '\\002B';
                color: white;
                font-weight: bold;
                float: right;
                margin-left: 5px;
                }

                .active:after {
                content: "\\2212";
                }


                .content {
                display: inline-block;
                padding: 0 18px;
                max-height: 0;
                overflow: hidden;
                transition: max-height 0.2s ease-out;
                overflow: hidden;
                background-color: white;
                }

                .column {
				  float: left;
				  padding: 1px;
				}

				.row:after {
				  content: "";
				  display: table;
				  clear: both;
				}
				.left {
				  width: 20%;
				}
				.middle {
				  width: 15%;
                  color: #282828;
				}
				.right {
				  float: right;
				  width: 20%;
				}
                </style>
                </head>
                <body>
                <div class="row">
					<div class="column left">
						<img src="loadcorelogo.PNG",
						 height = 48 width = 158/>
					</div>
                """
        session = self.getSessionInfo()
        html += '<div class="column middle"><center><b>{}</b></center></div>'.format(session['ownerID'])
        html += '<div class="column middle"><center><b>{}</b></center></div>'.format(reportName)
        html += '<div class="column middle"><center><b>{}</b></center></div>'.format(start)
        html += '<div class="column middle"><center><b>{}</b></center></div>'.format(end)

        html += """<div class="column right"><img src="keysightlogo.PNG",
						height = 48 width = 158 style="float:right;margin-top: -25px;"/>
					</div>
				</div>
                """

        for stat in statsList:
            response = self.get('/api/v2/results/{}/stats/{}?from={}'.format(testId, stat, t1), headers=self.headers)
            try:
                if response.json()['columns'][0] == "timestamp":
                    for i in range(len(response.json()['columns'])):
                        n = response.json()['columns'][i]
                        for j in range(len(response.json()['snapshots'])):
                            if n == 'timestamp':
                                t = float(response.json()['snapshots'][j]['values'][0][i])/1000
                                l.append(datetime.datetime.fromtimestamp(t) .strftime('%Y-%m-%d %H:%M:%S'))
                            else:
                                l.append(response.json()['snapshots'][j]['values'][0][i])
                        data[n] = l
                        l = []

                    html += '<button type="button" class="collapsible">{}</button><div class="content">'.format(stat)
                    html += '<table border="1"><tr><th>' + '</th><th>'.join(data.keys()) + '</th></tr>'

                    for row in zip(*data.values()):
                        html += '<tr><td>' + '</td><td>'.join(row) + '</td></tr>'

                    html += '</table></div>'
                    data.clear()

                else:
                    for i in range(len(response.json()['columns'])):
                        n = response.json()['columns'][i]
                        for j in range(len(response.json()['snapshots'][0]['values'])):
                            l.append(response.json()['snapshots'][0]['values'][j][i])
                        data[n] = l
                        l = []

                    html += '<button type="button" class="collapsible">{}</button><div class="content">'.format(stat)
                    html += '<table border="1"><tr><th>' + '</th><th>'.join(data.keys()) + '</th></tr>'

                    for row in zip(*data.values()):
                        html += '<tr><td>' + '</td><td>'.join(row) + '</td></tr>'

                    html += '</table></div>'
                    data.clear()

            except:
                self.logDebug("Exception raised: No stats available for {} view.".format(stat))
                pass

        #print(data)

        html += """
                </body>
                <script>
                var coll = document.getElementsByClassName("collapsible");
                var i;

                for (i = 0; i < coll.length; i++) {
                coll[i].addEventListener("click", function() {
                    this.classList.toggle("active");
                    var content = this.nextElementSibling;
                    if (content.style.maxHeight){
                    content.style.maxHeight = null;
                    } else {
                    content.style.maxHeight = content.scrollHeight + "px";
                    }
                });
                }
                </script>
                </html>
                """

        return html

    def getPDFreport(self,  folderName, startTime, resultFolder=None, wait=40, statusCode=202):
        if resultFolder:
            self.createFolder(resultFolder)

        testID = self.getTestId()

        response = self.post('/api/v2/results/{0}/operations/generate-pdf'.format(testID), headers=self.headers)
        assert response.status_code == statusCode

        operation_url = '/api/v2/results/{0}/operations/generate-pdf/{1}'.format(testID, response.json()['id'])

        while wait > 0:
            state = self.get(operation_url, headers=self.headers)
            self.logDebug(pformat(state.json()))

            if state.json()['state'] == 'SUCCESS':
                pdfReport = self.get(state.json()['resultUrl'], headers=self.headers)
                break

            if state.json()['state'] == 'ERROR':
                assert(False, 'Could not get the pdf report')

            wait -= 5
            time.sleep(5)

        else:
            assert(False, 'Failed to download the pdf report. Try increasing the wait time.')

        foldername = 'LoadCore_{}_{}/'.format(folderName, startTime.strftime('%Y%m%d_%H%M%S'))
        destinationPath = '{}/{}'.format(resultFolder, foldername)
        os.makedirs(destinationPath, exist_ok=True)
        filename = '{0}/{1}'.format(destinationPath, pdfReport.headers['Content-Disposition'].split("=")[1].strip('\"'))

        self.logInfo('getPDFreport: filename: {}'.format(filename))
        
        with open(filename, 'wb') as f:
            f.write(pdfReport.content)

        return filename

    def getCSVs(self, folder, startTime, resultFolder=None, wait=40, statusCode=202):
        if resultFolder:
            self.createFolder(resultFolder)

        testID = self.getTestId()

        response = self.post('/api/v2/results/{0}/operations/generate-csv'.format(testID), headers=self.headers)
        assert response.status_code == statusCode

        operation_url = '/api/v2/results/{0}/operations/generate-csv/{1}'.format(testID, response.json()['id'])

        while wait > 0:
            state = self.get(operation_url, headers=self.headers)
            self.logDebug(pformat(state.json()))

            if state.json()['state'] == 'SUCCESS':
                archive = self.get(state.json()['resultUrl'], headers=self.headers)
                break

            if state.json()['state'] == 'ERROR':
                assert(False, 'Could not get the results archive')

            wait -= 5
            time.sleep(5)

        else:
            assert(False, 'Failed to download the results archive. Try increasing the wait time.')

        foldername = 'LoadCore_{}_{}/'.format(folder, startTime.strftime('%Y%m%d_%H%M%S'))
        destinationPath = '{}/{}'.format(resultFolder, foldername)
        os.makedirs(destinationPath, exist_ok=True)
        filename = '{0}/{1}'.format(destinationPath, archive.headers['Content-Disposition'].split("=")[1].strip('\"'))
        self.logInfo('getCSVs: filename: {}'.format(filename))

        with open(filename, 'wb') as f:
            f.write(archive.content)

        return filename
    
    def getCapturedLogs(self, resultFolder=None, wait=40, statusCode=202):
        if resultFolder:
            self.createFolder(resultFolder)

        testID = self.getTestId()

        response = self.post('/api/v2/results/{0}/operations/export-results'.format(testID), headers=self.headers)
        assert response.status_code == statusCode

        operation_url = '/api/v2/results/{0}/operations/generate-results/{1}'.format(testID, response.json()['id'])

        while wait > 0:
            state = self.get(operation_url, headers=self.headers)
            self.logDebug(pformat(state.json()))

            if state.json()['state'] == 'SUCCESS':
                archive = self.get(state.json()['resultUrl'], headers=self.headers)
                break

            if state.json()['state'] == 'ERROR':
                self.logError('Could not get the captures/logs archive')

            wait -= 5
            time.sleep(5)

        else:
            self.logError('Failed to download the capture')

        filename = '{0}/{1}'.format(resultFolder, archive.headers['Content-Disposition'].split("=")[1])
        self.logInfo('getCapturedLogs: filename: {}'.format(filename))
        os.makedirs(resultFolder, exist_ok=True)
        
        with open(filename, 'wb') as f:
            f.write(archive.content)

        return filename


class LoadCoreAssistantException(Exception):
    def __init__(self, msg=None):
        if platform.python_version().startswith('3'):
            super().__init__(msg)

        if platform.python_version().startswith('2'):
            super(LoadCoreException, self). __init__(msg)

        showErrorMsg = '\nLoadCoreAssistantException: {}\n\n'.format(msg)
        print(showErrorMsg)

        with open(MW.debugLogFile, 'a') as logFile:
            logFile.write(showErrorMsg)
