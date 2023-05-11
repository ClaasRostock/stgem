'''
Stanley Bak
Python F-16

Rtau function
'''

def rtau(dp):
    'rtau function'

    if dp <= 25:
        return 1.0
    elif dp >= 50:
        return .1
    else:
        return 1.9 - .036 * dp
