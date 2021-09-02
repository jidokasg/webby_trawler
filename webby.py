import streamlit as st
import traceback
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
import datetime
import sqlite3
import os
import shutil
import re
from glob2 import glob



st.set_page_config(layout="centered")
#==============================================================================
vol_url = []
vol_title = []
num_complete = 0
#==============================================================================
if st.button('truncate'):
    conn = sqlite3.connect('fsi.db')
    conn.execute('''DELETE from fsi_results''')
    conn.commit()
    #conn.execute('''CREATE TABLE fsi_results
    #        (JOURNAL   VARCHAR,
    #        VOL_TITLE  VARCHAR,
    #        VOL_URL    VARCHAR,
    #        ARTICLE_TITLE  VARCHAR    PRIMARY KEY,
    #        ARTICLE_URL    VARCHAR,
    #        DOWNLOAD    VARCHAR,
    #        LAST_DOWNLOAD_DATE  VARCHAR,
    #       CRAWL_DATE);''')


    #print("Table created successfully")

    conn.close()

@st.cache

def load_data(nrows):
    data = pd.read_csv(DATA_URL, nrows=nrows)
    lowercase = lambda x: str(x).lower()
    data.rename(lowercase, axis='columns', inplace=True)
    data[DATE_COLUMN] = pd.to_datetime(data[DATE_COLUMN])
    return data

# Create a text element and let the reader know the data is loading.
#data_load_state = st.text('Loading data...')

# Notify the reader that the data was successfully loaded.
#data_load_state.text("Cache Loaded! (using st.cache)")


#====== DOWNLOAD FILE FUNCTION ======#

def download_link(object_to_download, download_filename, download_link_text):
    
    #Generates a link to download the given object_to_download.

    #object_to_download (str, pd.DataFrame):  The object to be downloaded.
    #download_filename (str): filename and extension of file. e.g. mydata.csv, some_txt_output.txt
    #download_link_text (str): Text to display for download link.

    #Examples:
    #download_link(YOUR_DF, 'YOUR_DF.csv', 'Click here to download data!')
    #download_link(YOUR_STRING, 'YOUR_STRING.txt', 'Click here to download your text!')

    if isinstance(object_to_download,pd.DataFrame):
        object_to_download = object_to_download.to_csv(index=False)

    # some strings <-> bytes conversions necessary here
    b64 = base64.b64encode(object_to_download.encode()).decode()

    return f'<a href="data:file/txt;base64,{b64}" download="{download_filename}">{download_link_text}</a>'

#======================================


def getdesktoppath ():
    return os.path.join (os.path.expanduser ("~"), "desktop")


#Website loading function
#==============================================================================
def get_url_and_wait_for_page_load(_driver, url):
    driver.get(url)
    WebDriverWait(driver, 60).until(
        EC.visibility_of_all_elements_located((By.XPATH, "//div[@class = 'app sd-flex-container']")))
#==============================================================================

def get_url_for_download(driver,url):
    driver.get(url)


#Load chromedriver and open website
#==============================================================================
def get_chromedriver(chromedriver_path,desktoppath):
    #Set default setting for Chrome Driver when using Selenium
    #=============================================================
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', {
    "download.default_directory": desktoppath,
    "download.prompt_for_download": False, #To auto download the file
    "download.directory_upgrade": True,
    "plugins.always_open_pdf_externally": True #It will not show PDF directly in chrome
    })

    driver = webdriver.Chrome(executable_path=chromedriver_path, options=options)
    return driver

def login(username,password):
    try: 
        driver.find_element_by_id("gh-signin-btn").click()
        driver.find_element_by_id ("bdd-email").send_keys(username)
        driver.find_element_by_id("bdd-elsPrimaryBtn").click()

        driver.find_element_by_id ("bdd-password").send_keys(password)
        driver.find_element_by_id("rememberMe").click()

        driver.find_element_by_id("bdd-elsPrimaryBtn").click()
        time.sleep(5)
    except:
        print('login failure')


