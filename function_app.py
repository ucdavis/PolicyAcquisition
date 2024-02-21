import azure.functions as func
import datetime
import json
import logging

from download_ucop_policies import download_ucop

app = func.FunctionApp()

# get timestamp
def utc_timestamp() -> str:
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()

@app.timer_trigger(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def ProcessUcop(myTimer: func.TimerRequest) -> None:
    print('Python timer trigger function ran at %s', utc_timestamp())
    
    logging.info('Starting Ucop Download %s', utc_timestamp())
    
    # Download the UCOP policies
    download_ucop()
    
    logging.info('Ucop Download Complete %s', utc_timestamp())

    # TODO: convert the downloaded PDFs to text

    if myTimer.past_due:
        logging.info('The timer is past due!')
