from sys import exit


def load_correct_creds(creds):
    try:

        return creds['prod']['access_key'], creds['prod']['secret_key'], creds['prod']['passphrase']
    
    except TypeError as te:
        message = 'Your credentials are formatted incorectly\n'
        message += f'TypeError:Exception:\n\t{str(te)}'
        exit(message)
    except Exception as e:
        message = 'oopsies, looks like you did something real bad. Fallback Exception caught...\n'
        message += f'Exception:\n\t{str(e)}'
        exit(message)
        
def load_discord_creds(creds):
    return creds['discord']['DISCORD_WEBHOOK']
