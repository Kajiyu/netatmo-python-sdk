# coding=utf-8

from sys import version_info, version
import json, time
from config import *

if version_info.major == 3 :
    import urllib.parse, urllib.request
else:
    from urllib import urlencode
    import urllib2


#Common Definition########
_BASE_URL       = "https://api.netatmo.net/"
_AUTH_REQ       = _BASE_URL + "oauth2/token"
_GETUSER_REQ    = _BASE_URL + "api/getuser"
_DEVICELIST_REQ = _BASE_URL + "api/devicelist"
_GETMEASURE_REQ = _BASE_URL + "api/getmeasure"
_ADDWEBHOOK_REQ = _BASE_URL + "api/addwebhook"
_DROPWEBHOOK_REQ = _BASE_URL + "api/dropwebhook"

#For Welcome Api###########
_GETHOMEDATA_REQ = _BASE_URL + "api/gethomedata"
_GETNEXTEVENTS_REQ = _BASE_URL + "api/getnextevents"
_GETLASTEVENTOF_REQ = _BASE_URL + "api/getlasteventof"
_GETEVENTSUNTIL_REQ = _BASE_URL + "api/geteventsuntil"
_GETCAMERAPICTURE_REQ = _BASE_URL + "api/getcamerapicture"
###########################


#Utilities############
def postRequest(url, params):
    # Netatmo response body size limited to 64k (should be under 16k)
    if version_info.major == 3:
        req = urllib.request.Request(url)
        req.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
        params = urllib.parse.urlencode(params).encode('utf-8')
        resp = urllib.request.urlopen(req, params).read(65535).decode("utf-8")
    else:
        params = urlencode(params)
        headers = {"Content-Type" : "application/x-www-form-urlencoded;charset=utf-8"}
        req = urllib2.Request(url=url, data=params, headers=headers)
        resp = urllib2.urlopen(req).read(65535)
    return json.loads(resp)

def toTimeString(value):
    return time.strftime("%Y-%m-%d_%H:%M:%S", time.localtime(int(value)))

def toEpoch(value):
    return int(time.mktime(time.strptime(value,"%Y-%m-%d_%H:%M:%S")))

def todayStamps():
    today = time.strftime("%Y-%m-%d")
    today = int(time.mktime(time.strptime(today,"%Y-%m-%d")))
    return today, today+3600*24
##################


####First Auth######
class ClientAuth:
    def __init___(self, clientId=_CLIENT_ID,clientSecret=_CLIENT_SECRET,username=_USERNAME,password=_PASSWORD, scope):
        postParams = {
                "grant_type" : "password",
                "client_id" : clientId,
                "client_secret" : clientSecret,
                "username" : username,
                "password" : password,
                "scope" : scope
                }
        resp = postRequest(_AUTH_REQ, postParams)
        self._clientId = clientId
        self._clientSecret = clientSecret
        self._accessToken = resp['access_token']
        self.refreshToken = resp['refresh_token']
        self._scope = resp['scope']
        self.expiration = int(resp['expire_in'] + time.time())

    @property
    def accessToken():
        if self.expiration < time.time(): # Token should be renewed
        postParams = {
                    "grant_type" : "refresh_token",
                    "refresh_token" : self.refreshToken,
                    "client_id" : self._clientId,
                    "client_secret" : self._clientSecret
                    }
        resp = postRequest(_AUTH_REQ, postParams)
        self._accessToken = resp['access_token']
        self.refreshToken = resp['refresh_token']
        self.expiration = int(resp['expire_in'] + time.time())
        return self._accessToken
####################################


###User Class#######################
class User:
    def __init__(self, authData):
        postParams = {"access_token" : authData.accessToken}
        resp = postRequest(_GETUSER_REQ, postParams)
        self.rawData = resp['body']
        self.id = self.rawData['_id']
        self.devList = self.rawData['devices']
        self.ownerMail = self.rawData['mail']
#####################################

#####DeviceList Class############
class DeviceList:
    def __init__(self, authData):

        self.getAuthToken = authData.accessToken
        postParams = {
                "access_token" : self.getAuthToken,
                "app_type" : "app_station"
                }
        resp = postRequest(_DEVICELIST_REQ, postParams)
        self.rawData = resp['body']
        self.stations = { d['_id'] : d for d in self.rawData['devices'] }
        self.modules = { m['_id'] : m for m in self.rawData['modules'] }
        self.default_station = list(self.stations.values())[0]['station_name']

    def modulesNamesList(self, station=None):
        res = [m['module_name'] for m in self.modules.values()]
        res.append(self.stationByName(station)['module_name'])
        return res

    def stationByName(self, station=None):
        if not station : station = self.default_station
        for i,s in self.stations.items():
            if s['station_name'] == station :
                return self.stations[i]
        return None

    def stationById(self, sid):
        return None if sid not in self.stations else self.stations[sid]

    def moduleByName(self, module, station=None):
        s = None
        if station :
            s = self.stationByName(station)
            if not s :
                return None
        for m in self.modules:
            mod = self.modules[m]
            if mod['module_name'] == module :
                if not s or mod['main_device'] == s['_id'] :
                    return mod
        return None

    def moduleById(self, mid, sid=None):
        s = self.stationById(sid) if sid else None
        if mid in self.modules :
            return self.modules[mid] if not s or self.modules[mid]['main_device'] == s['_id'] else None

