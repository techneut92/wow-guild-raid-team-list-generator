import requests
import json
from multiprocessing import Process, Queue
import time

# Script doesn't work with china. it might with taiwan?
# script has to be edited at get_access_token and set  the correct url to work with chinese data

API_CLIENT_ID = ""
API_CLIENT_SECRET = ""
API_REGION = "eu"                       # eu, us, etc  -> NOT CHINA
API_LOCALE = "en_GB"                    # en_GB, en_US, de_DE, etc
GUILD_NAME = "potato farmers"
GUILD_REALM = "doomhammer"
MEMBER_MIN_ILVL = "370"                 # Minimum item level to get in the list.
RAID_PROG = 'Battle of Dazar\'alor'     # raid name to get progression on
CHARACTER_FILE = 'characterlist.txt'    # File to save the character list too.
MAX_RETRIES = 10                        # maximum amount of retries on fetching a character

def classIntToStr(id):
    switcher = {
        1: 'Warrior',
        2: 'Paladin',
        3: 'Hunter',
        4: 'Rogue',
        5: 'Priest',
        6: 'Death Knight',
        7: 'Shaman',
        8: 'Mage',
        9: 'Warlock',
        10: 'Monk',
        11: 'Druid',
        12: 'Demon Hunter'
    }
    return switcher.get(id)

def get_access_token():
    d = requests.get('https://{0}.battle.net/oauth/token?grant_type=client_credentials&client_id={1}&client_secret={2}'.format(
        API_REGION, API_CLIENT_ID, API_CLIENT_SECRET
    ))
    jd = json.loads(d.text)
    return jd['access_token']


class MPool(Process):
    def __init__(self, q, members, access_token, workers=5):
        super().__init__()
        self.members = members
        self.q = q
        self.processes = []
        self.workers = workers
        self.access_token = acces_token

    @staticmethod
    def process_member(d, token, q):
        dt = requests.get("https://{0}.api.blizzard.com/wow/character/{1}/{2}?fields=progression%2Citems&locale={3}&access_token={4}".format(
            API_REGION, d['character']['realm'], d['character']['name'], API_LOCALE, token
        ))
        retries = 0
        while not dt.status_code == 200 and retries <= MAX_RETRIES:
            dt = requests.get("https://{0}.api.blizzard.com/wow/character/{1}/{2}?fields=progression%2Citems&locale={3}&access_token={4}".format(
                API_REGION, d['character']['realm'], d['character']['name'], API_LOCALE, token
            ))
            retries += 1
            if retries == MAX_RETRIES:
                print("Error fetching data for: {0}-{1}, status code: {2}".format(d['character']['name'], d['character']['realm'], dt.status_code))
            time.sleep(1)
        jdata2 = json.loads(dt.text)
        if 'items' in jdata2 and jdata2['items']['averageItemLevel'] >= 370:
            lfr = 0
            normal = 0
            heroic = 0
            lfr_last_kill = "0"
            normal_last_kill = "0"
            heroic_last_kill = "0"
            boss_count = 0
            for rdata in jdata2['progression']['raids']:
                if rdata['name'] == RAID_PROG:
                    i = 0
                    boss_count = len(rdata['bosses'])
                    for boss in rdata['bosses']:
                        if boss['lfrKills'] > 0:
                            lfr += 1
                        if boss['normalKills'] > 0:
                            normal += 1
                        if boss['heroicKills'] > 0:
                            heroic += 1
                        i += 1
                        if i == boss_count:
                            if boss['lfrKills'] > 0:
                                lfr_last_kill = str(boss['lfrKills'])
                            if boss['normalKills'] > 0:
                                normal_last_kill = str(boss['normalKills'])
                            if boss['heroicKills'] > 0:
                                heroic_last_kill = str(boss['heroicKills'])
            tab = "\t"
            tab2 = "\t"
            if len(jdata2['name']) < 8:
                tab = tab + "\t"
            if jdata2['class'] == 8 or jdata2['class'] == 10 or jdata2['class'] == 4 or jdata2['class'] == 11:
                tab2 = "\t\t"
            strr = "{0}{1}| {2}{3}| {4} | LFR: {5}/{6} ({7}) | N: {8}/{9} ({10}) | HC: {11}/{12} ({13}) |".format(
                jdata2['name'], tab, classIntToStr(jdata2['class']), tab2, jdata2['items']['averageItemLevel'], lfr,
                boss_count, lfr_last_kill, normal, boss_count, normal_last_kill, heroic, boss_count, heroic_last_kill
            )
            print(strr)
            q.put(strr)

    def run(self):
        running = True
        if len(self.processes) == 0:
            for i in range(0, self.workers):
                m = self.members.pop()
                pr = Process(target=self.process_member, args=(m, self.access_token, self.q))
                pr.start()
                self.processes.append(pr)
        while running:
            for i in range(0, len(self.processes)):
                if not self.processes[i].is_alive() and len(self.members) > 0:
                    m = self.members.pop()
                    pr = Process(target=self.process_member, args=(m, self.access_token, self.q))
                    pr.start()
                    self.processes[i] = pr
                elif len(self.members) == 0:
                    running = False
                    for p in self.processes:
                        p.join()
                    f = open(CHARACTER_FILE, 'a')
                    while self.q.qsize() > 0:
                        f.write(self.q.get())
                        f.write("\n")
                    f.flush()
                    f.close()
            time.sleep(0.001)


if __name__ == '__main__':
    open(CHARACTER_FILE, 'w+')
    acces_token = get_access_token()
    data = requests.get(
        "https://{0}.api.blizzard.com/wow/guild/{1}/{2}?fields=members&locale=en_GB&access_token={3}".format(
            API_REGION, GUILD_REALM, GUILD_NAME, acces_token))
    jdata = json.loads(data.text)
    qu = Queue()
    pl = MPool(qu, jdata['members'], acces_token, 50)
    pl.start()
    pl.join()
    k = input("done... press any key to exit")
