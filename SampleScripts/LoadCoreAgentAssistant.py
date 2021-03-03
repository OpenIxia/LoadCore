"""
LoadCoreAgentAssistant.py

An API library to control LoadCore Agents.
This library inherits the LoadCoreMWAssistant.py module to send REST APIs.

Requirements
   - requests
   - LoadCoreMWAssistant.py

Notes:
   - Don't use print()
   - To log messages on stdout and log messages in the debug log file, use:
      - self.logInfo, self.logDebug, self.logError

      - These are inherited from the Requests class

"""

from LoadCoreMWAssistant import Requests, LoadCoreAssistantException

class Agent(Requests):
    def __init__(self, agentIp):
        """
        Each LoadCore agent must have its own class object

        Parameter
           agentIp <str>: The Agent's IP address
        """
        self.agentIp = agentIp
        self.httpv2 = False
        self.baseurl = f'http://{self.agentIp}'
        self.headers = {'Content-Type': 'application/json'}

    def enableFilter(self, interface):
        """
        Enable filter for capturing

        Parameter
           interface <str>: The agent's traffic interface: "-i ens192"
        """
        url = '/api/v1/capture/filter'
        params = {'value': f'-i {interface}'}
        response = self.patch(url, params, headers=self.headers)
        assert response.status_code == 204

    def getFilter(self):
        """
        Return
           {'value': '-i ens160'}
        """
        url = '/api/v1/capture/filter'
        response = self.get(url, headers=self.headers)
        assert response.status_code == 200
        return response.json()
    
    def startCapture(self):
        """
        Enable capturing.  This API requires enabling filter interface.
        """
        url = '/api/v1/capture/start'
        response = self.post(url, headers=self.headers)
        assert response.status_code == 200

    def stopCapture(self):
        url = '/api/v1/capture/stop'
        response = self.post(url, headers=self.headers)
        assert response.status_code == 204

    def getCaptureStatus(self):
        """
        Return: 
           running|stopped
        """
        url = '/api/v1/capture/status'
        response = self.get(url, headers=self.headers)
        assert response.status_code == 200
        return response.json()['state']
    
