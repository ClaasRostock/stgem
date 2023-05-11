'''
Stanley Bak
Python F-16 GCAS
'''

def tgear(thtl):
    'tgear function'

    return 64.94 * thtl if thtl <= .77 else 217.38 * thtl - 117.38