###################################

####HomeData###########
class HomeData:
    def __init__(self, authData):
        self.getAuthToken = authData.accessToken
        postParams = {
            "access_token" : self.getAuthToken
            }
        resp = postRequest(_GETHOMEDATA_REQ, postParams)
        self.rawData = resp['body']
        self.default_home = self.rawData['homes'][0]
        self.default_home_name = self.default_home['name']
        self.default_home_id = self.default_home['id']
        self.homes = { d['_id'] : d for d in self.rawData['homes'] }
        self.status = resp['status']
        self.time_exec = resp['time_exec']
        self.time_server = resp['time_server']
        self.users = self.rawData['user']

    def getHomeById(self, hid=None):
        return None if hid not in self.homes else self.homes[hid]

    def getHomeByName(self, home_name=None):
        if not home_name : home_name = self.default_home_name
        for i,s in self.homes.items():
            if s['name'] == home_name :
                return self.homes[i]
        return None

    def getPersons(self, home=None):
        if not home : home = self.default_home
        return home['persons']

    def getEvents(self, home=None):
        if not home : home = self.default_home
        return home['events']

    def getCameras(self, home=None):
        if not home : home = self.default_home
        return home['cameras']

#####################################



#########NextEvent###################

class NextEvent:
    def __init__(self, authData, home, event_id, event_number=30):
        self.getAuthToken = authData.accessToken
        postParams = {
            "access_token" : self.getAuthToken,
            "home_id" : home.default_home_id,
            "event_id" : event_id,
            "size" : event_number
        }
        resp = postRequest(_GETNEXTEVENTS_REQ, postParams)
        self.rawData = resp['body']
        self.eventList = rawData['events_list']

    def getEventByOrder(self, number):
        if number > len(self.eventList):
            print("Error! No Number")
            return
        else:
            return self.eventList[number]

    def getEventbyId(self, id):
        for i,s in self.eventList.items():
            if s['id'] == id :
                return self.eventList[i]
        return None

    def getSnapShotOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['snapshot']

    def getMessageOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['message']

    def getCameraIdOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['camera_id']

    def getTypeOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['type']

    def getTimeOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['time']

#####################################

##############LastEvent##############

class LastEvent:
    def __init__(self, authData, home, event_id, event_number=10):
        self.getAuthToken = authData.accessToken
        postParams = {
            "access_token" : self.getAuthToken,
            "home_id" : home.default_home_id,
            "event_id" : event_id,
            "offset" : event_number
        }
        resp = postRequest(_GETLASTEVENTOF_REQ, postParams)
        self.rawData = resp['body']
        self.eventList = rawData['events_list']

    def getEventByOrder(self, number):
        if number > len(self.eventList):
            print("Error! No Number")
            return
        else:
            return self.eventList[number]

    def getEventbyId(self, id):
        for i,s in self.eventList.items():
            if s['id'] == id :
                return self.eventList[i]
        return None

    def getSnapShotOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['snapshot']

    def getMessageOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['message']

    def getCameraIdOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['camera_id']

    def getTypeOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['type']

    def getTimeOfEvent(self, event=None):
        if not event : event = self.eventList[0]
        return event['time']

#####################################

############CameraPicture###########

class CameraPicture:
    def __init__(self, image_id, key):
        self.getAuthToken = authData.accessToken
        postParams = {
            "access_token" : self.getAuthToken,
            "image_id" : image_id,
            "key" : key
        }
        resp = postRequest(_GETCAMERAPICTURE_REQ, postParams)
        self.rawData = resp['body']

####################################

################Ping################

class Ping:
    def __init__():
        return

    def getPing(vpn_url):
        if version_info.major == 3:
            req = urllib.request.Request(url)
            req.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
            resp = urllib.request.urlopen(req).read(65535).decode("utf-8")
        else:
            params = urlencode(params)
            headers = {"Content-Type" : "application/x-www-form-urlencoded;charset=utf-8"}
            req = urllib2.Request(url=url, headers=headers)
            resp = urllib2.urlopen(req).read(65535)
        ping = json.loads(resp)
        return ping

####################################

###############LiveVideo############

class LiveVideo:
    def __init__(self, vpn_url):

####################################

from sys import exit, stdout, stderr
if __name__ == '__main__':