def crawler(num_page,num_result,page_to_crawl,url,vol_title,vol_url,num_complete):

    for k,v in page_to_crawl.items():
        for n in range(1,int(num_page)+1):

            print ("Looking for volume links @ {}".format(page_to_crawl))
            get_url_and_wait_for_page_load(driver, url + "?page=" + str(n))

            errorhandle = driver.find_elements_by_class_name("js-handle-error")
            if len(errorhandle) == 0:

                for elements in driver.find_elements_by_class_name("accordion-panel-title"):
                    if elements.get_attribute("aria-expanded") == 'false':
                        try:
                            elements.click()
                        except:
                            pass


            time.sleep(5) ##to escape async exceptions

            #contain all volume title and url for further processing
            #==============================================================================
            vol_url += [vol.get_attribute("href")
            for vol in driver.find_elements_by_xpath("//a[contains(@class, 'js-issue-item-link')]")]

            vol_title += [vol.get_attribute("text")
            for vol in driver.find_elements_by_xpath("//a[contains(@class, 'js-issue-item-link')]")]
            #==============================================================================

            #Iterate across all captured volumes 
            #==============================================================================
            for i in range(0,len(vol_url)):

                get_url_and_wait_for_page_load(driver, vol_url[i])
                time.sleep(5) 
                titlelist = driver.find_elements_by_xpath("//a[contains(@class, 'anchor article-content-title u-margin-xs-top u-margin-s-bottom')]")
                urllist = driver.find_elements_by_xpath("//a[contains(@class, 'anchor pdf-download u-margin-l-right text-s')]")

                for title in range(0,len(titlelist)):
                    article_title = titlelist[title].get_attribute("text")
                    article_url = urllist[title].get_attribute("href")

                    values = [k, vol_title[i],vol_url[i],article_title,article_url]

                    conn.execute(
                        "INSERT OR IGNORE INTO fsi_results (JOURNAL, VOL_TITLE, VOL_URL, ARTICLE_TITLE, ARTICLE_URL) \
                        VALUES (?,?,?,?,?)", (k, vol_title[i],vol_url[i],article_title,article_url))
                    conn.commit()
                num_complete = num_complete + 1
                if int(num_complete) == int(num_result):
                    st.write('Ended at user defined volume')
                    break
        st.write('Completed')

            #==============================================================================


def file_selector(folder_path='./Drivers'):
    filenames = os.listdir(folder_path)
    selected_filename = st.selectbox('Select a file', filenames)
    return os.path.join(folder_path, selected_filename)


def download_files(df_download,driver,desktoppath):
    for index, row in df_download.iterrows():
        article_title = row[2]
        article_url = row[3]
        clean_article_title = re.sub('[^A-Za-z0-9]+', ' ', article_title)
        if article_url[-3:] == 'pdf':
            ##if pdf link is available, open the page and download to desktop
            get_url_for_download(driver,article_url)
            
            time.sleep(7)  
            #get latest downloaded file and rename to title
            
            filename = max([desktoppath + r"/" + f for f in os.listdir(desktoppath)],key=os.path.getctime)
            st.write(filename)
            shutil.move(filename,os.path.join(desktoppath, clean_article_title + ".pdf"))

        else:
            #to handle those with [Get Access] or [View PDF] view
            get_url_for_download(driver,article_url)

            time.sleep(5)     
            
            #check if it's [Get Access] view
            dl_btn = driver.find_elements_by_xpath("//a[contains(@class, 'anchor PdfDrawdownButtonLink u-margin-s-right u-margin-xs-top')]")
            #if it's [View PDF] view
            if dl_btn == []:
                dl_btn = driver.find_elements_by_xpath("//a[contains(@class, 'link-button link-button-primary')]")
                article_url = dl_btn[0].get_attribute("href")

                time.sleep(7)
                ##if pdf link is available, open the page and download to desktop
                get_url_for_download(driver,article_url)

                #get latest downloaded file and rename to title
                time.sleep(7)  
                
                filename = max([desktoppath + r"/" + f for f in os.listdir(desktoppath)],key=os.path.getctime)
                st.write(filename)
                shutil.move(filename,os.path.join(desktoppath, clean_article_title + ".pdf"))
                
                time.sleep(7)
            
            else:
                print('this is Get Access View')
                #click to go next page
                dl_btn[0].click()

                #driver.switch_to.window(driver.window_handles[1])
                time.sleep(7)        

                #sometimes it will download immediately, sometimes it will require click continue
                #to put a try pass
                #not a good practice but as a workaround
                try:
                    driver.switch_to.window(driver.window_handles[1])
                    continue_btn = driver.find_elements_by_xpath("//button[@class='button button-primary u-padding-l-hor move-right']")
                    
                    continue_btn[0].click()
                    
                    time.sleep(7) 
                    driver.close()
                    time.sleep(4) 
                    driver.switch_to.window(driver.window_handles[0])
                    
                    #get latest downloaded file and rename to title
                    filename = max([desktoppath + r"/" + f for f in os.listdir(desktoppath)],key=os.path.getctime)
                    st.write(filename)
                    shutil.move(filename,os.path.join(desktoppath, clean_article_title + ".pdf"))
                    
                except:
                    print('Continue button not found')
                    pass



