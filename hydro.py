#!/usr/bin/python3

#
# Jfree  -  hydro.py
# The purpose of this script is to access hydrological data from
# water.weather.gov and track the water level for a local body of water.
# If the water level breaches predefined flood limits, a warning e-mail
# is sent out along with a graph of the historical water levels.
#
# Note: This code can be generalized with minor modification to pull
# data for any body of water tracked by weather.gov.
#


import requests
import pandas as pd
import matplotlib.pyplot as plt
import smtplib, ssl

from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import date
from config import Config
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
plt.style.use('seaborn-darkgrid')


#########################
# Function definitions
#########################
def get_top(soup):
    '''
    Parameters
    ----------
    soup : BeautifulSoup object

    Returns
    -------
    top : tuple
        Returns the most recent measurement.
    '''
    children = list(soup[1].children)
    top = (children[1].contents[0], \
           float(children[3].contents[0][:5]))
    return top

def get_last_twelve_hrs(soup):
    '''
    Parameters
    ----------
    soup : BeautifulSoup object

    Returns
    -------
    last_twelve : pd.Series object
        Returns the most recent measurement.
    '''
    datetimes = []
    data = []
    
    # Extract contents contained in the tags.
    # Twelve hours corresponds to 48 observations.
    for row in soup[:48]:
        i=0
        for item in row.children:
            if type(item) == Tag:
                if i==1:
                    datetimes.append(item.contents[0])
                elif i==3:
                    data.append(item.contents[0][:5])
            i=i+1

    # Reformat data.
    datetimes = datetimes[1:]
    data = [float(i) for i in data[1:]]
    datetimes.reverse()
    data.reverse()
    last_twelve = pd.Series(index=datetimes[1:], data=data[1:])

    return last_twelve
    

    
def get_image(soup,
              limits=[14,14.5,16.5,18.5],
              show=True):
    '''
    Parameters
    ----------
    soup : BeautifulSoup object

    limits : Vertical reference lines to plot

    show : Boolean. If True, show plot. If False, do not show.

    Returns
    -------
    img : matplotlib image
        Returns time series plot of measurements.
    '''
    datetimes = []
    data = []
    
    # Extract contents contained in the tags.
    for row in soup:
        i=0
        for item in row.children:
            if type(item) == Tag:
                if i==1:
                    datetimes.append(item.contents[0])
                elif i==3:
                    data.append(item.contents[0][:5])
            i=i+1

    # Reformat data.
    datetimes = datetimes[1:]
    data = [float(i) for i in data[1:]]
    datetimes.reverse()
    data.reverse()

    # Organize data into a series and plot.
    series = pd.Series(index=datetimes[1:], data=data[1:])
    img = series.plot()
    
    plt.xticks(rotation=90)
    plt.ylabel("Water Level (ft)")
    plt.title("Black Creek Water Level, near Blanding")
    plt.tight_layout()
    if len(limits)!=0:
        start = 0
        step = (1/len(limits))
        for ref in limits:
            img.axhline(ref, color=(start,.1,0))
            start=start+step
    #img.legend(labels=['Level','Action', 'Minor', 'Mod.', 'Major'], loc=(.8,16.7))
    if show == True:
        #plt.show()
        pass
    return img

def get_warning_msg(img_id, max_level):
    msg = \
    '''
    <html>
    <body>
    <h3>Black Creek Water Level Warning Issued {} ft</h3>
    <br>
    <p>Note: The maximum water level in the last 12 hrs reached {}.</p>
    <p>See the attached image and assess the situation using appropriate
    information from local meterological sources.</p>
    <br>
    <img src="cid:{}">
    
    '''.format(date.today(), max_level, img_id)
    return msg

#############################
# Body
#############################

# Pull hydrograph data from here. This is for little Black Creek
# near Blanding Blvd, Middleburg FL.
# To find a body of water near you, navigate to water.weather.gov
# and search for a sensor on the provide map. You can find the
# source data quite easily from there.
url = 'https://water.weather.gov/'+ \
       'ahps2/hydrograph_to_xml.php?gage=bcmf1&output' + \
       '=tabular&time_zone=edt'

# Request webpage from weather.gov,
# grab hydrology data, and close the session.
r = requests.get(url)
if r.ok == True:
    text = r.text
else:
    raise Exception("Connection to webpage was no good.")
r.close()

# Soupify the raw html.
# Note: each row is contained in a <tr> element.
soup = BeautifulSoup(text, features='lxml').findAll('tr')

# Get data starting at the header
soup = soup[2:]

# If max observation in last 12 hours is within 1% of warning limit,
# get plot of data.
# Additionally create formatted HTML messages to send out as an alert.
last_twelve_hrs = get_last_twelve_hrs(soup)
largest_obs = max(last_twelve_hrs)
if largest_obs >= 13.86:  # 99% of 14 = 13.86
    image = get_image(soup)

    port = 465  # For SSL
    # Import your password from the Config package.
    password = Config.password
    # Create a secure SSL context
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        sender_email = 'SENDER-EMAIL-HERE'
        receiver_email = 'RECEIVER-EMAIL-HERE'
        server.login(sender_email, password)

        # Some modified boilerplate code below to handle the e-mail.
        # See stackoverflow -> Andrew Hare.
        
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = 'Potential Flood Warning {}'.format(date.today)
        msgRoot['From'] = sender_email
        msgRoot['To'] = receiver_email
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        
        msgText = MIMEText('This is the alternative plain text message.')
        msgAlternative.attach(msgText)
    
        # Must save a temporary copy of graph and read as bytes.
        plt.savefig("./tmpfile", format='png')
        fp = open('./tmpfile', 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        
        msgImage.add_header('Content-ID', '<graph>')
        msgRoot.attach(msgImage)
        
        msgText = MIMEText(get_warning_msg('graph',largest_obs), 'html')
        msgAlternative.attach(msgText)
        

        server.sendmail(sender_email, receiver_email, msgRoot.as_string())







    
    
