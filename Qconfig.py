with open('APItoken.txt') as f:
    APItoken = f.readlines()[0].rstrip('\n')

config = {
    'url': 'https://quantumexperience.ng.bluemix.net.api',
    'hub': None,
    'group': None,
    'project': None
}

if 'APItoken' not in locals():
    raise Exception('Please set up your access token. See Qconfig.py')