with st.expander('Web Crawler'):
    st.title('Selete Sites To Crawl')

    sites = st.radio(
    "Select sites to crawl:",
    ('Forensic Science International', 'Wiley Online', 'Other websites'))

    results = glob.glob('/**/chromedriver', recursive=True)  # workaround on streamlit sharing
    chromedriver_path = results[0]
    st.write(chromedriver_path)

    st.write('You selected `%s`' % chromedriver_path)

    operating_system = st.selectbox('Select your Operating System',('Windows', 'MacOS'))

    if sites == 'Forensic Science International':
        conn = sqlite3.connect('fsi.db')
        st.write("Connection Status: --Connected to FSI database--")
        username = st.text_input("Username")
        password = st.text_input("Password",type='password')
        num_page = st.text_input("Number of Pages",value='1')  
        num_result = st.text_input("Number of Volume",value='3')

        if username != "" and password != "":
            if st.button('Start Crawling'):
                page_to_crawl = {'FSI':'https://www.sciencedirect.com/journal/forensic-science-international/issues'}
                url = (''.join(str(v) for k,v in page_to_crawl.items()))
                desktoppath = getdesktoppath()
                if operating_system == 'Windows':
                    desktoppath = desktoppath + r'\asg_dl'
                else:
                    desktoppath = desktoppath + r'/asg_dl'
                driver = get_chromedriver(chromedriver_path,desktoppath)
                get_url_and_wait_for_page_load(driver, url)
                login(username,password)
                crawler(num_page,num_result,page_to_crawl,url,vol_title,vol_url,num_complete)

    elif sites == 'Wiley Online':
        st.write('work in progress')
    else:
        st.write('no other websites yet')


with st.expander('Browser'):
    st.title('Select articles to download')

    sites = st.radio(
    "Select DB to download:",
    ('','Forensic Science International', 'Wiley Online', 'Other websites'))

    if sites == 'Forensic Science International':
        conn = sqlite3.connect('fsi.db')
        st.write("Connection Status: --Connected to FSI database--")

        df = pd.read_sql_query("SELECT JOURNAL, ARTICLE_TITLE, ARTICLE_URL from fsi_results", conn)

        num = st.number_input('Index', max_value=df.shape[0])

        st.text_input("JOURNAL",df['JOURNAL'][num])
        st.text_area("ARTICLE TITLE", df['ARTICLE_TITLE'][num])
        st.write("ARTICLE URL", df['ARTICLE_URL'][num])

        if st.button('Add to download queue'):
            conn.execute(
                "UPDATE fsi_results SET DOWNLOAD = 'X' WHERE ARTICLE_TITLE = ?", (df['ARTICLE_TITLE'][num],))
            conn.commit()

        if st.button('Remove from download queue'):
            conn.execute(
                "UPDATE fsi_results SET DOWNLOAD = '' WHERE ARTICLE_TITLE = ?", (df['ARTICLE_TITLE'][num],))
            conn.commit()

        st.title('List of Queued Download(s)')

        df_download = pd.read_sql_query("SELECT JOURNAL, VOL_URL, ARTICLE_TITLE, ARTICLE_URL from fsi_results WHERE DOWNLOAD = 'X'", conn)
        st.write(df_download)


        if st.button('Start Download'):
            desktoppath = getdesktoppath()
            if operating_system == 'Windows':
                desktoppath = desktoppath + r'\asg_dl'
            else:
                desktoppath = desktoppath + r'/asg_dl'
            driver = get_chromedriver(chromedriver_path,desktoppath)
            get_url_and_wait_for_page_load(driver, 'https://www.sciencedirect.com/journal/forensic-science-international/issues')
            login(username,password)
            st.write(desktoppath)
            download_files(df_download,driver,desktoppath)
            st.write('done')
