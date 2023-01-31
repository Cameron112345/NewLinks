import csv
from bs4 import BeautifulSoup as bs
import aiohttp
import asyncio
from typing import List
import re

oldLinks = []
currentLinks = []
newLinks = []
removedLinks = []

tags = re.compile(r'^/tags')
news = re.compile(r'/news')
uploads = re.compile(r'[\'\"\(\/\s](uploads[^\.]+?\.[a-zA-Z0-9]{2,5})[\'\"\)\s]')

limit = asyncio.Semaphore(30)

with open('OldLinks.csv', 'r', newline='', encoding='utf-8') as old:
    oldReader = csv.reader(old, delimiter=',')
    next(oldReader)
    for row in oldReader:
        if row[0] != '':
            oldLinks.append(row[0])
    oldLinks = list(set(oldLinks))
    print(len(oldLinks))
    filtered = []
    for link in oldLinks:
        #match = re.match(r"^(?<=http)[^\.\?]*", link)
        match = re.match(r"https://www\.mvnu\.edu\/[^\.\?]*", link)
        if match is not None:
            filtered.append(match.group(0))
    oldLinks = filtered
    print(len(filtered))
    print(len(oldLinks))



async def getPage(session: aiohttp.ClientSession, link):
    if not link.startswith('/'):
        link = '/' + link
    mvnuLink = "https://www.mvnu.edu" + link
    try:
        async with limit:
            async with session.get(mvnuLink) as r:
                if not r.ok:
                    with open("error.txt", 'a') as errorFile:
                        errorFile.write(str(r.status) + " " + mvnuLink + '\n')
                    if r.status >= 500:
                        print("ERROR: ", r.status)
                else:
                    return await r.text(encoding='UTF-8')

    except Exception as e:
        print("Error downloading page: ", mvnuLink)
        print(e)
        return None
        if "payload" in str(e):
            print("Retrying")
            await getPage(session, link)


def getLinks(pages: List[str]):
    soups: List[bs] = []
    links: List[str] = []
    for page in pages:
        soups.append(bs(page, 'html.parser'))
    
    for soup in soups:
        for a in soup.findAll('a', href=True):
            a['href'] = a['href'].strip()
            if re.match(r"((?<=mvnu\.edu)|^\/)[^\.\?]*", a['href']):
                links.append(re.match(r"((?<=mvnu\.edu)|^\/)[^\.\?]*", a['href']).group(0))

    links = list(set(links))
    return links


async def main():
    global currentLinks
    currentLoopLinks: List[str] = ['']
    async with aiohttp.ClientSession() as session:

        limit = 1000                                                             
        current = 0

        while len(currentLoopLinks) > 0:
            current += 1
            if current > limit:
                return

            #---------------Get Pages--------------------------------------------------------
            pageTexts: List[str] = None
            tasks = []
            for url in currentLoopLinks:
                tasks.append(asyncio.create_task(getPage(session, url)))
            pageTexts = await asyncio.gather(*tasks)
            pageTexts = [pageText for pageText in pageTexts if pageText is not None]
             #-------------------------------------------------------------------------------


             #-------------------Get the new links from the pages-----------------------------------
            links = getLinks(pageTexts)
            #-------------------------------------------------------------------------------------
           

            #---------------Filter Links--------------------------------------------------
            links = [link for link in links if not re.match(r"^/uploads", link)]
            newLoopLinks = []
            for link in links:
                if "https://www.mvnu.edu"+link in currentLinks:
                    continue
                currentLinks.append("https://www.mvnu.edu" + link)
                newLoopLinks.append(link)

            currentLinks = list(set(currentLinks))
            currentLoopLinks = newLoopLinks 
            #------------------------------------------------------------------------

            print("currentLoopLinks: ", len(currentLoopLinks))
            print("currentLinks: ", len(currentLinks))


    newLinks = [link for link in currentLinks if link not in oldLinks]
    removedLinks = [link for link in oldLinks if link not in currentLinks]

    print("\n\n\nLength of new Links:", len(newLinks))
    print("Length of removedLinks:", len(removedLinks))
    print("Length of currentLinks:", len(currentLinks))
    print("Length of old Links:", len(oldLinks))

    with open("NewLinks.csv", 'w', newline='', encoding='utf-8') as new:
        writer = csv.writer(new, delimiter=',')
        writer.writerow(["URL"])
        for link in newLinks:
            writer.writerow([link])

    with open("RemovedLinks.csv", 'w', newline='', encoding='utf-8') as new:
        writer = csv.writer(new, delimiter=',')
        writer.writerow(["URL"])
        for link in removedLinks:
            writer.writerow([link])

    with open("CurrentLinks.csv", 'w', newline='', encoding='utf-8') as new:
        writer = csv.writer(new, delimiter=',')
        writer.writerow(["URL"])
        for link in currentLinks:
            writer.writerow([link])





asyncio.run(main())

